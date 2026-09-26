# Validate the guardrails

From the repository root after installing `requirements-dev.txt` in `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/architecture -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

The first command tests both the current checkout and synthetic violations. Use
`$env:MIKROCAM_BASE_REF = '<feature-base-sha>'` to select an explicit base; remove the
environment variable after the check. Fetch complete history when the guard reports a missing
revision. Never regenerate the record solely to silence a failure.

On the feature pull request, the Windows workflow must finish successfully and upload its
JUnit report. GUI smoke remains unchanged because this slice modifies no runtime GUI behavior.
