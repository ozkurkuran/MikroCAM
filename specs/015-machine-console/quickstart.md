# Quickstart
Use the pinned Python3.13 environment. Run focused test_console/test_wire modules, then full
pytest and actual desktop smoke. Never open hardware for automated validation.
Open Machine -> Console. Connect the explicit Fake fixture, inspect escaped TX/RX records,
choose a supported read-only query and check its outcome. Run a job to verify console admission
locks while raw logging continues. Inject delayed/duplicate/partial failures; reconnect is required
for another ordinary operation. Clear view changes display only. Inspect retained final evidence.