# Tasks — Aynı iş akışında SVG/PDF ve isteğe bağlı bakır kaynağı

Hikâyeler: **V2-US1** SVG görünümünü kullanma; **V2-US2** PDF sayfasını kullanma; **V2-US3** mevcut Gerber/Geometry nesnesini isteğe bağlı kaynak yapma. Bağımlılık: V1. V2-US3 mevcut Gerber bridge'ine bağlıdır; dosya açma için gerekli değildir.

- [x] T001 [US1] B01 İzole hedef ortamda `resvg_py==0.5.0` Windows/Python 3.13 wheel kurulumunu ve statik çizim/clipping renderını doğrula. `requirements-visual.txt`, `THIRD_PARTY_LICENSES/` ve araştırma kanıtını güncelle. Kabul: derleyici gerektirmeyen kurulum, paketleme denemesi ve license kaydı; başarısızsa sessiz renderer değişimi yok.
- [x] T002 [US1] B02 `tests/test_visual_svg_pdf.py`: mm/px/viewBox, stroke, delik, transform, clipPath, mask, transparency, metin ve gömülü bitmap örneklerini yaz. Harici referans/dinamik/eksik font hatalarını ekle. Kabul: T24,T25.
- [x] T003 [US1] B03 `bridge/visual_svg.py` ve source validation genişletmesini uygula. Ana maske pipeline'ını yeniden kullan. Kabul: B02; kaynak DPI ile çıktı pitch'i karıştırılmıyor.
- [x] T004 [US2] B04 `tests/test_visual_svg_pdf.py`: iki sayfa, farklı fiziksel ölçü, döndürülmüş sayfa, vektör+görüntü, bozuk/şifreli dosya ve modül eksikliği testlerini yaz. Kabul: T26,T27; tam piksele bölünmeyen ölçüler dahil.
- [x] T005 [US2] B05 `ui/visual_pdf.py`: lazy Qt PDF load, sayfa seçimi, fiziksel viewport ve NumPy RGBA çıktısını uygula. Kabul: B04; Qt nesnesi core/laser'a geçmiyor.
- [x] T006 [US1] B06 `bridge/visual_workflow.py`, `ui/visual_interlace_panel.py`: bitmap/SVG/PDF file dispatch ve PDF sayfa seçiciyi ekle. Kabul: T28; seçilen sayfa preview ve exportta aynı.
- [x] T007 [US2] B07 `tests/test_visual_sources_equivalence.py`: aynı basit çizimin PNG/SVG/PDF kaynaklarından beklenen mm/grid boyutunu ve interlace birleşimini karşılaştır. Kabul: kaynak render toleransı ile birebir split doğruluğu ayrı assert edilir.
- [x] T008 [US3] B08 `tests/test_visual_geometry.py`: mevcut top copper poligonları, delikleri ve kullanıcı ROI'si ile maske testi yaz. Kabul: T29; Gerber yokken dosya iş akışı çalışır.
- [x] T009 [US3] B09 `bridge/visual_geometry.py + core/geometry_visual.py` uygula. Mevcut izolasyon/temizleme geometrisini kaynak olarak al; yeni PCB CAM algoritması ekleme. Normal/ters alan seçiminde açık ROI ve kullanıcı önizlemesi kullan. Kabul: B08; Gerber'e özgü işlem interlace içine girmiyor.
- [x] T010 [US2] B10 SVG/PDF lazy import, Qt PDF lisans/paketleme ve donanımsız offscreen duman testini çalıştır. Kabul: bitmap+SVG+PDF tek pipeline üzerinden kaydedilip açılır; PDF vektör çıkarma kapsamı eklenmez.

Ortak G01/G02 ve açık alt kanıtlar: [master görevler](../../docs/design/visual-interlace/tasks.md).

T001/T010 kapanışı: [040 Windows paketleme](../040-packaging-windows/validation.md) kanıtlarıyla (2026-10-04).
