# Feature specification — Lazer reçete veritabanı

Branch: `037-laser-recipe-db`; base `70800e5b` (036 birleştirilmiş main); 2026-10-04.
Yol haritası dilimi 28 `laser-recipe-db`: “Malzeme, makine, lens ve recipe veritabanı ile
arayüzü; 0.2'deki JSON recipe'lerin yerini alır” (bağımlılık 5 `laserjob-model`).
036 ile gelen cihaz profili (diyot/CO₂/Ruida RF CO₂/fiber/MOPA/UV) ve reçete şema2
üzerine kurulur. Kullanıcı cihazı MOPA M7 100 W; üretici sınırları ve sayısal varsayılanlar
bilinmez, icat edilmez.

Kullanıcıya soru sorulamadı (otonom koordinatör görevi). Açık noktalar aşağıda
**uygulama varsayımı** olarak kayıtlıdır; kullanıcı kararı değildir ve değiştirilebilir.

## User scenarios and acceptance

### US1 — Kayıtlı reçeteyi seç ve kullan (P1)
Kullanıcı malzeme (ör. FR4 35 µm Cu) ve lens kayıtları oluşturur, editördeki cihaz
profilini makine olarak kaydeder, editördeki reçeteyi seçili malzeme/lens ile
veritabanına kaydeder. Uygulama yeniden açıldığında reçete listesinde arar, seçer ve
editöre yükler.
Bağımsız kabul: kaydedilen reçete aynı malzeme/makine/lens etiketiyle listelenir,
yüklenince editör değeri birebir aynıdır; arama reçete/malzeme/makine/lens adında
çalışır; veritabanı dosyası atomik yazılır ve yeniden açılınca aynıdır.

### US2 — 0.2 JSON reçetelerinin kayıpsız taşınması (P1)
Kullanıcı mevcut schema1 (cihazsız) ve schema2 (cihazlı) reçete JSON dosyalarını
veritabanına içe aktarır; tek reçeteyi yeniden JSON olarak dışa aktarır.
Bağımsız kabul: schema1 reçete cihazsız kalır (makine atanmaz, tahmin yapılmaz);
schema2 reçetenin profili eşit makineye bağlanır veya yeni makine olarak eklenir;
kanonik JSON dışa aktarımı içe aktarılan metinle bayt bayt aynıdır. Mevcut “Load/Save
recipe JSON” akışı değişmeden çalışır. Veritabanı dosyası kendi şema sürümünü taşır;
v1 altın dosyası açılır, gelecekteki sürüm reddedilir ve üzerine yazılmaz.

### US3 — Tutarlılık ve veri kaybı koruması (P2)
Kullanıcı makine profilini (ör. üretici sınırları) günceller, malzeme/lens/makine
siler, aynı anahtarlı reçeteyi yeniden kaydeder.
Bağımsız kabul: makine güncellemesi bağlı bütün reçeteleri yeni profille yeniden
doğrular, biri geçersizse hiçbir şey değişmez; kullanılan malzeme/lens/makine silinemez;
aynı anahtarlı farklı reçete onaysız ezilmez; bozuk veya başka süreçte değişmiş dosya
üzerine yazılmaz.

## Functional requirements

- FR001: Değişmez Qt'siz model: Material(ad, isteğe bağlı kalınlık mm, not),
  Lens(ad, isteğe bağlı odak uzaklığı mm, not), Machine(036 `LaserDeviceProfile`, not),
  RecipeEntry(`LaserRecipe`, makine/malzeme/lens referansı, not).
- FR002: Cihaz profili tek kaynaktır: cihazlı reçetenin profili bağlı makinenin
  profiline eşit olmak zorundadır; dosyada profil yalnız makinede saklanır.
- FR003: Cihazsız (schema1) reçete makinesiz kalır; makineli reçete cihazsız olamaz.
- FR004: Adlar tablo içinde büyük/küçük harf duyarsız benzersizdir; reçete anahtarı
  (malzeme, makine, lens, reçete adı) benzersizdir; referanslar mevcut olmak zorundadır.
- FR005: Hiçbir sayısal değer (güç, hız, frekans, ns, kalınlık, odak) üretilmez;
  boş isteğe bağlı değer `null` kalır.
- FR006: Veritabanı JSON'u `kind=mikrocam.laser-recipe-db`, `schema_version=1`; strict
  okuma (eksik/bilinmeyen/duplicate alan, bool sayı, NaN/Inf, gelecek sürüm red), boyut
  sınırı, deterministik yazım ve migration giriş noktası.
- FR007: schema1/schema2 reçete JSON içe aktarma kayıpsızdır; çakışan farklı reçete
  açık hata verir; içe aktarma çok dosyada hep-ya-hiç uygulanır.
- FR008: Makine güncellemesi bağlı reçeteleri yeniden doğrular; kullanılan katalog
  kaydının silinmesi reddedilir.
- FR009: Dosya deposu atomik yazar; okunan revizyondan sonra dışarıda değişen veya
  okunamayan dosyaya yazmayı reddeder; eksik dosya boş veritabanıdır.
- FR010: Laser CAM panelinde ince arayüz: malzeme/lens/makine seçimi ve yönetimi,
  arama, reçete tablosu, editöre yükleme, kaydetme, silme, JSON içe/dışa aktarma.
- FR011: İş, proje ve export paketleri reçetenin tam anlık görüntüsünü saklamaya devam
  eder; veritabanı referansı yazılmaz.
- FR012: Test-first; mimari/tam test, masaüstü smoke ve final-head Windows CI kanıtı.

## Uygulama varsayımları (kullanıcı kararı değil)

- UA1 Depolama: stdlib `json` ile tek dosya; SQLite seçilmedi (bkz. research.md).
- UA2 Konum: uygulama veri dizini altında `mikrocam/laser_recipe_db.json`; taşınabilir
  kurulumda Evo'nun `config` veri dizini kullanılır.
- UA3 İçe aktarılan reçeteye malzeme/lens o an seçili olanlardan atanır (varsayılan
  “Belirtilmemiş”); dosyadan veya addan tahmin yapılmaz.
- UA4 Makine adı cihaz profilinin model/profil adıdır; aynı adlı fakat farklı profilli
  makine çakışmadır, otomatik yeniden adlandırma yapılmaz.
- UA5 Görsel satır serpiştirme paneli bu dilimde veritabanı arayüzü almaz; reçete JSON
  ve gömülü reçete akışı korunur.
- UA6 Lens alanları ad ve isteğe bağlı odak uzaklığıyla sınırlıdır; tarama alanı vb.
  not alanına yazılır, yerleşik lens kataloğu yoktur.

## Scope and hazard analysis

Bu dilim veri/arayüz/kalıcılık işidir; makine hareketi, ARM, emisyon veya firmware
yazımı yoktur. Riskler: yanlış malzeme/makine reçetesinin seçilmesi (tablo dört
etiketi birlikte gösterir; seçim editöre açık yükleme ile olur ve mevcut doğrulamadan
geçer), sessiz veri kaybı (onay, revizyon denetimi, atomik yazım, bozuk dosyayı koruma),
profil değişikliğinin eski işleri değiştirmesi (işler anlık görüntü taşır, FR011).
Veritabanındaki bir reçete fiziksel olarak doğrulanmış sayılmaz; fiziksel kabul
cihazda yapılır ve bu dilimde WAITING kalır.
