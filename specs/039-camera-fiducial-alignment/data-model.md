# Data model — Fiducial hizalama

## Placement (genişletilmiş, `mikrocam/core/placement.py`)
- `origin`, `translation`, `rotation_deg`, `mirror_x` — değişmedi.
- `affine: (a, b, d, e, xoff, yoff) | None` — yeni. Verildiğinde diğer alanlar varsayılan
  olmalı; sonlu ve |det| > 1e-12. `matrix` bu katsayıları döner; `inverse()` tersini üretir.
- `rigid_data()` — rijit alanları dict olarak verir; affine ise ValueError (rijit saklayan
  formatlar için).

## FiducialPair (`mikrocam/core/fiducial.py`)
`name` (1..64 yazdırılabilir), `design_mm` (Point2D), `machine_mm` (Point2D | None),
`enabled` (bool).

## AlignmentPolicy
`method` ∈ {rigid, similarity, affine}; `max_residual_mm` (0, 10]; `max_scale_deviation`
[0, 0.1]; `min_separation_mm` (0, 10000].

## AlignmentFit
`method`, `policy`, `placement` (Placement), `residuals` (PairResidual…), `rms_mm`, `max_mm`,
`rotation_deg`, `observed_scale`, `axis_scales` (σ1, σ2), `determinant`, `redundancy`,
`reasons` (ret), `warnings`; `accepted` = reasons boş; `require_placement()`.

`PairResidual`: `name`, `design_mm`, `machine_mm`, `fitted_mm`, `error_mm`, `magnitude_mm`.

## FiducialSet (`mikrocam/core/fiducial_codec.py`)
`name`, `policy`, `pairs`. JSON:

```json
{"kind": "mikrocam.fiducial-set", "schema_version": 1, "units": "mm", "name": "...",
 "method": "affine",
 "policy": {"max_residual_mm": 0.05, "max_scale_deviation": 0.005, "min_separation_mm": 10.0},
 "pairs": [{"name": "F1", "design_mm": [0, 0], "machine_mm": [10, 20], "enabled": true}]}
```

## AlignedJobResult (`mikrocam/core/aligned_job.py`)
`original_source`, `original_report`, `g54_offset_mm` (XYZ; Z = setup.z_offset_mm),
`chord_error_mm`, `prepared_job` (PreparedJob, öteleme-yalnız), `lineage`.

## Makine yakalama (`mikrocam/machine/fiducial_capture.py`)
`capture_machine_xy(snapshot) -> Point2D`; `capture_work_offset_xy(snapshot) -> Point2D`.
Yalnız okuma; uygun değilse ValueError.
