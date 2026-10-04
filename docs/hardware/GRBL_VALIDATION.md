# GRBL 1.1 physical validation protocol

Status: prepared on 2026-10-01. **No physical device has been tested by an agent.**
The operator performs H3; software/Fake/CI results do not change a physical cell to passed.
Use one owner of the COM port at a time. Close Machine and other senders before the optional
inventory test. Close the inventory test before using Machine. Never run it on an active job.

## Preconditions and stop rules

- Remove the cutting tool. Disconnect spindle/laser power independently of software.
- Check physical E-stop operation and keep it reachable. Verify clamps, cable routing,
  axis travel and a safe air-cut clearance before any motion scenario.
- Record `$20`, `$21`, `$22`, `$23`, `$32`, report units `$13`, homing/position validity and
  configured limits. Do not change settings to make a test pass. Unexpected settings stop admission.
- Record startup blocks through Machine's readonly `$N` query. Do not execute or rewrite them.
- Begin with readonly checks, then bounded manual motion, then a short air job. Only the
  operator may issue movement, zero, hold/resume, reset or output commands through Machine.
- USB/serial opening can toggle driver DTR/RTS and reset a controller even when the program
  sends only queries. Observe this with output power disconnected and the mechanism stopped.
- If motion/output is unexpected, use physical E-stop, retain evidence and mark the cell failed.
  Do not rely on a severed USB link to deliver Stop. Feed hold can leave spindle/coolant on;
  Door can perform configured parking; reset may invalidate position. Record actual behavior.
- Restoring power/homing/position after a failure is a separate operator decision. No automatic
  reconnect/restart or replay is part of this protocol.

## Run record

Copy this section for each board/firmware/driver/commit combination. Retain raw wire logs,
readonly JSON, photographs/screenshots and measurements next to the completed record.

| Field | Value |
| --- | --- |
| Run ID / local date and time / timezone | Not tested |
| Operator | Not tested |
| Board manufacturer / model / revision | Not tested |
| Firmware greeting and complete `$I` output | Not tested |
| USB serial chip / VID PID / driver name and version | Not tested |
| Windows edition and build / physical COM port / baud | Not tested |
| MikroCAM commit (`git rev-parse HEAD`) / Python version | Not tested |
| Homing completed / position validity / `$20` `$21` `$22` `$23` `$32` `$13` | Not tested |
| Limit values and startup blocks | Not tested |
| E-stop and output-power isolation evidence | Not tested |
| Fixture / air clearance / probe type / measuring instrument accuracy | Not tested |
| Log directory and evidence hashes | Not tested |

## H2 optional readonly inventory

The test is skipped unless `MIKROCAM_HW_PORT` is set and is always skipped when `CI` or
`GITHUB_ACTIONS` is set. It opens one physical serial port at 115200, allows startup data to
settle, then sends exactly `?` (one byte), `$I`, `$$`, `$G`, `$#` (each with one newline).
It sends no movement, `$` setting write, wake line, unlock, homing or reset. Each query has a
three-second response bound and a 16384-byte capture cap. A missing response, controller
error or oversized reply fails the test. The port closes and the JSON is retained on failure.
Inventory rows are checked with strict GRBL parsers; TX attempts and successful writes are recorded separately.
Inventory passing proves only complete replies to these five queries at this moment.

Operator PowerShell, from the selected MikroCAM checkout:

```powershell
$env:MIKROCAM_HW_PORT = 'COM7' # replace with your physical device
$env:MIKROCAM_HW_LOG = 'E:\your-evidence\run-001\readonly.json'
& .\.venv\Scripts\python.exe -m pytest tests/hardware/test_readonly_grbl.py -q -s
Remove-Item Env:MIKROCAM_HW_PORT
Remove-Item Env:MIKROCAM_HW_LOG
```

Without `MIKROCAM_HW_LOG`, JSON defaults to `.venv/hardware/grbl-readonly-<UTC>.json`.
Attach the resulting log; copy its firmware/settings/modal/offset replies into the run record.
The test intentionally does not query `$N`; use Machine for that readonly record separately.
Agents run only `tests/test_hardware_readonly_guard.py` and the default-skipped collection.

