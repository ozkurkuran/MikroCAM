# Feature 030: KiCad production package and direct import
2026-10-02; branch030-kicad-cli-export; user explicitly prioritizes direct KiCad→MikroCAM transfer over intervening laser roadmap slices.
## Clarifications / recorded decisions
- Target installed KiCad10.0.x, Windows first. No optional KiCad dependency in the CAM app.
- Default export F.Cu/B.Cu/Edge.Cuts and separate PTH/NPTH, mm decimal drill, common absolute origin, no mirror/placement.
- Existing project stays intact; incoming objects are appended with existing collision-safe names. No machine connection/start.
- DRC always runs; errors/unconnected items require explicit acknowledgement in import UI. Warnings visible. No error acknowledgement inferred from timeout.
- Empty optional copper/drill files are recorded and skipped; nonempty outline required. Malformed/failed exports never publish a package.
## User stories
1. P1: Open a saved .kicad_pcb from MikroCAM; generate production files and append them with known roles.
2. P1: Open a versioned transfer package from file menu/startup/existing-instance forwarding; verify bytes before any object import.
3. P2: See DRC results and retained source/provenance; errors can be reviewed and explicitly acknowledged without changing design.
## Functional requirements
FR001 CLI discovery/configurable executable and actionable missing/unsupported errors, support KiCad10 only initially.
FR002 Copy board and companion project/rules before commands; source untouched, detect changes, refill zones only in snapshot.
FR003 DRC JSON plus Gerber X2 and separate PTH/NPTH mm decimal, common absolute frame, bounded execution, no shell.
FR004 Schema1 package with board hash/name, KiCad version, origin/units, full DRC JSON/hash/counts, file hashes/kinds/roles and skipped empty names.
FR005 Atomic destination publication, bounded 64files/16MiB each/64MiB total; no symlinks, traversal, duplicate/extra/encrypted members, malformed schema/hash or future version accepted.
FR006 Validate complete archive before importing anything; revalidate extracted bytes through existing manufacturing review and worker.
FR007 Known format/role assignments, no invented placement/mirroring, append to current project, retain original source/report in saved project.
FR008 DRC error/unconnected acknowledgement required; warning summary and failure pending rows visible; first parser failure stops remaining files.
FR009 File menu and precise startup .mcam-transfer/.kicad_pcb recognition before legacy substring dispatch; no script execution.
FR010 Responsive worker export/import; closing blocked only while worker owns objects/files; temporary files cleaned after worker settles.
FR011 Real installed KiCad export and native desktop evidence; core/archive/CLI fault and UI tests run without KiCad in CI.
FR012 Optional dependency absence does not affect normal app startup; no hardware I/O.
## Acceptance / success
Saved PCB → export → import yields aligned copper, outline, drills with source role reports. Package tamper/traversal reject before object creation. DRC failures never masquerade as passed checks. Existing CAM journeys remain green.
## Hazard analysis
File import only; no machine/lasing. Never auto-clear project or change coordinates. Corrupt package, export interruption, source change and parser failure are explicit; no partial archive publication. DRC acknowledgement permits CAM inspection, not fabrication certification.
