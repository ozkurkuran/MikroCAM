# Araştırma kararları ve kanıtlar

İnceleme tarihi: 2026-10-02. Bu dosya mevcut kanıtı tasarım tercihinden ayırır. Bağlantılı canlı belgeler değişebilir; uygulama profilinde test edilen sürüm ayrıca kaydedilmelidir.

## İlk plan turundaki referans depo incelemesi (tarihsel)

| Gözlem | Kanıt | Tasarıma etkisi |
|---|---|---|
| Çalışma ağacı 8.994 referans portu | [README](../../../README.md), [CLAUDE.md](../../../CLAUDE.md) | Ürün kodu Evo hedefinde; burada mimari belgeler |
| Genel bitmap import'u şekil çıkarıyor | `camlib.py: Geometry.import_image`, `appTools/ToolImage.py` | Native raster maske pipeline'ı bunun içine eklenmez |
| Legacy PDF aracı çizim komutlarını ayrıştırıyor | `appTools/ToolPDF.py`, `appParsers/ParsePDF.py` | Sayfanın tam görünümünü rasterlemek için genel PDF renderer kullan |
| SVG parser geometri çıkarıyor | `appParsers/ParseSVG.py` | Genel görsel görünüm için statik SVG renderer kullan |
| LaserJob ve yeni katmanlar roadmap'te | [ROADMAP](../../ROADMAP.md), [anayasa](../../../.specify/memory/constitution.md) | Mevcut hedef tipleri tekrar yaratma; alan paketleri Qt/legacy import etmesin |
| Kullanıcıya ait `docs/branding/` başlangıçta untracked | Başlangıç `git status --short` | Bu dosyalara dokunulmadı |

Hedef Evo deposunun gerçek serializer/worker/panel API'si bu dizinden çıkarılamaz. Bu yüzden G01 tam olarak bu girişleri belirleyen uygulanabilir bir görevdir; hayali host metot adı verilmemiştir.

## İlk plan turundaki yerel PDF fizibilitesi (tarihsel)

Mevcut `.venv` içinde Python 3.13.13, PyQt6/Qt 6.11.0, Pillow 12.3.0, NumPy 2.5.3 ve Shapely 2.1.2 bulundu. `PyQt6.QtPdf` ve `PyQt6.QtSvg` import edilebiliyor. pypdfium2 ve CairoSVG kurulu değil.

Bellekte oluşturulan 30×18 mm PDF, `QPdfDocument` ile 600×360 piksele render edildi. Page count 1, status Ready, iç siyah/dış beyaz örnek pikseller doğru. SVG ile aynı boyutlu basit rectangle denemesi de geçti. Dosya tabanlı ilk geçici PDF denemesi sandbox temp erişimine takıldı; belgeyi bellekte tutan deneme başarılı oldu. PDF desteğinin paketlenmiş uygulamada, worker thread'inde ve çok sayfalı dosyalarda geçtiği henüz söylenemez.

Qt PDF'nin sayfa ölçüsü ve render API'si bu dar amaç için uygundur. **Tasarım kararı:** PDF'den seçilmiş bir sayfayı görüntüye dönüştürme ilk kapsama alınır; OCR ve vektör çıkarma eklenmez. [Qt QPdfDocument](https://doc.qt.io/qt-6.11/qpdfdocument.html)