## H3 operator scenarios and acceptance

Each row is derived from the outstanding physical claims in the linked validation document.
Document expected vs observed behavior, pass/fail/not-tested, log path and measurements for
**every** row. For unsupported optional configurations, record a reasoned not-applicable value.
A simulator cannot satisfy any row. Never mark an entire feature validated from inventory alone.

| ID | Slice / source | Operator action and measurable acceptance |
| --- | --- | --- |
| H010-1 | [010](../../specs/010-machine-connect-grbl/validation.md) | With mechanisms stopped and power isolated, connect/disconnect/reconnect. Record greeting/reset on open, firmware and USB driver behavior. UI must match causal controller state and close ownership before reconnect. |
| H010-2 | 010 | Compare fresh Machine MPos, WPos, WCO and report units with controller replies in mm/inch as configured. Interrupt status reporting and verify stale/blank DRO rather than old actionable coordinates. Retain timestamps. |
| H011-1 | [011](../../specs/011-jog-and-work-zero/validation.md) | Home only after operator checks; perform smallest bounded jog on each free axis. Measure distance/direction and verify limit admission. Cancel during jog; observe actual stop distance and causal Idle. |
| H011-2 | 011 | Set G54 zero through Machine only at an explicitly chosen position. Compare offset readback. Power-cycle with outputs isolated; re-establish homing/position before checking stored G54. Record persistence and startup/reset effects. |
| H011-3 | 011 | Record startup blocks, parking/Door configuration and alarm state. Confirm refused manual actions stay refused. Test physical E-stop and configured Door/parking only with a known safe envelope. Do not classify Door as verified stop. |
| H013-1 | [013](../../specs/013-job-streaming/validation.md) | Review a short bounded air job with output power disconnected. Confirm explicit start, ordered accepted-line progress, final M5 M9 ACK, output-off readback and causal Idle endpoint. Measure observed endpoint against reviewed path. |
| H013-2 | 013 | Hold a safe air job; record deceleration, held state and physical outputs. Resume explicitly. Repeat with Stop and with panel/application close during hold; record completion of shutdown, no further job lines and actual stop/output state. |
| H013-3 | 013 | During a safe low-speed air job disconnect USB while E-stop is ready. UI must show failure and invalidate control; confirm no automatic replay after reconnect. Observe independently whether the mechanism continues because a lost link cannot transmit Stop. |
| H013-4 | 013 | Run a reviewed short-segment air job (including 026 output). Retain wire timing and video. Record visible pauses and attribute them using send/ACK timing; only demonstrated send-response delay can trigger C3. No character-counting mode is implied. |
| H014-1 | [014](../../specs/014-dry-run/validation.md) | Compare actual air-cut path and safe Z with dry-run/preflight bounds for the same source, placement, zero and limits. Check fixture clearance independently; simulation does not establish physical collision clearance. |
| H015-1 | [015](../../specs/015-machine-console/validation.md) | Query the readonly inventory and startup blocks through Machine console. Verify one owner, complete causal replies, bounded display and TX/RX timing. Cable loss/timeouts must not present success or allow stale evidence to admit motion. |
| H025-1 | [025](../../specs/025-probe-grid-heightmap/validation.md) | Check probe polarity/continuity independently. On a known plane acquire a small reviewed grid. Compare contact heights with independent measurements and saved measured provenance; record stopped Z separately from contact Z. |
| H025-2 | 025 | With safe limited Z travel test no-contact, failed contact, Stop during acquisition and cable loss. Partial map must remain partial; no unsafe retract/resume from unverified stop or stale coordinates. Record actual contact/stop/retract behavior. |
| H026-1 | [026](../../specs/026-autolevel-z-compensation/validation.md) | Measure board registration/G54 and surface independently, then review/save derived output. First run in air with tool removed; compare placement, rapid clearance and Z bounds to original/map/reference. |
| H026-2 | 026 | Only after air results pass, restore a suitable tool and output power under operator control for a sacrificial coupon. Measure isolation depth/uniformity and map/probe accuracy with instrument/tolerance declared before cutting. Record all errors; do not infer accuracy from software chord tolerance. |

