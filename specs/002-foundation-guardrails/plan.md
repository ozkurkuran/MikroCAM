# Implementation Plan: Foundation guardrails

**Branch**: `002-foundation-guardrails` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)

## Summary

Create minimal `mikrocam` and `core` packages, project metadata, stdlib AST dependency
checks, a Git-aware legacy line ratchet and hosted Windows checks. No application behavior changes.

## Technical Context

- Language/runtime: standard CPython 3.13 x64; `.python-version` supplies CI's exact version.
- Dependencies: existing requirements-dev pins only; AST, pathlib, subprocess and JSON from stdlib.
- Storage: versioned `tests/architecture/legacy-baseline.json` anchors ten largest legacy modules
  at merged slice 001. It is not rewritten automatically to hide growth.
- Testing: pytest fixtures in temporary Git repositories and source trees; full existing suite offscreen.
- Platform/type: Windows primary, developer tooling for desktop application; no Qt in guard helpers.
- Performance: guard checks on tracked source complete within the normal unit run; no product SLA.
- Scope: 3 stories, 14 tasks; no feature packages beyond core, GUI changes or dependencies.

## Constitution Check

Pre-design and post-design checks both pass:

| Gate | Result | Evidence |
| --- | --- | --- |
| I: new logic location and direction | Yes | Product skeleton in mikrocam/core; development checks live under tests/architecture. |
| II: legacy fixes/wiring only, <=50 | Yes | No legacy application edits. |
| III/VII: justified abstractions/dependencies | Yes | Plain functions, no new dependency. |
| IV: single sources/versioned persistence | Yes | Python version file retained; baseline JSON has schema_version 1. No user-data format. |
| V: hardware/display free and test first | Yes | Synthetic boundary/ratchet tests before helpers, full offscreen suite. |
| VI: machine/laser analysis where relevant | Yes | No movement or emission behavior. |
| VII: licenses/provenance/clean room | Yes | Independently authored checks, no external source copied. |
| <=3 stories and <=40 tasks | Yes | Three stories, fourteen tasks. |

## Project Structure

```text
mikrocam/__init__.py, mikrocam/core/__init__.py
pyproject.toml
tests/architecture/
  imports.py, growth.py, legacy-baseline.json
  test_import_boundaries.py, test_legacy_growth.py, test_runtime_metadata.py
.github/workflows/ci.yml
docs/DEVELOPMENT.md
specs/002-foundation-guardrails/{spec,plan,research,data-model,quickstart,tasks,validation}.md
```

## Complexity Tracking

No exceptions. Test tooling may invoke Git and inspect source; those developer operations
are outside the runtime core and do not import it or the legacy application.
