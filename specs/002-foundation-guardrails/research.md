# Research: Foundation guardrails

## Dependency checks

Decision: inspect Python AST without importing checked modules. Resolve absolute/relative
imports, package initializers, aliases and literal importlib/builtin dynamic imports; reject
unresolved dynamic targets. Enforce the constitutional layer matrix and core's stdlib,
NumPy/Shapely allowlist. Package root remains stdlib-only. Hardware-facing stdlib imports
are excluded from core. This is a development check, not a sandbox against hostile code.

Rationale: deterministic checks do not need Qt or side effects. Synthetic bad modules prove
the guard fails even while the initial core is empty. Alternatives: import-linter adds a
dependency; runtime import hooks execute code and miss unexecuted paths; regex misses syntax.

## Legacy growth

Decision: record top ten application Python modules at slice 001, verify the record against
its immutable Git revision, then compare current contents with the feature's Git base.
CI supplies a base SHA (PR base, push previous revision); local feature branches use merge-base
with origin/main. If already at main, use the first parent to check the latest change.
Track renames using Git and fail on unavailable history or missing/malformed baseline.

Rationale: +50 is per feature, not a lifetime ceiling. Line counts use splitlines so platform
newline translation is irrelevant. Signed reductions offset additions as the constitution says.
Alternatives: manually updating baseline each feature hides growth; always comparing against
the first release incorrectly accumulates unrelated changes. Exceptions stay explicit failures
until a reviewed plan justification and narrowly scoped guard adjustment accompany them.

## Hosted validation and packaging

Decision: Windows Actions with checkout full history, setup-python reading .python-version,
existing pip pins, pip check, offscreen pytest, and retained JUnit results. Read-only repository
permissions. A minimal PEP 621 project declaration supplies name, version and requires-python;
requirements remain authoritative and this slice does not introduce a wheel distribution.

Rationale: this reproduces the clean core environment already proven in slice 001. Desktop
OpenGL smoke remains a separate manual check when UI changes. No speculative Linux support.