## Compatibility matrix

Copy the matrix once for each board/firmware/driver/commit run. Every result needs its wire-log
path and physical measurement or observation reference. Initial values below deliberately
preserve the absence of evidence; they are not failures or passes.

| Board / firmware / run ID | 010-1 | 010-2 | 011-1 | 011-2 | 011-3 | 013-1 | 013-2 | 013-3 | 013-4 | 014-1 | 015-1 | 025-1 | 025-2 | 026-1 | 026-2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Not supplied / not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested | Not tested |

Cell format: `passed/failed/not-tested/not-applicable — evidence path; observation; tolerance`.
A failed case opens a test-first hotfix when existing behavior is wrong, or a separate spec
proposal when new behavior is required. Keep the raw failure evidence.

## H042 firmware identification scenarios (spec 042) — NOT_RUN

Status: prepared on 2026-10-04; **NOT_RUN on every board**. Software was built and tested only
against FakeGRBL profiles; no grblHAL or FluidNC board was available. These rows are readonly:
the operator only connects, reads the Machine **Firmware** row/tooltip and the wire log, and
disconnects. Keep spindle/laser power isolated anyway because opening a port may reset a board.
Record the complete greeting and `$I` reply verbatim (Machine console `$I` or H2 inventory JSON).

| ID | Board / firmware | Operator action and measurable acceptance |
| --- | --- | --- |
| H042-1 | GRBL 1.1 (gnea, e.g. Uno 1.1h) | Connect. TX begins `$I`, `$$`, `?`. Firmware row shows `GRBL 1.1x (build YYYYMMDD)`, RX matching `[OPT:…,rx]`, budget `min(rx,128)`, motion enabled. Repeat with a board that resets on open: one extra `$I` after the greeting, then identified. |
| H042-2 | grblHAL, default compatibility level 0 | Greeting `GrblHAL 1.1f ['$' or '$HELP' for help]`; `$I` lists `[FIRMWARE:grblHAL]`, NEWOPT, DRIVER/BOARD. Row shows `grblHAL 1.1f`, reported RX, char-counting unavailable, motion disabled (043). Jog/zero/job/probe stay disabled; console works. |
| H042-3 | grblHAL with `COMPATIBILITY_LEVEL` ≥ 1 | Greeting `Grbl 1.1f ['$' for help]`, plain `$I` has a three-field OPT (RX usually 1024). Expected: **Unknown** with the 255-limit note, motion disabled. Record whether RX ≤ 255 on that build (would be classified GRBL; report it). |
| H042-4 | FluidNC v3.x and v4.x, default start message | Greeting `Grbl <x.y> [FluidNC v<x.y.z> (…) '$' for help]`. Row shows `FluidNC x.y.z`, RX unknown, motion disabled (044) — never `GRBL`. Record `[MSG:INFO:` boot lines seen. |
| H042-5 | FluidNC with a custom `$Start/Message` | Set a custom start message on the bench only, reset the board while connected. Record whether a reset was detected (known D1 gap UA-8: greetings not starting with `Grbl `/`GrblHAL ` are not reset evidence). Restore the setting afterwards. |
| H042-6 | Any unsupported firmware (e.g. GRBL 0.9, Grbl_ESP32 1.3a) | Row shows **Unknown** with a reason; all motion controls disabled; Stop/Abort/Disconnect usable; no automatic retry of `$I`. |
| H042-7 | Any identified board | Reset the controller from its button while connected and idle. Same firmware: only `$$` is re-read. After reflashing to a different family between sessions, reconnect shows the new family. |

| Board / firmware / run ID | H042-1 | H042-2 | H042-3 | H042-4 | H042-5 | H042-6 | H042-7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Not supplied / not tested | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

Identification passing does not validate grblHAL/FluidNC motion; that belongs to specs 043/044.

## H044 FluidNC USB serial scenarios (spec 044) — NOT_RUN

