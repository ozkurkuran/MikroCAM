"""Compose source contours and hatch, then apply the shared job placement once."""
from dataclasses import replace

from mikrocam.core.laser_geometry import contour_paths, hatch_paths, selected_area
from mikrocam.core.laser_job import LaserJob
from mikrocam.core.laser_paths import (CancelCheck, CopperFeatures, LaserPlan, PlanOptions,
                                      check_cancelled, check_path_count)
from .interlace import interlace_paths


def plan_laser(job: LaserJob, options: PlanOptions, features: CopperFeatures | None = None,
               cancelled: CancelCheck = None) -> LaserPlan:
    """Return a complete immutable placed plan, or an explicit error/cancellation."""
    if not isinstance(job, LaserJob) or not isinstance(options, PlanOptions):
        raise ValueError('Planning requires LaserJob and PlanOptions')
    features = CopperFeatures(job.region) if features is None else features
    if not isinstance(features, CopperFeatures) or features.copper != job.region:
        raise ValueError('Feature source copper must match the job copper')
    check_cancelled(cancelled)
    paths = list(contour_paths(features, options.contour_mode, cancelled))
    if options.hatch:
        area = selected_area(features, options.region_mode)
        paths.extend(hatch_paths(area, options.spacing_mm, options.angle_deg, options.cross_hatch, cancelled))
    check_path_count(len(paths))
    paths = interlace_paths(tuple(paths), options.interlace_n, cancelled)
    placed = []
    for path in paths:
        check_cancelled(cancelled)
        placed.append(replace(path, points=job.placement.apply_points(path.points)))
    check_cancelled(cancelled)
    return LaserPlan(job, options, tuple(placed))
