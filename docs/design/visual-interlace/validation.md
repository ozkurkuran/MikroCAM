# Kabul ve test matrisi

Bu dosya40kabul senaryosunu ve çalışan V1/V2 kanıtlarını ayırır. Native T30–T40 kabulü ayrı statüdedir; Python maskesi LightBurn hareketini kanıtlamaz.

## Test katmanları

Saf maske/plan testleri Qt, OpenGL, LightBurn veya donanım istemez. Importer ve proje entegrasyonu ayrı test grubudur. Qt PDF testinde `QT_QPA_PLATFORM=offscreen` kullanılır. Native proje uyumluluğu ayrıca gerçek LightBurn aç/kaydet/Preview denemesine bağlıdır; görüntü karşılaştırması tek başına hareket sırası kanıtı değildir.

| Test | Girdi veya olay | Beklenen sonuç | Gereksinim |
|---|---|---|---|
| T01 | 600×360, 508 DPI | 0,05 mm pitch, 30×18 mm canvas | FR-005,008 |
| T02 | Tam piksele bölünmeyen mm ölçüsü | Ceil grid, esnetme yok, padding <1 piksel | FR-005,008 |
| T03 | Alpha=0/128/255 ve siyah/beyaz RGB | Beyaz compositing ve deterministik gri dönüşümü | FR-002 |
| T04 | Eşik sınırı 127/128/129, invert ve padding | Belirlenmiş `< threshold`; padding her zaman beyaz | FR-002,005 |
| T05 | NaN, infinity, negatif/0 ölçü, aşırı piksel | Erken açık hata; kaynak değişmez | FR-005,024 |
| T06 | PNG/JPEG/BMP/TIFF/WebP/GIF fixture'ları | Doğru RGBA, page/frame ve EXIF yönü | FR-001,002 |
| T07 | Paletli saydam resim, CMYK/ICC örneği | Görünüm doğru normalize; sRGB kararı kayıtlı | FR-002 |
| T08 | Bozuk dosya, yanıltıcı uzantı, bomba boyut | Decode öncesi/sonrası limit; başarı yerine hata | FR-001,024 |
| T09 | N=3,H=10 | `[0,3,6,9] [1,4,7] [2,5,8]` | FR-007,009 |
| T10 | N=1..8, H=0..1024 | Satır birleşimi range(H), çift üyelik yok | FR-006,007,009 |
| T11 | bool/kesir/aralık dışı N, negatif H | Hata; H=0 yalnız saf partition'da geçerli | FR-006 |
| T12 | N=1 farklı maskeler | Ana maskeyle pixel-identical; input değişmez | FR-010 |
| T13 | Beyaz, siyah, checkerboard, tek piksel, rastgele maskeler | Parça OR=M, uint16 toplama=M, aynı shape/grid | FR-007,008,009 |
| T14 | N=1..8 mixed, farklı H | Sabit sıra tablosu, yine tam bir kez üyelik | FR-011 |
| T15 | Boş satırlar ve N=2/3/4 | Orijinal r paritesi değişmez; grup numarası kullanılmaz | FR-012,015 |
| T16 | Tek parça/birleşim/zoom preview | Kaynakla aynı grid; downsample üretim verisini değiştirmez | FR-013,023 |
| T17 | PNG encode/decode | 0/255 ve pixel-identical; byte sıkıştırması önemsiz | FR-008,016 |
| T18 | Kaynak taşınıp JSON iş açılması | Gömülü maske, tüm ayarlar ve sıralar aynı | FR-016 |
| T19 | Eski recipe, gelecek schema, bozuk hash | Eskiye N=1 migration; diğerlerinde açık hata | FR-016,021 |
| T20 | Proje kaydet/aç ve iş kaydet/aç | Ortak payload korunur, dış yol bağımlılığı yok | FR-016 |
| T21 | GUI kaynak/ölçü/eşik değişikliği | Worker sonucu doğru revizyonda gösterilir | FR-005,013 |
| T22 | İptal veya eski worker geç bitiyor | Yeni iş/dosya bozulmaz; export stale planı reddeder | FR-024 |
| T23 | pitch <, =, > spot; spot bilinmiyor | Yalnız küçükse bilgi; bilinmiyorsa varsayım yok | FR-017 |
| T24 | SVG stroke/fill/delik/clip/mask/viewBox | Golden görünüm ve doğru mm sınırı | FR-003 |
| T25 | SVG dış referans, eksik font, animasyon | Açık hata; sessiz eksik çizim kabul edilmez | FR-003,021 |
| T26 | PDF iki sayfa, döndürülmüş/karışık içerik | Doğru sayfa, mm boyutu ve yön | FR-004 |
| T27 | PDF modülü yok, şifreli/bozuk dosya | Uygulama açılır, ilgili kaynak anlamlı hata verir | FR-004,021 |
| T28 | Aynı işin bitmap/SVG/PDF sürümü | Tek kaynak-independent bölücü, doğru ölçü | FR-001,003,004 |
| T29 | Gerber delikleri ve açık ROI | İstenen alan maskesi, Gerber zorunluluğu yok | FR-001,002 |
| T30 | G02 `.lbrn2` fixture'ı ve yeni export | Gömülü görüntü, katman bağlantısı ve mm doğru | FR-014,022 |
| T31 | Bilinmeyen profil/katman limit aşımı | Export reddi; sessiz alan veya tur kaybı yok | FR-021 |
| T32 | N=3 mixed sıra | Etkin Image katman sırası 0,2,1 | FR-011,014 |
| T33 | H=2,N=8; boş grup; asimetrik köşeler | Tuval aynı, boş katman Output kapalı, ayna/kayma yok | FR-008,012,014 |
| T34 | LightBurn Open->Save->Open->Preview | N=1..8 için piksel satır/ölçü/sıra korunur | FR-014,015,022 |
| T35 | Beyaz satır, iki yön, üstten alta örnek | Gerçek skip/yön profile kaydedilir; bilinmeyen garanti edilmez | FR-012,015,023 |
| T36 | Eksik güç/hız recipe, boş maske | Export kapalı; kullanıcı işi yine kaydedebilir | FR-021 |
| T37 | Export yazım hatası/iptal | Eski destination aynı byte'larda kalır | FR-024 |
| T38 | N=3,R=2 ve farklı boş gruplar | Etkin pikseller toplam R kez; sıra 0,1,2,0,1,2 | FR-018 |
| T39 | N=3,mixed,R=3,vary=True | `[0,2,1] [1,0,2] [2,1,0]`, kayıt sonrası aynı | FR-019 |
| T40 | Dwell, boş geçiş ve tur sınırı | Etkin geçişler arasında bekleme; sonda yok; unsupported export reddi | FR-020,021,023 |

