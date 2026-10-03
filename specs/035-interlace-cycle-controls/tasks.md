# Tasks — Doğrulanmış native tur, sıra değişimi ve bekleme

Hikâyeler: **V4-US1** tam tur tekrarı; **V4-US2** tur sırası değişimi; **V4-US3** desteklenen profilde geçişler arası bekleme. Bağımlılık: V3. Kontrollerin gerçek native desteği ayrı ayrı tamamlanır.

- [ ] T001 [US1] D01 `tests/test_visual_interlace.py`: R turda her piksel R kez, etkin/boş geçişler ve kapasite sınırı; `0,1,2,0,1,2` oracle'ını yaz. Kabul: T38.
- [ ] T002 [US1] D02 `core/visual_interlace.py + laser/visual_plan.py` plan genişlemesi ve `lightburn_export.py` R*N ayrı katman yazımını uygula. Profilin ölçülmüş kapasitesini aşma. Kabul: D01 ve hedefte iki tur Preview sırası doğru.
- [x] T003 [US2] D03 `tests/test_visual_reference.py` ile tura göre grup kimliği kaydırmasını ve recipe round-trip'i test et; sonra `core/visual_interlace.py + laser/visual_plan.py`, `laser/visual_recipe.py + bridge/visual_recipe.py` davranışını tamamla. Kabul: T39 ve sözleşmedeki üç örnek sıra.
- [ ] T004 [US3] D04 G02 prosedürünü native dwell için genişlet. `tests/reference/lightburn/<profile_id>/` içine before/after ayar dosyası ve Preview kanıtı ekle. Kabul: gerçek süre/bekleme davranışı kanıtlı veya yetenek açıkça unsupported.
- [ ] T005 [US3] D05 `tests/test_visual_reference.py` ve `tests/integration/test_lightburn_dwell.py` yaz; sonra doğrulanmış profil alanını uygula. Kabul: T40; `max(etkin_geçiş-1,0)*delay`, lazer kapalı, son geçişte ek dwell yok. Destek yoksa hata yolu test edilir ve bu altözellik tamamlandı sayılmaz.
- [ ] T006 [US1] D06 `ui/visual_interlace_panel.py` tur/sıra/bekleme kontrollerini capability'ye göre etkinleştir; etkin geçiş sayısını ve toplam dwell'i göster. Kabul: desteklenmeyen kayıt kaybolmadan açılır; export gerekçesi açıklanır.
- [ ] T007 [US2] D07 Hedef uygulamada kayıt/aç, iki tur ve mixed sıra kabul testlerini çalıştır; destek tablosu ve Türkçe kullanım metinlerini güncelle. Kabul: her iddia profile özgü kanıtlı, eski tek tur çıktısı değişmemiş.

Ortak G01/G02 ve açık alt kanıtlar: [master görevler](../../docs/design/visual-interlace/tasks.md).
