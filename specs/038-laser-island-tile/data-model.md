# Data model

## IslandSettings (`mikrocam.core.laser_paths`)

| Alan | Tip | Kural |
| --- | --- | --- |
| tile_size_mm | float | sonlu, > 0, ≥ `PlanOptions.spacing_mm` |
| overlap_mm | float | sonlu, 0 ≤ x < tile_size_mm (komşular arası toplam) |
| angle_step_deg | float | sonlu; tek parite döşemelere eklenir |
| order | str | `checkerboard` veya `raster` |

`PlanOptions.island: IslandSettings | None = None`; None önceki davranıştır. Ada hatch ister.

## IslandTile (`mikrocam.core.laser_islands`, geçici)

`column`, `row` (orijine sabit tam sayı indis), `angle_deg`, `paths` (kaynak mm
`LaserPath` hatch parçaları; aile → tarama indisi → x sırası). `parity = (column+row) mod 2`.
Dosyaya yazılmaz; planner döşemeleri sırayla düzleştirir.

## Export manifest şema 3 (`mikrocam.laser-export`)

v1 alanları + `island` (nesne veya null) + `device` (nesne veya null). `island` alanları
tam olarak `tile_size_mm`, `overlap_mm`, `angle_step_deg`, `order`. `device` null ise
pass ayarları v1 dört alanıdır; değilse v2 profil alanlarıdır.

| Yazılan | Koşul |
| --- | --- |
| v1 | ada yok, cihaz profili yok (değişmedi) |
| v2 | ada yok, cihaz profili var (değişmedi) |
| v3 | ada var (cihaz profili olsun olmasın) |

Migration: `upgrade_manifest(data)` v1/v2 → v3 (`island: null`, `device` korunur veya
null); v3 kopyalanır. Okuyucu 1/2/3 dışını reddeder. Reçete ve job JSON değişmez.
