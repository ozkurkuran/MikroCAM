# Third-party changes

## 2026-09-26 — FlatCAM Evo Beta_1.0 baseline

- Source repository: https://bitbucket.org/marius_stanciu/flatcam_beta
- Source branch and commit: `Beta_1.0`, `e046a2a33926003765f83d6402b96fe6c5c3bcf7`.
- Previous fork baseline: `mekatrol/flatcam` at `d0a86cf4f1ac41a206b20f316d4a29f28a93bbff`.
- License: MIT, as recorded in the upstream `LICENSE`; copyright notices retained.
- Reason: user-selected current Evo baseline for the Python 3.13 compatibility slice.
- Files: the 208 upstream changed paths between these commits; exact inventory is available
  with `git diff --name-status upstream-evo-baseline upstream-evo-beta1-baseline`.
- Changes made during import: none; a fast-forward retained all 61 upstream commits unchanged.
- MikroCAM commit: `e046a2a33926003765f83d6402b96fe6c5c3bcf7` (same commit after fast-forward).
- Verification: baseline tags point to the original commits; source branch and selected tag
  match. Runtime verification remains part of `001-evo-py313-baseline`.

Later documentation changes import MikroCAM's own Spec Kit files and replace the root
contributor guide. The upstream guide remains available at `upstream-evo-beta1-baseline:CLAUDE.md`.
