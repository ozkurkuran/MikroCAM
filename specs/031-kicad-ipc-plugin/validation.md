# Validation031 — 2026-10-02
Official installed KiCad10.0.6; optional kicad-python0.8.0 pinned with its complete dependency tree and license texts. Official KiCad10 plugin schema validates. Test-first missing installer ERROR, backup-in-plugin duplicate action red and SDK0.8 no-public-close red fixed without adopting unsupported API.

Real isolated IPC evidence PASS exit0 (.venv/kicad-ipc-native.log): live unsaved text copied with SaveCopyOfDocument, original PCB byte-for-byte unchanged, real CLI produced retained package, CAM launch argv recorded. Toolbar button click itself NOT_RUN. Official include_project snapshot also copies custom DRC rules; no KiCad source copied into implementation.

Native Qt/OpenGL MikroCAM smoke PASS exit0 (.venv/kicad-native-desktop.log): KICAD_STARTUP_DIRECT_MM_ALIGNMENT_SOURCE_PROJECT_ROUNDTRIP_OK and KICAD_REAL_IPC_PACKAGE_FOUR_ROLES_DRC_ACK_ALIGNMENT_OK; imported four roles, gated DRC errors with explicit acknowledgement, checked hole alignment, saved/reopened provenance. Both screenshots kicad-transfer-smoke.png and kicad-real-import-smoke.png inspected. Real sample has307 errors,84 warnings,0 unconnected: export/import verification, not DRC design acceptance. Initial concurrent startup timeout and float assertion failure retained in central tracker; final serial journey passes with original120s watchdog and0.001mm parser bounds tolerance.

Local installer PASS in real Windows Documents known folder: C:/Users/ozkur/OneDrive/Documents/KiCad/10.0/plugins/org.mikrocam.bridge. Published source bytes match, CAM interpreter/configured checkout exist, API already enabled so its settings were unchanged. Existing unrelated plugin files/settings preserved; reinstall backup behavior unit-tested. Restart PCB Editor to discover action and provision its isolated optional Python environment.

Final complete suite, exact-head Windows CI and main delivery remain pending; no prior PASS inherited. No physical serial port opened.
