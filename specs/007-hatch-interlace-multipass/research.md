# Research: Interlace and multiple passes
- 006 paths preserve original scan_index and family, including gaps from clipping. Grouping
  by list position would incorrectly split the two sides of a hole; use scan_index modulo N.
- Python modulo gives nonnegative residues for negative indices; document/test this rule.
  Sort only occupied groups, avoiding an N-sized loop for sparse rows.
- Recipe values already enforce finite positive parameters, power <=100 and unique names.
  UI is an editor for these values; it must not invent material/device ranges or defaults.
- Schema1 already has ordered passes with all parameters; no migration or format change needed.
- Paths are common to each pass in this slice. Sharing an immutable tuple avoids multiplying
  potentially 200,000 paths in memory. Export can iterate pass_plans in recipe order.
- Existing generation disables input container; programmatic edits still cancel/invalidate.
  Editor changes feed that same pathway. The source boundary and single placement stay intact.
