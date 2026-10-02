# MikroCAM Bridge for KiCad10

Standalone IPC toolbar action. It snapshots the current named PCB (including unsaved edits) with SaveCopyOfDocument, exports a versioned production package through MikroCAM’s CLI helper and opens MikroCAM. The original design remains unchanged. No CAM app imports, machine movement or laser action.

## Install on Windows
From the MikroCAM checkout with its validated Python3.13 environment:
```powershell
.\.venv\repro-a\Scripts\python.exe -m mikrocam.kicad.install_plugin
```
The installer resolves the real Windows Documents known folder and publishes `KiCad/10.0/plugins/org.mikrocam.bridge`. It records the checkout and Python paths in config.json and enables the API server in `APPDATA/kicad/10.0/kicad_common.json`, preserving all other keys. Existing bridge files and changed settings are backed up. Bridge backups live beside the plugins directory so KiCad cannot load them as duplicate actions.

Restart PCB Editor. KiCad prepares the plugin’s isolated Python environment from pinned requirements.txt; the MikroCAM µ button appears when dependencies are ready. The action is **Send to MikroCAM**. A new unnamed board must be saved once; subsequent unsaved edits are copied without saving over the original.

In MikroCAM, clean production files append to the current project. DRC errors/unconnected items pause import for review; use View DRC report, acknowledge and Import reviewed if you want CAM inspection. No coordinate mirror or placement is added. [Transfer guide](../../docs/KICAD_TRANSFER.md).

If Python plugin preparation fails, check PCB Editor Preferences→Plugins and KiCad’s warning messages. Select/recreate the Python environment if necessary. Export failures are reported in KiCad; no incomplete package is opened. Completed .mcam-transfer files are retained in the configured `.venv/kicad-transfers` folder for audit/retry. Move/reinstall the checkout by running the installer again; do not hand-edit token/socket values.

For a different installation location use `--plugins PATH --settings PATH --python PYTHON --transfers PATH`. Uninstall only `org.mikrocam.bridge`; restore the settings backup if you want the prior API setting. Backups contain only previous bridge files/configuration; unrelated plugins remain intact.

Official optional SDK kicad-python0.8.0 is MIT. All plugin dependencies are separately pinned; their license texts are retained in THIRD_PARTY_LICENSES/optional-kicad. No additions to CAM requirements.txt. Primary references: https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/ and the official KiCad10 plugin schema. This plugin implementation is original MikroCAM code.
