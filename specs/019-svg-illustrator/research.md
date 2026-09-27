# Research: Illustrator SVG appearance

## Source behavior and reproducibility
Neo MIT head914630319725b0d6034801f4808ae345d53b407b: ParseSVG.py
svg_read_xmp_max_page_size/svg_physical_scale/svg_source_advisor; svg_node_is_visible;
svgcompound_fillrule2shapely. Relevant commits9b73859dea7705b1c7ccaac614d2d05de1e05ca4,
c1e01850fac318126338cc27ba995100dd86ef46,181c1f2a28d9a03675c4ee42bec234494bfe63e1.
The repo has no relevant SVG fixtures/tests; README/CHANGELOG reference unshipped Prueba2/AI
manual drill files. Claims there cannot establish vendor compatibility. Existing MIT notice retained.
Decision: independently implement bounded semantics and original analytic fixtures, no module copy.

## Physical metadata
Adobe specifies [MaxPageSize](https://developer.adobe.com/xmp/docs/xmp-namespaces/xmp-t-pg/)
and [Dimensions](https://developer.adobe.com/xmp/docs/xmp-namespaces/xmp-data-types/dimensions/)
with stDim w/h/unit, namespace http://ns.adobe.com/xap/1.0/sType/Dimensions#.
Decision: strict known namespace and one complete structure; accept element fields or RDF attribute
fields, reject duplicates/ambiguity. Map documented unit names plus Neo's Millimeters convention.
Use only unavailable dimensions (absent or percentage without external viewport); preserve explicit
absolute/unitless/px dimensions and report conflict. No average of X/Y factors as in Neo.
Original percentage tokens require report schema2, with strict schema1 migration; effective root
attributes stay separate from raw source facts. Existing source text remains byte-equivalent.

## Styles and layers
Existing display:none/opacity0 and inherited visibility already handle hidden layers. Retain group
labels/IDs in source evidence and bounded notices rather than adding a second layer editor.
Common Illustrator exports use .stN rules. Support simple .class/#id/tag/* and comma lists, bounded
rule text/count, declaration order, specificity, inline and important precedence. Reject external,
conditional, escaped/combinator/attribute selectors and unsupported declarations explicitly.
[CSS cascade](https://www.w3.org/TR/css-cascade-3/) is the reference for precedence.

## Compound material
Decision: preserve fast valid non-touching nesting; crossing/touching/self-crossing fill uses bounded
noded linework, polygonized faces and signed winding at each representative point. Evenodd uses
parity, nonzero uses winding!=0. No make_valid/buffer(0) repair guessing. Preflight segment-pair work,
face/coordinate limits and winding-operation budget prevent pathological expansion.

## Clipping
[SVG clipping](https://www.w3.org/TR/SVG11/masking.html#ClippingPaths) defines local clip coordinates,
union among clip child silhouettes, intersection across ancestor applications, and clip-rule
inherited from definition ancestors, not the target. Fill/stroke/opacity do not define clip silhouette;
display/visibility matter. clip-path is not inherited; parent application still limits its subtree.
[Bounding-box units](https://www.w3.org/TR/SVG11/coords.html#ObjectBoundingBox) use unclipped geometry
without stroke width. Decision: use shared application IDs and original path bounds transformed back
to the reference frame for whole-group bbox; apply clips after all original render results exist.
Clip shapes retain local matrices and definition styles; the application matrix is transformed once
with vertical flip. Reject nested clipping inside definitions, missing/external refs and degenerate
bbox explicitly. Ordinary SVG may ignore invalid refs; CAM intentionally fails instead of leaking
unclipped material. Drill detector refuses clipped elements because source circles alone are no
longer evidence of a full visible hole. Source paths remain historic facts for reports.

No unresolved design research. No authentic Illustrator export or physical manufacturing validation
is claimed; original analytic data and existing corpus are the available reproducible evidence.
