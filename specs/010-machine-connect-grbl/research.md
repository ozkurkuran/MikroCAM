# Research: Read-only GRBL connection

## Decisions
- Reuse pinned pyserial in `bridge/serial_transport.py`, injecting it into the pure controller.
  Rejected: relaxing the domain import guard; copying legacy ToolLevelling; network transports.
- Use a small Transport Protocol because SerialIO and FakeGRBL are two concrete implementations.
  Rejected: generic backend registry, dependency-injection container or plugin architecture.
- Send only `?` and `$$\n`. Require report-unit evidence before mm DRO; never write a setting.
  Rejected: assuming mm, sending a reset/wake sequence, or changing reporting configuration.
- Treat WCO as session evidence; clear it on reset, unit change, stale status or disconnect.
  Show whichever coordinate system was reported directly if the offset is absent.
- One I/O owner with immutable snapshots; no UI accesses from the worker. Existing laser worker
  and shutdown tests provide local lifecycle patterns, not machine-control semantics.

## Existing Code/Licenses
`requirements.txt` pins pyserial 3.5; its BSD-3-Clause notice is already in the dependency
inventory. `tests/architecture/imports.py` permits bridge integration dependencies while
machine stays stdlib/core-only. `appPlugins/ToolLevelling.py` already has serial probing, but
its port-opening scan, DTR toggle, wake sequence and development success override are not reused.
`mikrocam/ui/laser_cam.py`, `laser_worker.py` and existing Qt shutdown tests show local integration.

## Primary Sources (checked 2026-09-27)
- [GRBL 1.1 interface](https://github.com/gnea/grbl/blob/master/doc/markdown/interface.md):
  asynchronous status, optional/reordered fields, MPos/WPos/WCO and report-unit behavior.
- [GRBL settings](https://github.com/gnea/grbl/blob/master/doc/markdown/settings.md): `$$` reads
  settings and `$13` identifies report units; assignments change stored configuration.
- [pySerial API](https://pyserial.readthedocs.io/en/stable/pyserial_api.html): bounded serial
  read/write APIs and the possibility of OS/driver DTR/RTS effects on opening.
- [GRBL maintainer discussion](https://github.com/gnea/grbl/issues/731): adapter/bootloader
  resets can accompany serial opening. Explicit user action does not make positions trustworthy.

This is protocol-based independent implementation. No external application source is ported;
no FlatCAM-Plus source, remote or artifact is accessed. Actual controller hardware is not
required for software tests and is not opened during development validation.
