# Data model

This compatibility slice adds no runtime model or persistent schema.

| Entity | Fields / source | Invariants |
| --- | --- | --- |
| Working baseline | upstream tag, Python patch, pinned packages | Standard 3.13 x64; identical installed versions in two clean environments |
| Reference CAM job | fixed Gerber/Excellon, isolation parameters, four named objects | Nonempty geometry/G-code; saved and reopened names, kinds and G-code match |
| Validation record | commands, environment, counts, warnings, baseline hashes | No failed/omitted check is represented as passing |

Existing Evo project serialization remains authoritative. Smoke transitions are load →
isolate → generate CNC → save → reopen → render → normal shutdown. Failure at any stage
returns a nonzero process status and cannot count as a completed journey.
