# Quickstart validation (after implementation)

Use the existing pinned Python 3.13 x64 environment. No new dependency, desktop or hardware.
Run from the repository root. Commands below describe the contract; implementation is pending.

1. Run focused tests and offline corpus audit:
   `python -m pytest tests/test_reference_dataset.py tests/test_reference_capture.py tests/test_reference_compare.py -q`.
   Require 10–20 admitted designs, all five origins, valid SHA256/role/license evidence.
2. Verify both detached source worktrees are clean at the exact revisions in the contract.
   Do not switch/update/patch them. Freeze capture-config.json only after recorded API probes.
3. Capture each baseline into a fresh temporary directory, supplying its interpreter/source:
   `python tests/reference/capture.py --engine evo --source ../MikroCAM-reference-evo --python PYTHON_PATH --manifest tests/reference/boards/manifest.json --config tests/reference/capture-config.json --output NEW_EVO_DIRECTORY`.
   Repeat for legacy8994 with `../FlatCAM-reference-8994`. Repeat each capture into another
   fresh directory and check normalized reproducibility before reviewing tracked goldens.
4. Capture current using `--engine current --revision CLEAN_CURRENT_SHA` and its source/interpreter.
5. Compare explicitly, for example:
   `python tests/reference/compare.py --baseline evo --goldens tests/reference/goldens/evo --candidate CURRENT_DIRECTORY --manifest tests/reference/boards/manifest.json --config tests/reference/capture-config.json --distance-mm 0.000001 --area-mm2 0.000001 --report REPORT_PATH`.
   These numbers are an explicit example, not default or approved automatic tolerance widening.
   Repeat separately against legacy8994. Never choose whichever baseline passes automatically.
6. Inspect exit 0/all-match, 1/measured-difference, or 2/indeterminate-invalid and each stage's
   metrics/diagnostic. Known baseline errors remain exit 2 until real comparable evidence exists.
   Preserve both distinct baseline outputs and report inherited differences honestly.
7. Run full pytest and architecture/growth/size gates. Verify references/settings unchanged,
   no owned child processes remain and comparison requires no network.

Deliberate mutation tests must detect a moved coordinate, removed hole, reversed CNC path,
IN conversion mistake, input byte corruption and missing/error stage. Raw G-code is audit
evidence; passing this comparison does not certify machine safety or target/controller behavior.