## Genel doğruluk örnekleme sınırı

“Tüm H” sonsuz bir test aralığı değildir. Matematiksel dayanak bölüm-kalan teoremidir: her r için tek `k=r%N` vardır. Otomatik test bunun yanında N=1..8 ve H=0..1024'ü kapsamlı tarar; 1025,4095,4096,4097 ve 100003 gibi büyük/sınır değerlerini de ekler. Maskelerde sabit seed ile küçük farklı W,H örnekleri kullanılır; büyük H partition testinde dev bitmap oluşturulmaz.

Kesişim testi yalnız toplam satır sayısına bakmaz. Her r'nin sayımı tam 1 olmalı. Piksel testi bool toplamının taşmaması için en az uint16 kullanır. Siyah=0 PNG byte'larında `OR` yapmak yerine True=kazıma maskelerine dönülür.

## Referans veri seti

- 13×10 asimetrik maske: dört köşeyi farklı işaretle, en üst/en alt satırda tek siyah piksel ekle. Ayna, bir satır kayma ve otomatik kırpmayı yakalar.
- 600×360 kullanıcı örneğinin sentetik eşdeğeri: aynı tam boyut ve 508 DPI; telifli görsel gerekmez.
- Sadece satır 0,2,5,9 dolu H=10 maske: boş satır sonrası indekslerin kaymaması.
- 10×10 tamamen beyaz/siyah/checkerboard ve H<N maskesi.
- 30×18 mm SVG/PDF: rectangle, delik, ince stroke, açık beyaz kenar. Piksel kökeni ve gerçek ölçü bilinir.
- Tam piksele bölünmeyen 30,013×18,017 mm kaynak: padding ve ölçek ayrımı.
- Kaynak bitmap'i ve renderer beklenen çıktısı ayrı fixture; render toleransını interlace eşitliğine taşımayın.

