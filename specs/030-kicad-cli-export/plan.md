# Plan030
## Constitution Check
I yes: core schema pure stdlib; kicad domain only core; bridge uses domain+existing importer; thin Qt orchestration.
II yes: two small menu/startup seams, <50 net legacy lines. III yes: no new abstraction or app dependency; KiCad external executable.
IV yes: mm/absolute/no transforms; one schema version. V yes: fault tests before code; fake runner plus native QA. VI yes: import only, hazard analysis.
VII yes: original implementation, official CLI reference only; no external source copied. VIII yes:3 stories/16 tasks.
## Design
core/kicad_transfer.py immutable schema and strict codec. kicad/package.py bounded ZIP I/O; kicad/export.py subprocess snapshot/DRC/export; kicad/__main__.py command-line helper.
bridge/kicad_transfer.py validates package bytes against manufacturing inspection and prepares immutable review with generated role assignments.
ui/kicad_transfer.py extends existing file-set dialog for DRC acknowledgement, export worker and archive lifetime. appMain startup/menu short connection only.
Failure ownership: temporary snapshot/output are worker-owned; reader lifetime belongs to visible dialog until import finishes. Failed parse keeps successful objects as existing manufacturing policy.
No Complexity Tracking exceptions. Performance bounds:64files,16MiB per member,64MiB total,256KiB manifest,60s per CLI command.
