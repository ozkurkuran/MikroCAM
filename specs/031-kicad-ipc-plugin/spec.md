# Feature031: KiCad IPC toolbar transfer
2026-10-02; user requests necessary direct KiCad→MikroCAM integration. Depends on030; does not require laser recipe/island slices.
## Clarifications / decisions
KiCad10.0.x PCB Editor, official IPC kicad-python0.8.0 optional isolated Python runtime. Transfer includes unsaved editor changes using SaveCopyOfDocument (Board.save_as), preserving open document and original design. Named PCB required; new unnamed board must be saved once by user.
## Stories
1. P1 Click MikroCAM toolbar action; current live PCB snapshot becomes030 production package and opens MikroCAM.
2. P1 Install/reinstall the bridge without replacing unrelated KiCad plugins or changing CAM dependencies.
3. P2 See actionable missing configuration/API/CLI/export/launch errors; recover without source changes.
## Functional requirements
FR001 Official IPC plugin.json PCB toolbar action with MikroCAM icon, no SWIG/application imports.
FR002 Use launch-provided socket/token via official SDK; correct instance; reject unsupported version/unnamed board.
FR003 Save a private copy including project; original board, unsaved state and active document unchanged; export copy via030.
FR004 Validate configured CAM Python/repo/output directory; use argv/shell=False and bounded helper wait; no global environment changes.
FR005 Unique retained .mcam-transfer package; open existing/new MikroCAM through precise startup path; no machine start or project clearing.
FR006 Failed snapshot/export/CLI never launches CAM with partial/stale package; errors visible in KiCad action console.
FR007 Reversible installer uses resolved Documents location or explicit target, backup prior bridge files and changed KiCad API settings; unrelated files untouched.
FR008 Pin optional dependency tree and record MIT/BSD licenses; normal CAM starts without SDK.
FR009 Tests fake IPC/launch failures and official manifest schema; real installed IPC snapshot/CLI/native CAM evidence independent of CI.
## Hazard analysis
File transfer only, no serial port or laser. SaveCopy exports current in-memory snapshot; no save/revert/destructive editor operation. DRC gates stay in030. Package paths are generated local data, no script execution from manifest.
## Success
Toolbar action carries current named board including unsaved edits to aligned manufacturing objects in MikroCAM. Reinstall preserves other plugins/settings and configuration accurately identifies current checkout/runtime.
