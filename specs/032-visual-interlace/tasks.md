# Tasks — Bitmap açma, aynı ölçülü satır grupları ve taşınabilir iş

Hikâyeler: **V1-US1** resmi ölçülendirip maske hazırlama; **V1-US2** tamamlayıcı geçişleri inceleme; **V1-US3** PNG ve iş/proje kaydıyla çalışmaya devam etme. Bağımlılık: G01, roadmap 2/4/5.

- [x] T001 [US1] A01 `tests/test_visual_core.py`: ölçü/padding, 508 DPI, alpha, eşik, ters renk, NaN/negatif boyut ve immutable veri testlerini önce yaz. Kabul: T01,T02,T03,T04,T05.
- [x] T002 [US1] A02 `mikrocam/core/visual.py`, `core/interlace_job.py` tiplerini [veri sözleşmesine](../../docs/design/visual-interlace/data-model.md) göre ekle; mevcut Placement/LaserRecipe tiplerini kullan; poligon LaserJob değiştirilmez. Kabul: modeller Qt/legacy/Pillow import etmiyor. PASS: core/interlace testleri.
- [x] T003 [US1] A03 `tests/test_visual_bitmap.py`: 1-bit, palette-alpha, RGBA, RGB/JPEG, EXIF yönü, TIFF ve animasyon kare seçimi, bozuk/çok büyük dosya örneklerini yaz. Kabul: T06,T07,T08.
- [x] T004 [US1] A04 `bridge/visual_bitmap.py`, `importers/visual_source.py`, `core/visual_normalize.py` uygula. Pillow'ı `requirements-visual.txt` içinde sabitle, license notice ekle. Kabul: A01/A03 geçer; 1-bit eş ölçekte piksel kaybı yok.
- [x] T005 [US2] A05 `tests/test_visual_interlace.py` ve `tests/test_visual_reference.py` yaz. JSON referanslarını fixture'a kopyala. Kabul: T09–T15; tüm N ve seçilmiş/geniş H aralıkları.
- [x] T006 [US2] A06 `core/visual_interlace.py + laser/visual_plan.py`: row partition, mixed sıra, yön metadata'sı, boş grup sayımı ve lazy maskeyi uygula. Kabul: A05 geçer; N tam maskesi bellekte tutulmaz.
- [x] T007 [US2] A07 `core/visual_preview.py`, `ui/visual_preview.py`: ana maske/tek geçiş/renkli birleşim ve geçiş listesini ekle. Kabul: T16 (thumbnail zoom); üretim bitmap'i preview'den türetilmez.
- [x] T008 [US3] A08 `tests/test_visual_recipe.py`, `smoke_visual_app.py`, `test_visual_bitmap.py` yaz. Kaynak taşınması, hash, eski kayıt ve başarısız yazım dahil. Kabul: T17–T20.
- [x] T009 [US3] A09 `bridge/visual_png.py`, `laser/visual_recipe.py + bridge/visual_recipe.py` ve JSON schema dosyasını uygula. Gömülü kaynak/ana maske ve N=1 migration ekle. Kabul: A08; yeni `.mcam` formatı yok. PASS: schema 1 portable roundtrip; bilinmeyen hash/grid reddedilir.
- [x] T010 [US1] A10 `bridge/visual_workflow.py`, `ui/visual_interlace_panel.py`: tek dosya açma, mm/DPI/eşik, sayfa/kare seçimi ve maskeyi hazırlama bağla. Mevcut menüde en fazla kısa bağlantı ekle. Kabul: T21; uygulamaya özel iş mantığı UI'de yok.
- [x] T011 [US3] A11 G01'de bulunan gerçek serializer girişine `bridge/visual_project.py` bağla; proje kaydet/aç ve bağımsız JSON iş kaydını doğrula. Kabul: kaynak olmadan aynı maskenin açılması, yeni FlatCAM nesne sınıfı gerekmemesi.
- [x] T012 [US2] A12 İptal, revizyon kontrolü, spot notu ve bellek limitini tamamla. `tests/test_visual_ui.py` içinde eski worker sonucunu reddet. Kabul: T22,T23.
- [x] T013 [US3] A13 UI duman testi, import sınırı ve legacy büyüme kontrolünü çalıştır; `docs/visual-interlace.md` kullanım belgesini yaz. Kabul: bitmap->N PNG->recipe/proje->yeniden aç uçtan uca çalışır. Native export henüz tamamlandı denmez.

Ortak G01/G02 ve açık alt kanıtlar: [master görevler](../../docs/design/visual-interlace/tasks.md).
