"""Opt-in operator-run inventory. Agents and CI never connect to hardware."""
import json
import os
import re
from pathlib import Path
import subprocess
import time

import pytest

from mikrocam.bridge.serial_transport import SerialIO
from mikrocam.machine.firmware import FirmwareFamily, identify
from mikrocam.machine.grbl import parse_status
from mikrocam.machine.grblhal import normalize_query_line
from mikrocam.machine.job_preparation import query_record

COMMANDS = (b"?", b"$I\n", b"$$\n", b"$G\n", b"$#\n")


def enabled(environ):
    return bool(environ.get("MIKROCAM_HW_PORT")) and not (
        environ.get("CI") or environ.get("GITHUB_ACTIONS"))


def inventory_record(command, line, grblhal=False):
    """Validate complete raw inventory syntax without claiming physical positions.

    ``grblhal`` (spec 043) applies the controller's grblHAL status mode and query dialect.
    """
    if len(line) > 512 or any(not 32 <= ord(char) <= 126 for char in line):
        raise ValueError("Inventory record must be bounded printable ASCII")
    if command == b"?" and line.startswith("<"):
        parse_status(line, grblhal=grblhal)
        return True
    if grblhal and command != b"$I\n":
        line = normalize_query_line(line)
        if line is None:
            return False
    if command == b"$I\n" and line.startswith("[VER"):
        if re.fullmatch(r"\[VER:1\.1[a-z]?(?:\.[0-9]{8})?:[^\[\]]{0,200}\]", line) is None:
            raise ValueError("Malformed GRBL build record")
        return True
    purpose = {b"$$\n": "settings", b"$G\n": "modal", b"$#\n": "parameters"}.get(command)
    if purpose:
        # Only validate parameter syntax; the returned converted value is never retained.
        record = query_record(purpose, line, "mm")
        return record is not None and record[0] == {"settings": 0, "modal": "modal", "parameters": "G54"}[purpose]
    return False


def family_of(lines):
    """Classify a captured $I reply with the controller's own rules (042/043)."""
    evidence = tuple(line for line in lines if line.startswith("[") and not line.startswith("[MSG:"))
    return identify("", evidence).family


def read_query(transport, command, transcript, clock=time.monotonic, grblhal=False):
    """Bounded fragmented-line read; an inventory record alone never consumes an ACK."""
    if type(command) is not bytes or command not in COMMANDS:
        raise ValueError("Only the five readonly GRBL queries are allowed")
    transcript.append({"direction": "tx-attempt", "hex": command.hex()})
    if transport.write(command) != len(command):
        raise OSError("Incomplete readonly query write")
    transcript.append({"direction": "tx", "hex": command.hex()})
    deadline = clock() + 3.0
    buffer = b""
    lines = []
    received = 0
    record = False
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
            try:
                line = raw.decode("ascii").removesuffix("\r")
            except UnicodeDecodeError as error:
                raise ValueError("Inventory record must be ASCII") from error
            lines.append(line)
            if line.startswith(("error:", "ALARM:")):
                raise ValueError(f"Readonly query rejected: {line}")
            record = inventory_record(command, line, grblhal) or record
            if command == b"?" and record and line.startswith("<") and line.endswith(">"):
                return lines
            if command != b"?" and line == "ok" and record:
                return lines
        if len(buffer) > 512:
            raise ValueError("Inventory record exceeds 512 bytes")
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
        grblhal = False
        for command in COMMANDS:
            lines = read_query(transport, command, evidence["wire"], grblhal=grblhal)
            evidence["queries"][command.decode().strip()] = lines
            if command == b"$I\n":
                family = family_of(lines)
                evidence["firmware"] = family.value
                grblhal = family is FirmwareFamily.GRBLHAL
        evidence["result"] = "passed"
    finally:
        try:
            transport.close()
        finally:
            log.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
            print(f"Readonly hardware evidence: {log.resolve()}")
