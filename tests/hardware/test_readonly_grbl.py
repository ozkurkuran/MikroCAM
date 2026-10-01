"""Opt-in operator-run inventory. Agents and CI never connect to hardware."""
import json
import os
from pathlib import Path
import subprocess
import time

import pytest

from mikrocam.bridge.serial_transport import SerialIO

COMMANDS = (b"?", b"$I\n", b"$$\n", b"$G\n", b"$#\n")
PREFIXES = {b"?": "<", b"$I\n": "[VER:", b"$$\n": "$0=",
            b"$G\n": "[GC:", b"$#\n": "[G54:"}


def enabled(environ):
    return bool(environ.get("MIKROCAM_HW_PORT")) and not (
        environ.get("CI") or environ.get("GITHUB_ACTIONS"))


def read_query(transport, command, transcript, clock=time.monotonic):
    """Bounded fragmented-line read; an inventory record alone never consumes an ACK."""
    if type(command) is not bytes or command not in COMMANDS:
        raise ValueError("Only the five readonly GRBL queries are allowed")
    transcript.append({"direction": "tx", "hex": command.hex()})
    if transport.write(command) != len(command):
        raise OSError("Incomplete readonly query write")
    deadline = clock() + 3.0
    buffer = b""
    lines = []
    received = 0
    while clock() < deadline:
        chunk = transport.read(4096)
        if not isinstance(chunk, bytes):
            raise OSError("Invalid readonly response")
        if not chunk:
            continue
        transcript.append({"direction": "rx", "hex": chunk.hex()})
        received += len(chunk)
        if received > 16384:
            raise ValueError("Readonly response exceeded 16384 bytes")
        buffer += chunk
        while b"\n" in buffer:
            raw, buffer = buffer.split(b"\n", 1)
            line = raw.decode("utf-8", errors="replace").strip()
            lines.append(line)
            if line.startswith(("error:", "ALARM:")):
                raise ValueError(f"Readonly query rejected: {line}")
            record = any(item.startswith(PREFIXES[command]) for item in lines)
            if command == b"?" and record and line.startswith("<") and line.endswith(">"):
                return lines
            if command != b"?" and line == "ok" and record:
                return lines
    raise TimeoutError(f"No complete readonly reply for {command!r}")


@pytest.mark.hardware
@pytest.mark.skipif(not enabled(os.environ), reason="Operator-only: set MIKROCAM_HW_PORT; always skipped in CI")
def test_readonly_grbl_inventory():
    port = os.environ["MIKROCAM_HW_PORT"]
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    log = Path(os.environ.get("MIKROCAM_HW_LOG", f".venv/hardware/grbl-readonly-{stamp}.json"))
    # Validate log destination before opening any port.
    log.parent.mkdir(parents=True, exist_ok=True)
    evidence = {"port": port, "utc": stamp, "queries": {}, "wire": [], "result": "failed"}
    evidence["commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], timeout=5).decode("ascii").strip()
    transport = SerialIO(port)
    try:
        transport.open()
        # Allow spontaneous startup/reset data to settle without sending wake/reset bytes.
        deadline = time.monotonic() + 2.0
        size = 0
        while time.monotonic() < deadline:
            chunk = transport.read(4096)
            if chunk:
                evidence["wire"].append({"direction": "rx-startup", "hex": chunk.hex()})
                size += len(chunk)
                if size > 16384:
                    raise ValueError("Startup exceeded readonly capture limit")
        for command in COMMANDS:
            evidence["queries"][command.decode().strip()] = read_query(transport, command, evidence["wire"])
        evidence["result"] = "passed"
    finally:
        try:
            transport.close()
        finally:
            log.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            print(f"Readonly hardware evidence: {log.resolve()}")
