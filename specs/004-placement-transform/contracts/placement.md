# Core placement API

- `Placement(...).matrix` returns `(a,b,d,e,xoff,yoff)` such that
  `x' = a*x + b*y + xoff`, `y' = d*x + e*y + yoff`.
- `apply_point(point)` returns an immutable `(x,y)` tuple in mm.
- `apply_points(points)` returns a tuple of transformed points, preserving order.
- `apply_geometry(geometry)` returns new planar Shapely geometry with the same placement.
- `inverse()` returns a Placement that maps output coordinates back to input coordinates.
- Invalid argument values raise ValueError; an unsupported geometry object raises TypeError.
- Dataclass values are immutable; no global state, I/O, UI, host or controller dependency.
