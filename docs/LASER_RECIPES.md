# Lazer cihazına göre reçete

**Lazer CAM** ve **Görsel satır serpiştirme** panelleri aynı reçete editörünü
kullanır. Yeni reçetede lazer türünü seçin, reçete ve geçiş adını girin, ardından
gösterilen sayısal alanları doldurun. Değerler otomatik üretilmez.

| Lazer türü | Zorunlu geçiş ayarları | İsteğe bağlı |
| --- | --- | --- |
| Diyot / G-code | Güç %, hız mm/s | Minimum güç % |
| CO₂ | Güç %, hız mm/s | Minimum güç % |
| Ruida RF CO₂ | Güç %, hız mm/s | Minimum güç %, PWM kHz |
| Fiber galvo | Güç %, hız mm/s, frekans kHz | Minimum güç % |
| MOPA galvo | Güç %, hız mm/s, frekans kHz, atım süresi ns | Minimum güç % |
| UV galvo | Hız mm/s, frekans kHz, atım süresi ns | — |

Dar panelde geçiş tablosunu yatay kaydırarak diğer sütunlara ulaşabilirsiniz.
Lazer türünü değiştirdiğinizde gizlenen alanların yazım taslağı korunur; tekrar
aynı türe dönerseniz görünür. Kaydedilen reçete yalnız seçili türün alanlarını
içerir. Tür veya değer değişikliği hazırlanan işi geçersiz kılar; yeniden hazırlayın.

## MOPA M7 100 W

**MOPA galvo** seçip model adına `MOPA M7 100 W` yazabilirsiniz. Bu ad üretici,
tam varyant, frekans aralığı veya izin verilen atım sürelerini belirlemez.
`100 W` etiketi güç yüzdesini Watt'a çevirmeye yarayan bir kalibrasyon değildir.

**Üretici sınırlarını kullan** seçeneği ile cihazınıza ait belgeye göre frekans
ve atım süresi aralıklarını `min:max` biçiminde yazın. Ayrık atım seçenekleri
varsa virgülle ayrılmış ns değerlerini girin. Bunlar isteğe bağlıdır; girildiğinde
sınır dışı değerler ve listede olmayan atım süreleri reddedilir. RF CO₂ PWM
aralığı da ayrı girilir. Bu aralıklar için yerleşik M7 varsayımı yoktur.

## Kaydetme ve LightBurn aktarımı

Cihazlı reçeteler ve onları içeren iş/paket kayıtları sürüm 2 olarak saklanır.
JSON, MikroCAM proje kaydı, görsel PNG ZIP ve geometri SVG/DXF paketleri profil
ile geçiş değerlerini korur. Eski sürüm 1 kayıtları **Eski reçete — cihaz türü
belirtilmemiş** etiketiyle aynı değerlerde açılır; sayılarından cihaz tahmin edilmez.

Bu metadata, LightBurn katman ayarlarının uygulanmış olduğu anlamına gelmez.
SVG/DXF/PNG görsellerini aktardıktan sonra katman ayarlarını LightBurn'de kontrol
edin. Native `.lbrn2` düğmesi gerçek Image projesi, sürüm/cihaz profili ve
Open→Save→Preview kabulü beklediği için kapalıdır. Ayrıntılar:
[LightBurn uyumluluk kaydı](lightburn-compatibility.md).

Fiber frekansı atım tekrar frekansıdır; RF CO₂ PWM taşıyıcı frekansı ayrı alandır.
GRBL S-value maksimumu, kaynak seçimi, portlar ve kalibrasyon cihaz/firmware
ayarlarıdır. Reçete bu ayarları veya fiziksel lazeri değiştirmez.

Davranış referansları: LightBurn'un [galvo ayarları](https://docs.lightburnsoftware.com/latest/Reference/CutSettingsEditor/GalvoSpecificCutSettings/),
[ortak katman ayarları](https://docs.lightburnsoftware.com/latest/Reference/CutSettingsEditor/SharedSettings/),
[PWM override](https://docs.lightburnsoftware.com/latest/Reference/CutSettingsEditor/LineMode/#override-pwm-frequency)
ve [galvo port ayarları](https://docs.lightburnsoftware.com/latest/Reference/DeviceSettings/GalvoPorts/).

## Reçete veritabanı

**Lazer CAM** panelindeki **Reçete veritabanı** bölümü malzeme, lens, makine ve
reçeteleri tek dosyada saklar. Dosya yolu bölümün üstünde gösterilir; Windows'ta
normalde `%APPDATA%\FlatCAM\mikrocam\laser_recipe_db.json` konumundadır.

1. **Malzeme → Yeni…** ve **Lens → Yeni…** ile kayıt ekleyin. Kalınlık ve odak
   uzaklığı isteğe bağlıdır; boş bırakılırsa boş kalır, değer tahmin edilmez.
2. Editörde lazer türünü ve model adını seçip **Makine → Editör profilini kaydet**
   deyin. Aynı adlı makinenin profilini (ör. üretici sınırları) değiştirmek, ona
   bağlı bütün reçeteleri yeni profille yeniden doğrular; biri uymazsa hiçbir şey
   değişmez.
3. Malzeme ve lensi seçip **Editördekini kaydet** deyin. Makine, editördeki cihaz
   profilinden belirlenir; yoksa eklenir. Aynı malzeme/makine/lens için aynı adlı
   ama farklı değerli reçetenin üzerine yazmadan önce onay istenir.
4. **Ara** kutusu reçete, malzeme, makine ve lens adlarında arar. Satırı seçip
   **Editöre yükle** (veya çift tıklama) reçeteyi editöre kopyalar.

Hazırlanan iş, proje ve SVG/DXF/PNG paketleri reçetenin tam kopyasını saklar;
veritabanında sonradan yapılan bir değişiklik kaydedilmiş işleri değiştirmez.
Kullanılan malzeme, lens veya makine silinemez.

### Eski JSON reçeteleri

**JSON içe aktar…** sürüm 1 (cihazsız) ve sürüm 2 (cihazlı) reçete dosyalarını
seçili malzeme/lens altında ekler. Sürüm 1 reçete makinesiz, “cihaz türü
belirtilmemiş” olarak kalır. Seçilen dosyalardan biri hatalıysa hiçbiri eklenmez.
**JSON dışa aktar…** seçili reçeteyi yeniden tek dosya olarak yazar; MikroCAM'in
yazdığı bir dosya içe ve dışa aktarıldığında bayt bayt aynı kalır. **Load/Save recipe
JSON** düğmeleri de değişmeden çalışır.

Veritabanı dosyası `schema_version: 1` taşır. Açılamayan, bozuk veya daha yeni
sürümlü dosya **salt okunur** gösterilir ve üzerine yazılmaz. Dosya başka bir
MikroCAM penceresinde değiştiyse kayıt reddedilir; **Yeniden yükle** ile güncelleyin.

Veritabanındaki bir reçete fiziksel olarak doğrulanmış sayılmaz. Değerleri kendi
cihazınızda test kuponuyla doğrulayın; yazılım fiziksel interlock'un yerine geçmez.
