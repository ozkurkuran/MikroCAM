# H1/H2 preparation validation

Prepared 2026-10-01 against main `8680a09d`. No physical port was connected.

- H1 scenarios derived from physical limitations in validation.md for 010,011,013,014,015,025,026.
  GRBL_VALIDATION.md includes preconditions, per-run metadata, evidence-backed matrix, operator
  actions/acceptance and explicit H3/C3/D gates. Every initial physical cell is not tested.
- H2 exact readonly inventory: ?, $I, $$, $G, $#; bounded three-second query waits and 16384-byte
  capture cap. No motion, setting write, wake, reset or implicit network port.
- 24 mock guard tests passed; one physical test skipped by default. Tests cover CI exclusion,
  exact allowlist, fragmented reads, missing inventory despite ACK, timeout/error/alarm/bounds,
  and close/log retention on both success and failure. No test enables a real device.
- Complete local suite with CI=true: 5124 passed, 310 subtests passed, 3 skipped, 11 existing warnings
  in 305.48 s. Includes architecture/legacy-growth checks; `.venv/hardware-full.log`.
- Final-head Windows CI is required and recorded in the PR after this document's commit.
- H3 is outstanding: requires an operator's GRBL1.1 board, completed matrix and raw logs/measurements.
  Nothing in this preparation certifies physical travel, stopping, outputs or compensation accuracy.

## Delivery review, 2026-10-02
Malformed/truncated expected records and misleading TX success on short/failed writes were
reproduced first, then corrected. Ten malformed-response cases and two write-evidence cases
now pass along with the original 24 mock guards. The operator command uses the documented
checkout-relative interpreter. Physical inventory remains skipped; no device was connected.
Original ddc9c7ab Windows evidence: https://github.com/ozkurkuran/MikroCAM/actions/runs/36925087618 .
The final integration's separate exact-head CI result is recorded in central docs/IS_TAKIP.md.