## Gerçek doğrulama komutları

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -r requirements-visual.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q -rs
.\.venv\Scripts\python.exe tests/smoke_visual_app.py
```

Qt unit/UI koşusu conftest offscreen/isolated settings kullanır. Native runner gerçek
desktop/OpenGL ister;120 s watchdog ve izole settings/data/pipe ile yalnız kendi
MikroCAM sürecini yönetir. Makine/COM/lazer erişimi yoktur. Windows CI install adımı
optional visual extra'yı da kuracak şekilde hazırlanmıştır; CI run henüz yapılmadı.

## V1/V2 uygulama kanıtı

Kaynak base `c5a666cf`, branch032, uncommitted. Önce full checkpoint5669/310 PASS,
sonraki kaynak eec5ca1a:5744/310 PASS,3 skip,11baseline warning,458.19 s.
Typed API son kaynak `8fefc0d0`: 27 UI/recipe PASS / 4.45s; final full 5744/310 PASS / 509.30s.
Son kaynak manifest `.venv/visual-api-final-source.json`.

| Senaryo | Kanıt / durum |
| --- | --- |
| T01–T05 | PASS `tests/test_visual_core.py`: exact508DPI, padding, alpha/eşik/invert, limits, immutable logicalSHA |
| T06–T08 | PASS `tests/test_visual_bitmap.py`:6 format,1 bit/16 bit/CMYK/ICC/EXIF/frame, bozuk ve bombguard |
| T09–T15 | PASS `tests/test_visual_interlace.py`, `test_visual_reference.py`:8240row combinations,40edge patterns, immutable/disjoint, mixed order, kaynak satır paritesi helper |
| T16 | PASS `test_visual_core.py`, `test_visual_ui.py`: group downsample kaybı yok, fit ve thumbnail zoom üretim maskesini değiştirmiyor |
| T17–T19 | PASS `test_visual_recipe.py`, `test_visual_bitmap.py`:1 bitPNG, embedded source/master, missinginterlace migration, duplicate/nonfinite/hash/schema/grid rejection |
| T20 | PASS gerçek `smoke_visual_app.py`: kaynaklar silinir, hostFlatPrj save/reopen hash aynı; standaloneJSON save/load |
| T21–T23 | PASS `test_visual_ui.py`, `test_visual_reference.py`, `test_visual_export.py`: GUI timer worker bloklanınca ilerler; stale result/cancel/spot strictcomparison |
| T24–T25 | PASS `test_visual_svg_pdf.py`:stroke/fill/hole/clip/mask/transparency/font/embedded bitmap; external/dynamic/missingfont rejection |
| T26–T28 | PASS `test_visual_svg_pdf.py`, `test_visual_sources_equivalence.py`:PDF page/rotation/encrypted/missingQtPdf/mixed content, common physicalgrid and exactsplit |
| T29 | PASS `test_visual_geometry.py`, `test_visual_ui.py`:ROI,holes,invert,inch→mm, detached geometry; Gerber olmadan dosya akışı |
| T30–T36 | WAITING G02/native LightBurn; Python/image testleri nativePASS yerine konmaz |
| T37 | PNG/JSON atomiccancel/stale PASS; native LightBurn failure paths NOT_RUN |
| T38–T40 | Core cycles/order/dwell veJSON persistence PASS; native capacity/dwell/Preview WAITING |

Native son typed API koşusu `.venv/visual-api-final-native.log`: exit0,
`VISUAL_BITMAP_SVG_PDF_PNG_JSON_HOST_PROJECT_ROUNDTRIP_OK` ve
`VISUAL_FOCUSED_NATIVE_RENDER_SHUTDOWN_OK`. Menu action,3formats, embeddedJSON,
PNG union, mevcut Geometry carrier, source deletion, real project reopen, existing
Gerber/Drill/isolation/CNC roundtrip, OpenGL render, normal thread/pool shutdown.
Screenshot `.venv/visual-dock-native.png` gözle incelendi; Türkçe metinler ve bütün
canvas fit doğrulandı. UIzoom11test ayrıcaPASS. Eski FAIL/timeout logları korunur.

Saf algoritma/codec source doğrulaması ile nihai binary release license audit ayrı;
75 crate kaynak notice kapsamı PASS; wheel build provenance ve final bundle audit açık. Native .lbrn2 veya fiziksel lazer testi yok.

## 2026-10-02 plan kanıtı

- Referans ortam: CPython 3.13.13, PyQt6/Qt 6.11.0, Pillow 12.3.0, NumPy 2.5.3.
- QtSvg ile bellekte oluşturulan basit 30×18 mm çizim 600×360 render edildi; beklenen iç/dış pikseller doğrulandı.
- Qt PDF ile bellekte oluşturulan 30×18 mm tek sayfa 600×360 render edildi; pageCount=1, Status.Ready, siyah/beyaz kontrol pikselleri doğru. Okunan boyut yaklaşık 29,999999×17,999999 mm; bu PDF sayı yuvarlamasıdır.
- `resvg_py` kurulumu ve renderer golden testleri bu turda yapılmadı; B01/B02 görevidir.
- Hedef LightBurn sürümü/device profili ve gerçek `.lbrn2` kabulü bu turda doğrulanmadı; G02/C05 görevidir.
- Bu denemeler uygulama kodu yazıldığı veya yukarıdaki 40 kabul testinin geçtiği anlamına gelmez.

## Son kaynak kapanış kaydı

Son code/config fingerprint: `8fefc0d0bccc6c5b1c29aa219a595f0c5047d262569eb7200c24738cbbdb3c8c`.
Full `.venv/visual-api-final-regression.log` **PASS exit0**: **5744 test,310alt test**,
3skip,11mevcut warning,509.30s. Bu koşu son publictypehint API'ye aittir; eski
checkpoint'lerden taşınmış PASS değildir. Import/growth/notices bu full koşuya dahildir.
Native `.venv/visual-api-final-native.log` **PASS exit0**, normal shutdown marker'ı var.
Modül600/fonksiyon80/publictypehint check **PASS**. Final başlangıcından sonra code/config
hash'lerinde değişiklik yok. Demo ZIP yeniden decode edilip600×360/mode1/508DPI ve
piksel toplamı=master doğrulandı; manifest native settings applied=False.

Yerel yazılım doğrulaması kapandı. V3native, V4native ve binaryrelease noticeaudit
ayrı açık işlerdir. Main/remote/PR/CI/merge NOT_RUN. Proje hedefi tam .lbrn2 teslimi
olduğundan **bütün hedef tamamlandı değildir**.

## 2026-10-03 — resumed checkpoint

Complete suite PASS exit0: **5746 tests,310subtests,3skips,11existing warnings,306.23s**.
Log: `.venv/visual-resume-final-regression.log`; JUnit: `.venv/visual-resume-final-pytest.xml`.
Source/notice checkpoint: `77899fec9b5b14b87485c5be6c34bc6e6f79af92eee28e7dc815c6e06468334e`,201 SHA-verified files.
`.venv/visual-resume-final-result.json` proves the checkpoint stayed unchanged.
The actual worktree `.venv/Scripts/python.exe` passed pip check; seven SVG-dependent
cases first failed under the older repro-a interpreter, then passed in the correct
environment before this full run. Both results are retained as separate evidence.

The prior native menu/source/project/OpenGL/shutdown evidence remains applicable
to unchanged runtime/config files; it was not rerun or relabelled as a new native test.
Notice inventory and the two added notice tests are covered by this fresh full suite.
Historical5744-test records above remain historical rather than the current full result.

A local source checkpoint preserves V1/V2 and their tests/specs/notice records.
The commit is recorded in the central IS_TAKIP after git verifies it.
Push/PR/hosted CI/main delivery remain NOT_RUN. Two real historical vector-only
projects provide limited format metadata; they are not Image fixtures. Current
LightBurn executable/device/embedded Image evidence and native V3/V4 remain open.
No complete binary-release audit or complete .lbrn2 product delivery is claimed.