Status: prepared on 2026-10-04; **NOT_RUN on every board**. Software was built and tested only against
the FakeGRBL `fluidnc` (v4.1.1) and `fluidnc3` (v3.9.9) profiles; no FluidNC board was available and
H3 has not been completed. Use an ESP32 FluidNC board whose firmware is v3.9.x or v4.x, record the
exact release, board, USB bridge chip (CP210x/CH340/native S3 USB) and driver. Isolate spindle/laser
power, remove the tool and keep the physical E-stop reachable for every motion row. The optional H2
readonly inventory now detects FluidNC from `$I` and additionally sends only
`$/macros/startup_line0`, `$/macros/startup_line1`, `$/macros/after_reset`, `$RI` and `$CD`.

| ID | Operator action and measurable acceptance |
| --- | --- |
| H044-1 | Port-open reset: with mechanisms stopped connect 5× and disconnect. Record whether the board reboots on open (ROM lines `ets`/`rst:0x` or `ESP-ROM:` in the wire log), time to the greeting, and that MikroCAM shows `FluidNC x.y.z … motion enabled` only after the greeting/quiet period; no `$I`/`$$` before readiness is acknowledged. Record DTR/RTS behaviour per USB bridge; note any board left in download mode (S3). |
| H044-2 | Readonly evidence: H2 inventory plus Machine console `$CD`. Compare `$$` (`$13`, `$30`, `$32`), `$#` (TLO scalar on 3.x, vector on 4.x), macros and `$RI` with the YAML. Confirm MikroCAM never sent `$N`, settings writes or `0x87`–`0x8A`. |
| H044-3 | Startup macros: on the bench set `macros/after_reset` (then `startup_line0`) to a harmless non-motion line, e.g. `G4P0`; jog/job/probe must be refused before any motion with the macro named. Restore the empty values afterwards. With `$RI=200` the same refusal must name `$RI`; restore `$RI=0`. |
| H044-4 | Smallest bounded jog on each axis, Cancel jog during a 10 mm jog, G54 selection and XY/Z zero: measure distances/direction and offsets as in H011-1…3. Record that Cancel jog returns `ok` (FluidNC suppresses `error:130`). |
| H044-5 | Short reviewed air job (send-response) with output power disconnected; Pause/Resume, Stop and Abort as in H013-1/2. Record `Hold:0/1`, `Door:n` and whether `after_reset` stayed empty so Stop used `0x18`. Character counting must be refused. |
| H044-6 | Probe grid on a known plane as in H025-1/2 (contact `[PRB:…:1]`, `ALARM:5` on no-contact) and a reviewed autolevel air run as in H026-1. |
| H044-7 | Custom greeting: set `$Start/Message` to a text not starting with `Grbl`, reset the board from its button while idle and during a safe air job. Expected: idle → identity/units re-read after ~2 s; job → stopped (`0x18`/`0x84`), no further job lines. Restore the default afterwards. |
| H044-8 | Power-cycle (or EN button) while connected and idle, then during a safe air job: UI must invalidate units/identity, end the operation as reset, and re-identify only after the board is ready. Observe independently whether the mechanism stopped. |
| H044-9 | USB cable loss during a safe low-speed air job (as H013-3): failure shown, no automatic replay. |

| Board / FluidNC release / bridge / run ID | H044-1 | H044-2 | H044-3 | H044-4 | H044-5 | H044-6 | H044-7 | H044-8 | H044-9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Not supplied / not tested | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

Spec 044 closes the D1 software gap UA-8 (custom greeting reset detection) in software only; H042-5
and H044-7 remain the physical evidence and are NOT_RUN.

## Completion and deferred gates

H1/H2 are agent preparation. H3 is complete only when an operator supplies a completed record
and matrix for at least one GRBL 1.1 board with sufficient evidence for each applicable row.
Only then can relevant ROADMAP physical-validation annotations be changed. C3 additionally
needs measured segment stalls tied to send-response timing. The user explicitly started grblHAL
and FluidNC software work on 2026-10-04 (docs/IS_TAKIP.md); physical D validation still needs
the target FluidNC/grblHAL board and the H042 rows above.
No physical evidence is asserted by this document.
