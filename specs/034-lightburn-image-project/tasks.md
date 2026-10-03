# Tasks — Doğrulanmış tek LightBurn Image projesi

Hikâyeler: **V3-US1** native proje üretme; **V3-US2** sıra/ölçü/piksel eşleşmesini doğrulama; **V3-US3** uyumluluk sınırlarını kullanıcıya doğru bildirme. Bağımlılık: V1, G02; genel görsel ürün teslimi için V2 de tamamlanır.

- [ ] T001 [US1] C01 `tests/integration/test_lightburn_export.py` ve `test_lightburn_profile.py`: G02 fixture'larından beklenen native alan, katman referansı, bitmap decode ve kapasite testlerini önce yaz. Kabul: T30,T31.
- [ ] T002 [US1] C02 `laser/lightburn_profile.py`: ilk kanıtlı profil verisini ve `validate_export` hata sonuçlarını yaz. Device/version/fixture digest zorunlu. Kabul: doğrulanmamış profile export engelli.
- [ ] T003 [US1] C03 `laser/lightburn_export.py`: 1 tur, N=1..8, ortak placement ve gömülü görüntülerle atomik native yazımı uygula. Kabul: C01; N=1 piksel eşitliği ve N=3 ölçüleri doğru.
- [ ] T004 [US2] C04 `tests/integration/test_lightburn_semantics.py`: mixed sıra, Output kapalı boş grup, crop edilmemiş tuval, Negative kapalı ve geçiş başına tekrar=1 testlerini ekle. Kabul: T32,T33.
- [ ] T005 [US2] C05 Hedef LightBurn'de Open->Save->Open->Preview kabul prosedürünü yürüt. Sürüm/device, 13×10 ve 600×360 örnekleri, beyaz satır atlama ve scan yönü kanıtlarını manifeste yaz. Kabul: T34,T35; yazılım uyumluluğu XML testinden ayrı kanıtlı.
- [ ] T006 [US3] C06 `ui/visual_interlace_panel.py` export ayarları/raporu, bilinmeyen profil, eksik recipe ve boş maskeyi bağla. Kabul: T36; kullanıcıdan güç/hız tahmini yapılmıyor.
- [ ] T007 [US3] C07 `tests/integration/test_lightburn_export_failure.py`: iptal, disk yazma hatası, hash uyuşmazlığı ve desteklenmeyen yön isteğinde önceki dosyanın korunmasını test et. Kabul: T37.
- [ ] T008 [US2] C08 V1+V2+V3 uçtan uca demo: PNG/SVG/PDF'den `.lbrn2` üret, hedefte aç, settings ve görselleri karşılaştır. `docs/lightburn-compatibility.md` doğrulanmış destek tablosunu ekle. Kabul: ana ürün hedefi tamam; makine ateşleme gerekmez.

Ortak G01/G02 ve açık alt kanıtlar: [master görevler](../../docs/design/visual-interlace/tasks.md).
