# Read-only GRBL validation quickstart

Run from the feature checkout with the existing pinned CPython3.13 development environment.
No additional dependency or actual serial device is needed for automated validation.

1. Run the new parser/controller/fake/serial-adapter tests without Qt or hardware.
2. Run panel and worker tests under the existing settings sandbox, including ten repeated
   connect/disconnect/close cycles. Verify only status/settings reads are recorded.
3. Run full pytest and architecture/growth checks.
4. Run `python tests/smoke_app.py` on a real desktop; add fake Machine panel coverage without
   opening an actual serial port. Retain logs and a screenshot in the ignored validation folder.
5. Check actual imported implementation stays within the four-layer architecture and old CAM
   flows still work. Record commands/results/limitations in validation.md before PR delivery.

For eventual manual real-controller validation, opening the Machine panel does not connect.
Select a known GRBL1.1 port explicitly; port opening may reset some adapters/controllers.
Verify reported units, machine/work coordinates and offsets against the controller display.
Read-only Disconnect closes communications and is not a physical emergency-stop control.
