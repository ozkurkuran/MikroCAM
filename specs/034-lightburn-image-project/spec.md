# Feature specification — Doğrulanmış tek LightBurn Image projesi

Dal:032-visual-interlace, base `c5a666cf`. Bu dilim tek entegrasyon worktree'sinde tutulur.
Genel sözleşme: [24 gereksinim](../../docs/design/visual-interlace/spec.md).

## User scenarios and acceptance

### US1 — Native gömülü görüntü projesi üretme

Öncelik:P1. Gereksinimler:FR-014. Bağımsız kabul, tasks.md içindeki [US1] test ve uygulama çiftleridir.

### US2 — Ölçü/sıra/piksel satırını gerçek uygulamada doğrulama

Öncelik:P2. Gereksinimler:FR-008,011,012,015,022. Bağımsız kabul, tasks.md içindeki [US2] test ve uygulama çiftleridir.

### US3 — Uyumluluk sınırlarını açık bildirme

Öncelik:P3. Gereksinimler:FR-021,024. Bağımsız kabul, tasks.md içindeki [US3] test ve uygulama çiftleridir.

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
