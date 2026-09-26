# Placement value

`Placement(origin=(0,0), translation=(0,0), rotation_deg=0, mirror_x=False)` is frozen.
Origin and translation must each contain exactly two finite real, nonboolean numbers in mm;
they normalize to immutable float pairs. Rotation is a finite real, nonboolean degree value.
Mirror is strictly boolean. Positive rotation is counterclockwise in Cartesian XY.

For point p: `result = translation + R(rotation_deg) * M(mirror_x) * (p - origin)`.
No conversion to/from inches occurs here. Empty planar geometry is allowed; invalid topology,
non-finite geometry or Z/M dimensions are rejected explicitly. Source geometry is never modified.
No serialization schema is introduced until a job actually persists placement.
