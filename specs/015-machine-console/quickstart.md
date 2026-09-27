# Quickstart
Use the pinned Python 3.13 environment. Run the focused `test_console` and `test_wire` modules, then
the full pytest suite and an actual-desktop smoke test. Never open hardware for automated
validation.

Open Machine → Console. Connect the explicit Fake fixture, inspect escaped TX/RX records, choose a
supported read-only query, and check its outcome. Run a job to verify that console admission locks
while raw logging continues. Inject delayed, duplicate, and partial failures; reconnect before
another ordinary operation. **Clear view** changes only the display. Inspect retained final
evidence.
