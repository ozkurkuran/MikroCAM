# Research: Placement transform

Decision: source origin is subtracted before mirror and CCW rotation; translation is the
destination of that origin. Rationale: the same board datum maps to the fixture datum regardless
of orientation. Alternative rejected: rotating after destination translation unexpectedly rotates
the fixture offset. A bottom flip negates the local X coordinate (reflection about local Y).

Decision: expose the conventional six 2D affine coefficients `(a,b,d,e,xoff,yoff)` as the shared
definition for point and Shapely geometry APIs. Rationale: geometry and point consumers cannot
drift into separate transform math. Alternative rejected: a separate matrix hierarchy adds no value.

Decision: inverse returns another Placement. The orthogonal mirror/rotation part is invertible
without numerical matrix inversion. Its translation/origin swap, its angle negates unless mirrored,
and the same mirror flag is retained. Tests verify this composition rather than trusting algebra alone.

Decision: accept finite real coordinates, normalize immutable point pairs to floats, reject bools,
Z geometry and non-finite geometry coordinates. Preserve empty geometries and reject invalid
polygon topology. Existing Shapely is reused; no new runtime dependency or external code port.