Qt PDF lisans sayfası modül ve PDFium bileşenlerinin ayrı lisans bildirimlerini listeler. Paketleme görevi bu bildirimleri envantere ekler; burada hukuki uyumluluk tamamlandı iddiası yoktur. [Qt PDF lisans bilgisi](https://doc.qt.io/qt-6.11/qtpdf-licensing.html)

## Kaynak renderer seçimleri

**Bitmap:** Pillow mevcut ortamda bulundu. Sık kullanılan bitmap biçimleri için tek codec kullanmak yeterlidir; çıktı maskesi de PNG olarak saklanır. Hedefte doğrudan dependency pin eklenecektir. [Pillow biçim belgeleri](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html)

**SVG:** QtSvg basit örneği render edebildi, fakat clipping dahil görünüm kısıtları genel SVG ithalatında risk oluşturuyor. Legacy parser da aynı gereksinimin yerine geçmiyor. [Qt SVG görünüm desteği](https://doc.qt.io/qt-6/topics-vectorimageformats.html)

resvg_py 0.5.0 proje sayfasında Python >=3.10 ve `cp310-abi3-win_amd64` wheel mevcut. Bu metadata hedef Python'a aday olduğunu gösterir; kurulum testi değildir. **Tasarım tercihi:** statik SVG için resvg_py; G02'den ayrı B01 kurulum/render kapısı. [PyPI resvg_py](https://pypi.org/project/resvg_py/), [resvg_py API](https://resvg-py.readthedocs.io/en/latest/)

Wrapper MIT, resvg MIT/Apache-2.0 lisans seçeneklerini bildiriyor. Statik SVG altkümesine odaklanan renderer; tüm SVG özelliklerini desteklediği varsayılmıyor. Harici kaynaklar, eksik fontlar ve desteklenmeyen öğeler için önkontrol gerekir. [Wrapper kaynak deposu](https://github.com/baseplate-admin/resvg-py), [resvg README](https://github.com/linebender/resvg/blob/main/README.md), [desteklenmeyen özellikler](https://github.com/linebender/resvg/blob/main/docs/unsupported.md)

Alternatifler: CairoSVG yeni native dağıtım bileşenleri değerlendirmesi gerektirir; mevcut QtSvg ise daha dar görünüm sözleşmesi ister. Bu aşamada ikinci SVG renderer/fallback eklenmez. Qt PDF paketleme kabulü başarısız olursa pypdfium2 aynı PDF sayfa rasterleme sözleşmesi için sonraki adaydır; şu anda ikinci PDF backend'i eklenmez. PyMuPDF gerektiren bir ihtiyaç yoktur.

## LightBurn için doğrulanmış ürün davranışları

Pass-Through önceden hazırlanmış görüntüyü yeniden işlememek için sunuluyor; çözünürlük fiziksel görüntü boyutuyla ilişkilidir. Üstten alta yatay tarama açısı belgede 180° olarak açıklanıyor. Bunlar hedef dosya alan adlarını veya galvo satır atlama davranışını kanıtlamaz. [Image Mode](https://docs.lightburnsoftware.com/latest/Reference/CutSettingsEditor/ImageMode/)

Katmana göre sıralama ve optimizasyon ayarlarının projeye kaydı belgelenmiştir. Proje export'u sadece renk numarası atamaya indirgenemez. [Optimization Settings](https://docs.lightburnsoftware.com/latest/Reference/OptimizationSettings/)

Proje dosyası Open ile açılmalıdır; Import işlemi proje ayarlarının yüklenmesiyle aynı değildir. Kabul prosedürü bu nedenle Open kullanır. [File Management](https://docs.lightburnsoftware.com/latest/Reference/FileManagement/)

Katmandaki tekrar ile bütün iş tekrarı farklı kavramlardır. Galvo Framing'de bütün iş için Repeat davranışı belgelenir; bunun her hedef sürümde `.lbrn2` içinde nasıl saklandığı bu çalışmada doğrulanmadı. [Galvo Framing](https://docs.lightburnsoftware.com/latest/Reference/GalvoFraming/)

Üretici forumundaki teknik açıklama transform ve origin/mirror alanları arasındaki ilişkiye örnek veriyor. Bu tarihsel açıklama tam güncel şema değildir; G02'nin yerine geçmez. [LightBurn geliştirici açıklaması](https://forum.lightburnsoftware.com/t/lbrn2-file-documentation/52174/2)

## Henüz doğrulanmayan uyumluluk noktaları

| Soru | Durum | Kapatan görev |
|---|---|---|
| Kullanıcının LightBurn sürümü ve cihaz ailesi | Bu plan hazırlanırken bildirilmedi | G02 |
| `.lbrn2` bitmap payload'ı ve kesin alan adları | Gerçek dosya fixture'ı henüz yok | G02,C01 |
| Origin, mirror ve pixel-center eşleşmesi | Koordinat sözleşmesi tasarlandı; hedef kanıtı yok | G02,C05 |
| Beyaz satırların hareketten atlanması | Profil bazında doğrulanmalı | G02,C05 |
| Bidir yönünün kaynak r paritesiyle eşleşmesi | Garanti edilmiyor | C05, capability kontrolü |
| Gerçek katman kapasitesi | Tahmin edilmedi | G02 |
| Tam tur sırasının native dosyada korunması | Ayrı katman genişlemesi önerildi | D01,D02 |
| Katmanlar arası ms dwell | Destek varmış gibi kabul edilmedi | D04,D05 |
| resvg Windows kurulumu ve golden SVG | PASS:0.5.0 ABI3 wheel, clip/mask/font/embedded-image testleri; binary notice audit açık | B01,B02 |
| Qt PDF worker/karmaşık dosyalar | PASS:çok sayfa/rotation/encrypted/missing renderer/mixed bitmap-vector +nativeCAM; binary release ayrı | B04,B05,B10 |

Bu sorular planlamanın tamamlanmasına engel değildir; ölçülebilir uygulama kabul kapılarıdır. Özellikle G02 geçmeden native export varmış gibi kullanıcıya dosya verilmez.

## Evo uygulama bulguları

Gerçek katman/API uyarlaması [target-integration.md](target-integration.md) içindedir.
NumPy core'da, codec bridge'de, Qt ui'de: ilk planın QtPdf bridge varsayımı hedef
import guard'ına göre değiştirildi. Mevcut Placement/Recipe tekrar kullanıldı;
Geometry obj_options payload gerçek host save/reopen ile doğrulandı.

resvg_py 0.5.0 exact Windows wheel Python 3.13'te kuruldu; default dpi0 physical mm
belgelerde invalid-size üretti. Açık dpi96 kaynak belge birimini çözdü; kazıma508DPI
ayrı kaldı. Wrapper MIT LICENSE ve artifact/metadata SHA exact envanterde.

Bitmap16-bit gri tone mapping, CMYK/sRGB ICC, EXIF, palette alpha ve explicit frame
seçimi geçti. SVG known fonts local files ile renderlenir; missing font/glyph açık
hata verir. PDF Qt document worker thread'inde load/render/close, bytes detached.
Crop source coordinate belirsizliği SVG/PDF'de açık unsupported ile çözüldü; bitmap
EXIF sonrası pixels kullanılabilir. İlk UI bütün sayfayı kullanır.

LightBurn standard ProgramFiles/ProgramFiles(x86), process ve uninstall kayıtlarında
bulunmadı. Version/device/program veya saved project yerel yolu sorusu pending.
Bu koşul G02'yi WAITING yapar; örnek PNG/mask veya XML parse native yürütüm kanıtı değildir.

## Son kaynak ve uyumluluk hazırlığı

[75 crate kaynak notice kanıtı](notice-audit.md) ve
[10 LightBurn keşif örneği](../../examples/visual-interlace/lightburn-discovery/README.md) hazır.
Keşif seti PNG/JSON içerir; gerçek `.lbrn2` fixture veya native PASS değildir.
