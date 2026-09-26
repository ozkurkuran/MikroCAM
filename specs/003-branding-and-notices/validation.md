# Validation: Branding and notices

## Pre-implementation analysis

16/16 specification checks pass; no extension hooks configured. FR-001/002 map to T003–T006,
FR-003/004/005/006 to T007–T009 (identity consistency also T003), FR-007/008 to T010–T012.
SC-001/003 require desktop smoke, SC-002 inventory tests and SC-004 update-boundary tests.
Three stories, seventeen tasks. GUI smoke has an explicit plan exception; no other unresolved
constitutional conflict, ambiguity or missing task coverage. No public API/transfer contract
is introduced; the UI acceptance contract is in the spec.

## Local implementation evidence

- Test-first identity/update checks initially failed in 15 cases (one compatibility case
  already passed). Focused identity/updater/architecture suite: 214 passed, 10 subtests.
- Clean core environment full suite: **634 passed, 2 unchanged upstream placeholders skipped,
  310 subtests passed** in 40.20s. The three preexisting SWIG warnings remain. `pip check` clean.
- A strict facade characterization initially expected version_check to call Evo. It now asserts
  the product boundary instead; its suite passes with 185 subtests. No test was silently skipped.
- Notice tests initially failed for the missing inventory. Review found code/bytecode under
  directories named `licenses` had been collected as legal text. Five added regressions failed,
  the eight false-positive records/files were removed, and **24 notice tests now pass**. The
  unpublished notice commit was corrected before push. No executable package code is included.
- Final inventory: **58 exact dependency pins, 5 separate components, 135 hashed files**,
  1,039,771 bytes. Installed copies match wheel RECORD hashes; additional source archive
  hashes/provenance are recorded. `.gitattributes` preserves the original bytes in Git.
- Real desktop smoke exited 0: STARTUP_OK, ABOUT_OK, GERBER_OK, EXCELLON_OK, ISOLATE_OK,
  CNC_OK (26,367 G-code characters), PROJECT_SAVE_OK, PROJECT_ROUNDTRIP_OK, RENDER_OK and
  SHUTDOWN_OK. Saved project compatibility version stays Unstable; all four object kinds and
  G-code survive reopen. Temporary settings/data and normal worker/process shutdown verified.
- `.venv/about-smoke.png` and `.venv/startup-smoke.png` were visually inspected: MikroCAM 0.1.0,
  both upstream copyrights, project links and GPL dependency note render correctly, with the
  inherited Evo artwork retained. These local validation artifacts are ignored by Git.
- Ratchet: **-225/50** against f9bd51f7; total changed legacy source **-248**. New runtime
  modules have at most 72 lines and functions at most 10 lines. No new runtime dependency.

Hosted validation is the remaining delivery gate.

Review clarified FR-005/SC-002: this source-checkout slice inventories all 58 pins and copies
their full package licenses and supplied bundled notices. An absent optional native-library
notice cannot be manufactured from the parent package license; those omissions are explicitly
recorded for the later binary-packaging slice. This does not certify a redistributable binary
bundle. About/preferences and dynamic-version checks pass; upstream asset attribution is retained.
