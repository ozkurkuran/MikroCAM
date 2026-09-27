# Quickstart

Use the pinned Python3.13 environment and dependencies. Run `python -m pytest -q`, then
`python tests/smoke_app.py` from this worktree. Feature tests are `tests/test_svg_drill*.py`.

In File / Import SVG drills, choose `tests/reference/svg-drills.svg`. Analyse with the desired
vertical flip. Review source identity, centres, diameters and heuristic notices. Select a subset,
name output, create Excellon. Export/reopen it and save/reopen the project. Check equal physical
measurements with mm/inch application units. Ordinary SVG import/source objects remain unchanged.
Cancel, no selection, malformed files, changed flip/path and conflicting holes must create nothing.

The fixture is original analytic Proteus-style artwork, not a real Proteus export. Record exact
runtime/CI heads, focused/full results and actual desktop evidence in validation.md; real vendor
sample and physical machining remain unverified unless separately exercised.
