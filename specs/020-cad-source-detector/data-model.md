# Data model: historical CAD source assessment

Frozen CadSourceEvidence(application, field, value): application in KiCad/Illustrator/Inkscape/
Proteus/Unknown; field nonempty UTF8<=80chars; value nonempty UTF8<=512chars. Unknown value retains
an explicit producer field that names an unsupported or ambiguous application. No mutable fields.

Frozen CadSourceAssessment(source_name, source_format, source_sha256, application, status, evidence,
reason): name nonemptyUTF8<=256; formatSVG/DXF; sha lowercase64hex orNone only whenunavailable;
application supportedenum; statusidentified/unknown/conflicting/unavailable; evidence exacttuple<=32
of exact records without duplicates; reason nonemptyUTF8<=512. identified requires one known application matching all
evidence; unknown requires no known positive; conflicting requires >=2 distinct evidenceapplication
values (Unknown may participate); unavailable always application Unknown and empty evidence. All non-identified statuses require application Unknown. No partial positive on limits.

Codec schema_version1, exact record-field keys plus version; evidence JSONarray; stricttypes,
unknownversions/extrakeys rejected, <=65536canonicalUTF8bytes. Fresh detached containers each call.
Old owner.cad_source absent/None remainsNone, without recomputation. New objects persist optionaldict.
Geometry changes do not mutate historical assessment. No geometry fields in this record.
