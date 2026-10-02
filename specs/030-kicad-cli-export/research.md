# Research, 2026-10-02
Installed CLI10.0.6 verified. Official10 CLI supports pcb drc --format json, --refill-zones/--save-board, pcb export gerbers and drill --excellon-separate-th, decimal/mm/absolute. Default Gerber absolute matches drill absolute; X2 roles inspected again by existing importer.
Sources: https://docs.kicad.org/10.0/en/cli/cli.html ; https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/ . KiCad10 IPC exports unavailable, so031 calls030 CLI. No jobset needed for one fixed, testable production workflow.
Existing ManufacturingImportDialog/worker and bridge guard bytes before publication, preserve source_file/manufacturing_source and stop first failure. Reuse rather than second parser/owner.
ZIP schema1 and hash are local integrity/provenance, not authenticity. Reader validates all bounded entries before any extraction/import; no extractall. Snapshot/pro files maintain DRC context and refill does not modify originals.
