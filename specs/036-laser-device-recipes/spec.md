# Feature specification — Cihaz türüne göre lazer reçeteleri

Branch: `036-laser-device-recipes`; base `92100235`; 2026-10-03.
User: “ne gerekiyorsa yap; ben MOPA kullanıyorum ama başkası kullanmıyor”.
Kullanıcı cihaz tanımı MOPA M7 100 W; üretici/tam varyant ve native LightBurn profili bilinmiyor.

## User scenarios and acceptance

### US1 — Uygun lazer parametreleri (P1)
Kullanıcı diyot, CO₂, Ruida RF CO₂, fiber galvo, MOPA veya UV seçer.
Bağımsız kabul: diyot/CO₂ reçetesi frekans ve ns atım olmadan hazırlanır; fiber
frekans ister, MOPA frekans+ns atım ister; UV doğrudan power istemez. RF CO₂
PWM frekansı opsiyoneldir ve fiber atım frekansından ayrı alandır.

### US2 — Kayıpsız taşınabilirlik (P1)
Eski schema1 reçete/job/project kayıtları cihazı tahmin edilmeden aynen okunur.
Yeni kayıt cihaz türü/adı/sınırları ve bütün geçiş değerleriyle roundtrip olur.
Bağımsız kabul: JSON, CAM/project, SVG/DXF transfer manifest, görsel JSON/PNG ZIP
üzerinde aynı profil/değerler korunur; eski schema1 çıktısı değişmez.

### US3 — Üretici sınırları ve görünür doğrulama (P2)
Kullanıcı opsiyonel frekans/PWM/ns aralığı veya izin verilen ns listesini girer.
Bağımsız kabul: sınır dışı/uyumsuz değer açık hata olur; tür değişiminde draftlar
geri dönüldüğünde korunur, etkin olmayan alanlar yeni cihaz reçetesine yazılmaz.

## Functional requirements

- FR001: Tek immutable cihaz capability modeli hem CAM hem görsel reçetede kullanılır.
- FR002: Power%, speed mm/s, min-power%, frequency kHz, pulse-width ns ve PWM kHz ayrı alanlar.
- FR003: Türün desteklemediği non-null parametre import/model seviyesinde reddedilir.
- FR004: Zorunlu değerler açık girilir; cihaz/modelden üretim değeri icat edilmez.
- FR005: Eski dört-alanlı schema1 cihazı unspecified olarak kalır, MOPA diye etiketlenmez.
- FR006: Yeni recipe schema2 strict ve versioned; nested job/visual/manifest envelope
  kendi sürümünü arttırır, schema1 okuyucu/migration korunur; gelecekteki/duplicate/unknown alan reddedilir.
- FR007: GUI seçime göre sütun/sınırları gösterir, hassas float değerlerini ve draftları korur.
- FR008: Profil değişimi mevcut async iptal/revision mekanizmasına changed sinyaliyle katılır.
- FR009: JSON/project/export paketleri profil ve aktif alanları korur; gerçek native ayar uygulanmış sayılmaz.
- FR010: Üretici aralıkları ve discrete ns listesi isteğe bağlıdır, exact model sınırı kanıtsız eklenmez.
- FR011: Frekans ve PWM birbirine çevrilmez; controller/firmware/device port ayarı proje katmanına taşınmaz.
- FR012: Test-first, mimari/full/native, exact-head PR/main CI kanıtı ile teslim edilir.

## Scope and hazard analysis

Bu dilim metadata/UI/persistence içindir; donanım, ARM, emisyon veya firmware
yazımı yok. Yanlış lazer türü/yanlış birim riski explicit tür/birim, strict
unsupported-value rejection ve kullanıcı üretici sınırıyla ele alınır.
“100 W” power yüzdesinden Watt dönüşümü üretmez. Genel tür desteği gerçek M7
cihaz aralıklarının veya fiziksel işlemin doğrulandığı anlamına gelmez.
Native `.lbrn2` için mevcut G02 fixture/sürüm/device/Open-Save-Preview kapısı korunur.
