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
