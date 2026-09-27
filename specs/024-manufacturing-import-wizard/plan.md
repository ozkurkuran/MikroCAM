# Implementation Plan: Manufacturing file set review

Branch024-manufacturing-import-wizard | Date2026-09-27 | [Spec](spec.md)

## Summary

Add a parent-owned multiple-file drop/select wizard. Inspect immutable bounded Gerber/Excellon
bytes, expose content/metadata/filename evidence, require explicit compatible assignments, and
import selected files in one sequenced worker. Stop on the first failed row, retain successes,
and require renewed review for pending rows. Persist optional source/layer evidence per object.

## Technical Context

Pinned Python3.13/PyQt6/NumPy/Shapely; no new dependency. Existing Gerber/Excellon parsers and
normal AppObject factory remain the geometry/unit/default authority. Domain code inspects bytes
and tokenizes Gerber statements without I/O; bridge owns files, original bytes and factory calls.
UI owns drop events, editable rows, review invalidation and existing worker dispatch/signals.
Gerber/Excellon source_file stores lossless Latin1 original bytes; optional manufacturing_source
schema1 stores bounded historical classification evidence. Existing SVG/PDF/CAD reports unchanged.

Bounds:64 paths,16MiB/file,64MiB/set,100000 Gerber statements/Excellon lines,1MiB individual
statement,32 evidence items/20 issues,256-byte names,4096-byte paths,64KiB persisted report.
File paths must resolve to regular files. Metadata uses bounded complete markers; source parsing
uses the same immutable bytes that were inspected. These are input limits, not new complexity
guarantees for the legacy geometric parsers. Their reported fail/defective results stop publication.

## Constitution Check

All eight gates YES before and after design:
1. Core records/codec, importers byte classification/tokenization, bridge file/factory, UI Qt.
2. Short menu and optional Gerber/Excellon field/serialization/UI hooks only, within+50 legacy lines.
3. Concrete reuse of existing parsers/factory; no registry, job engine, transactional rollback or new dependency.
4. Source coordinates unchanged; normal host unit conversion once, classification separate from Placement.
5. Tests precede classification, tokenizer, source guards, failures and state transitions.
6. No controller action. Explicit file-role review and accurate per-file outcomes; source/defaults preserved.
7. Independent classification from format docs and existing MIT parser reuse; no external code copied.
8. Three stories and39tasks. Sol owns records/codec/UI and independent classifier; root integrates boundary.

## Structure

mikrocam/core/manufacturing_models.py: bounded immutable evidence, inspection, file, assignment,
review and report records. manufacturing_codec.py: strict optional schema-one report codec.
mikrocam/importers/manufacturing_classify.py: conservative source/filename proposals and conflicts.
mikrocam/importers/gerber_statements.py: bounded statements preserving macros and compact commands.
mikrocam/bridge/manufacturing_import.py: inspect files, exact revalidation, sequential guarded
normal factories and receipt iterator. Additional concrete helper module only if function limits require.
mikrocam/ui/manufacturing_import.py: dialog/drop/review/worker state; manufacturing_report.py:
collapsed per-object source/layer evidence. appMain/GerberObject/ExcellonObject get short hooks.
tests/test_manufacturing_*.py, tests/test_gerber_statements.py and smoke_manufacturing_import.py.
docs/MANUFACTURING_IMPORT.md plus validation.md record evidence and limits.

## Complexity Tracking

No exception. Review proposes layer roles; it does not validate PCB stackups, align boards, merge
files, infer plating from geometry or alter bottom-layer coordinates. One file remains one object.
Gerber drill artwork stays Gerber: a layer role is not an automatic Excellon conversion request.
