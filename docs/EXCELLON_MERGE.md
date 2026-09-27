# Reviewed Excellon merge

Select two or more Excellon objects and open **Plugins → Review Excellon merge...**.
Choose **Analyse selected Excellons**. Inspect the physical tool diameters, drill/slot counts,
complete source tool mapping, removed duplicates and blocking conflicts. Enter a new object
name and explicitly create the reviewed merge. The new object uses current application
defaults; each source retains its own settings and original text.

The current per-tool `tooldia`, drill Points, slot endpoint pairs and explicit object units
are authoritative. Sparse programmatic drill-only tools may omit `slots`; slot-only tools may omit
`drills`. The normal file parser supplies both keys at completion. An absent key means empty. A present malformed sequence or wholly empty tool fails
analysis. Cached `solid_geometry`, `units_found` and historical source text never determine
operations. Mixed MM and IN sources are normalized to physical mm once, then the shared
factory converts to current destination units once. No source reparse or position transform.

Exactly equal physical diameters share a sequential output tool, sorted by diameter. Exact
duplicate holes share both diameter and centre. Exact duplicate slots share diameter and
endpoints, allowing reversed direction; the first retained slot keeps its original direction.
Every removed operation is mapped to its retained source/tool/operation. Nearby centres,
different diameters and short nonzero slots are not silently merged, resized or snapped.

Equality is exact after floating-point unit normalization. For example, 0.3 inch can normalize
to 7.619999999999999 mm, which differs from a literal 7.62 mm. Such operations remain distinct
and overlapping ones block creation. The diameter table displays enough digits to distinguish
them. This conservative first version does not provide an approximate fusion tolerance.

Footprints are analytic capsules: a round hole is a point with tool radius, and a straight
slot is an endpoint segment with tool radius. Any centreline distance less than the sum of
radii is a conflict. This detects drill/drill, drill/slot and slot/slot intersections without
tessellated-buffer approximation. Tangency is allowed. Same-centre holes with unequal
diameters are identified explicitly. All conflicts block creation; only the first 200 details
are displayed, alongside the complete conflict count. Correct source operations and analyse
again instead of choosing an arbitrary winner.

The review is ephemeral. Source membership and complete freshly recomputed review equality
are checked inside factory initialization before destination changes, then again after local
export and before publication. Changing names, units, tool IDs, diameters or operations, or
removing/replacing a source, requires another analysis. A failed initialization/export does
not publish a partial result. No source is deleted or modified by this workflow.

Limits are 2–64 sources, 1,000 total input tools and operations, and 1,000 output operations;
each source/tool must contain operations. Coordinates and positive diameters are bounded to
1e9 mm. Only valid finite planar Points and nondegenerate straight slots are accepted.
There are at most 499,500 pair comparisons. No hardware connection, new dependency or new
project format is involved. The original legacy merge remains independently available.

Normal project persistence retains unquantized drills and slots. Export/reparse accuracy is
limited by the normal exporter: metric tool diameters use two decimal places, inch tools four,
and coordinates use configured precision. A diameter rounded to zero in the generated tool header
blocks publication with a clear export-precision error. Validation uses those output quanta and existing
legacy inch-conversion roundoff. This is an independent extension of MikroCAM's shared
Excellon factory; no external source module was copied. No physical drilling is claimed.
