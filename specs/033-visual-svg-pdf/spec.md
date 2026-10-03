# Feature specification — Aynı iş akışında SVG/PDF ve isteğe bağlı bakır kaynağı

Dal:032-visual-interlace, base `c5a666cf`. Bu dilim tek entegrasyon worktree'sinde tutulur.
Genel sözleşme: [24 gereksinim](../../docs/design/visual-interlace/spec.md).

## User scenarios and acceptance

### US1 — Statik SVG görünümünü kullanma

Öncelik:P1. Gereksinimler:FR-003. Bağımsız kabul, tasks.md içindeki [US1] test ve uygulama çiftleridir.

### US2 — PDF seçili sayfayı kullanma

Öncelik:P2. Gereksinimler:FR-004. Bağımsız kabul, tasks.md içindeki [US2] test ve uygulama çiftleridir.

### US3 — Mevcut bakır/poligon ve açık ROI kullanma

Öncelik:P3. Gereksinimler:FR-001,002. Bağımsız kabul, tasks.md içindeki [US3] test ve uygulama çiftleridir.

## Scope and invariants

Kaynak bytes detached; bir master mask; her grup aynı W,H,pitch,placement.
Her satır r%N grubunda; her kazıma pikseli turda bir kez; N=1pixel-identical.
Boş satırlar yeniden indekslenmez. H<N ve H%N!=0 geçerlidir. Proje kaydı kaynak
yolu bağımlılığı taşımaz. Gerçek LightBurn yürütümü yalnız native profil kanıtıyla.

## Success criteria

Tasks ve validation kanıtı aynı kaynak revizyonuna ait olmalı. Bir UI/PNG başarısı
native .lbrn2 kabulü değildir. Üretim ölçüsü ve maskeyi thumbnail'dan türetme.

## Out of scope and hazards

OCR, PDF vektör extraction, yeniPCB CAM algoritması, yeni nesne/format/registry,
fiziksel makine/lazer iletişimi yok. Yanlış ölçek/ayna/ters renk/sıra riski grid,
asimetrik maskeler ve hedef uygulama roundtrip'iyle ele alınır. Güç/hız tahmin edilmez.
