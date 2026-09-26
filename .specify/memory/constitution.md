# MikroCAM Anayasası

MikroCAM; PCB CAM, CNC kontrolü, probing ve fiber lazer CAM'i tek uygulamada birleştirir. Kapsam
geniş olduğu için bu anayasanın asıl amacı şudur: **ürün büyüdükçe karmaşıklık büyümeyecek.**
Kurallar kod incelemesinde veya otomatik testle doğrulanabilecek biçimde yazılmıştır.

Terimler:

- **Taban**: FlatCAM Evo. MikroCAM reposu `mekatrol/flatcam`'in fork'udur. Python 3.13'e taşınmış
  FlatCAM 8.994 ayrı bir repoda altın referans olarak durur.
- **Legacy host**: Evo'dan gelen, `mikrocam/` dışındaki tüm uygulama kodu (`app*` modülleri ve
  paketleri, `camlib.py`, `tclCommands/`, `preprocessors/` vb.).
- **Yeni kod**: `mikrocam/` paketi altındaki her şey.
- **Lisans modeli**: MikroCAM açık kaynaktır ve GitHub'da herkese açık, MIT lisansıyla yayınlanır.
  Satış planı yoktur.

## Core Principles

### I. Katmanlar ve Tek Yönlü Bağımlılık

Yeni kod dört katmandan oluşur. Her katman yalnızca kendi altındakileri import edebilir:

```text
legacy host ─▶ mikrocam.ui ─▶ mikrocam.bridge ─▶ mikrocam.<alan> ─▶ mikrocam.core
```

- `mikrocam.core`: Birimler, geometri tipleri, koordinat transform'u ve iş (job) modelleri.
  Yalnızca stdlib, NumPy ve Shapely kullanabilir. Qt, donanım I/O'su ve legacy import'u YASAKTIR.
- `mikrocam.<alan>` (ör. `importers`, `machine`, `probe`, `laser`): Yalnızca `core`'u import eder.
  PyQt6 ve legacy import'u YASAKTIR. Alanlar birbirini import etmez; ortak ihtiyaç `core`'a taşınır.
- `mikrocam.bridge`: Legacy nesneleri (Gerber, Excellon, Geometry, CNCJob…) ile `core` tipleri
  arasındaki TEK çeviri katmanıdır. Legacy'yi import edebilen tek yeni kod paketidir.
- `mikrocam.ui`: PyQt6 panelleri. İş mantığı içermez: Girdiyi toplar, alan fonksiyonunu çağırır,
  sonucu gösterir.
- Ayrı süreçte çalışan entegrasyonlar (ör. KiCad eklentisi) uygulamayı import etmez. Uygulamayla
  sürüm numaralı bir dosya formatı üzerinden konuşur.
- Bu kurallar CI'da otomatik bir import-sınır testiyle doğrulanır.

Gerekçe: Evo'nun iç yapısı upstream'de değişirse yalnızca `bridge` etkilenir. Qt'siz çekirdek,
ekran ve donanım olmadan test edilebilir.

### II. Legacy Sınırlama

- Legacy host dosyalarına yeni özellik mantığı EKLENMEZ. İzin verilenler: (a) hata düzeltmesi,
  (b) bir `mikrocam` özelliğini menüye veya araç listesine bağlayan kısa bağlantı kodu.
- Legacy değişiklikleri bilinçli olarak küçük tutulur. Böylece upstream Evo güncellemeleri
  çakışmasız alınabilir.
- Büyüme bütçesi: Legacy host'un en büyük modülleri (ana uygulama modülü, `camlib.py` ve benzerleri)
  birlikte feature başına en fazla +50 satır büyüyebilir. Hangi dosyaların izleneceği
  foundation-guardrails feature'ında belirlenir ve bir büyüme testi (ratchet) bu dosyaların kayıtlı
  satır sayılarını izler. Bütçeyi aşmak, plan.md "Complexity Tracking" tablosunda gerekçelendirilir.
- Legacy'den kod silen veya kodu `mikrocam`'e taşıyan değişiklikler teşvik edilir. Ancak taşınan
  davranış önce testle korunmalıdır. Upstream'le çakışma riskini artıran taşımalar gerekçelendirilir.
- Dış kaynaklardan (kpkrisnop, FlatCAM 9 Neo S2, dwrobel) modül toptan kopyalanmaz ve repo
  birleştirilmez. Önce davranış bir testle tanımlanır, sonra doğru katmana port edilir. Upstream
  Evo güncellemeleri kendi commit'leri olarak merge edilir; diğer değişikliklerle karıştırılmaz.

### III. Basitlik: Somut İhtiyaç Olmadan Soyutlama Yok

- Soyut sınıf/Protocol, plugin noktası, registry veya yeni ayar seçeneği ancak en az iki somut
  kullanımı varsa eklenir. Donanım sınırında gerçek uygulama ile Fake uygulama iki kullanım sayılır.
- Roadmap'teki listeler (Serial/TCP/HTTP/WebSocket; GRBL/grblHAL/FluidNC/Marlin…) yapılacak işler
  değil, seçeneklerdir. Her ek transport, controller veya backend gerçek bir ihtiyaçla, kendi
  spec'iyle gelir.
- Genel amaçlı altyapı yazılmaz: DI container, event bus, genel plugin yükleyici veya özel ORM
  kullanılmaz. Qt sinyalleri ve düz fonksiyon çağrıları yeterlidir.
- Yeni runtime bağımlılığı için plan.md'ye gerekçe, lisans ve değerlendirilen alternatif yazılır;
  sürümü sabitlenir. Ağır veya opsiyonel bağımlılıklar (PDF, raster, kamera, KiCad) lazy import
  edilir; uygulama bunlar yüklü olmadan da açılmalıdır.
- Feature flag yalnızca yarım veya riskli özellik için kullanılır. Hepsi tek bir yerde tanımlanır,
  kaldırılma koşulu yazılır ve özellik kararlı hâle geldikten sonraki sürümde flag silinir.

### IV. Tek Doğruluk Kaynağı

- Birim: Yeni kodda iç birim mm'dir. Inch dönüşümü yalnızca sınırda (import, export, UI) yapılır.
- Koordinat: CAM'den makineye dönüşüm (öteleme, dönme, ayna, fixture origin; ileride
  fiducial/affine) `core` içinde TEK bir tiptir. Önizleme, simülasyon, probing, dry-run ve gerçek iş
  aynı transform'u kullanır. Kopya transform kodu YASAKTIR.
- Parametre: Takım ve recipe değerleri tek bir yerden okunur. İstenen değer bulunamazsa sessizce
  global default'a düşülmez; hata veya uyarı verilir.
- CNC ve lazer ayrı iş modelleridir (`CNCJob` ≠ `LaserJob`). Lazer parametreleri CNC modeline,
  lazer recipe'leri de Tool DB'ye rastgele anahtarlar olarak eklenmez.
- İş modelleri donanımdan bağımsız, serileştirilebilir düz veridir (dataclass). Cihaza özgü çeviri
  yalnızca backend'de yapılır; backend desteklemediği bir alanı sessizce yok saymaz, açıkça reddeder.
- Ürün kimliği (ad, sürüm, About metni) tek bir modülde tutulur.
- Kalıcı formatlar (proje, recipe DB, makine profili, KiCad transfer paketi) bir şema sürümü taşır.
  Her şema değişikliğinde bir migration ve eski dosyayı açan bir test eklenir.

### V. Donanımsız ve Önce-Test Doğrulama

- `core` ve alan paketlerindeki her davranış pytest ile test edilir. tasks.md'de bu modüllerin test
  görevleri uygulama görevlerinden önce gelir. Bu testler Qt, OpenGL veya donanım gerektirmez.
- Makine ve galvo kodu CI'da Fake controller'a karşı test edilir: ok, error, alarm, gecikmeli ACK,
  bağlantı kopması, limit ve probe senaryoları. Gerçek donanım testi bunların yerine geçmez, onlara
  eklenir.
- Her hata düzeltmesinde önce hatayı yeniden üreten bir test eklenir.
- Parser ve geometri değişiklikleri `tests/reference/` veri setiyle, toleranslı olarak
  karşılaştırılır. Altın referans, ayrı repodaki Python 3.13'e taşınmış FlatCAM 8.994 ile
  değişmemiş Evo tabanının (`upstream-evo-baseline`) çıktılarıdır.
- UI ince tutulduğu için UI testleri duman testi (smoke) düzeyindedir (`tests/smoke_app.py`).

### VI. Güvenlik Önce (Makine ve Lazer)

- CAM kodu donanıma asla doğrudan yazmaz. Zincir şöyledir: Job → MachineController → Transport →
  donanım.
- Controller durumu açık bir durum makinesidir (DISCONNECTED, IDLE, JOG, PROBING, RUNNING, PAUSED,
  ALARM/ERROR/ESTOP). UI yalnızca mevcut durumun izin verdiği komutları etkin gösterir.
- Stop/abort yolu her durumdan erişilebilir ve Fake controller ile test edilir. Bağlantı kopması
  veya zaman aşımında hareket ve emisyon durdurulur (fail-safe).
- Lazer emisyonu ancak ön kontroller geçtikten sonra (bağlantı, interlock, kapı, e-stop, kaynak
  hazır, iş sınırları, odak, recipe) ayrı bir ARM adımıyla mümkün olur.
- Yazılım kontrolleri fiziksel interlock'un yerine geçmez. Bu, kullanıcı dokümantasyonunda açıkça
  yazılır.
- Makineyi hareket ettiren veya lazeri ateşleyen her spec'te bir "Tehlike analizi" bölümü bulunur.
- Makine iletişimi (tx/rx) ve iş olayları, tanı için loglanabilir olmalıdır.

### VII. Lisans ve Kaynak İzlenebilirliği

- Kod yalnızca MIT, BSD veya Apache-2.0 uyumlu kaynaklardan port edilir. Orijinal telif bildirimleri
  korunur.
- Dış kaynaklı her değişiklik `THIRD_PARTY_CHANGES.md` dosyasına işlenir: kaynak repo, commit,
  dosya, lisans, gerekçe, yapılan değişiklik ve MikroCAM commit'i.
- FlatCAM-Plus'ın non-commercial modüllerinin (CNC Control, Plotter, 3D Preview, AI Assistant) kodu
  ASLA kopyalanmaz. Satış planı olmaması bunu değiştirmez: Public MIT repo, bu kodu başkalarının
  ticari kullanımına açmış olur. Karşılık gelen MikroCAM özelliği temiz oda yöntemiyle geliştirilir:
  gereksinim → spec → bağımsız uygulama. Uygulamayı yapan kişi veya ajan bu modüllerin kaynak kodunu
  açmaz; yalnızca README, ekran görüntüsü ve davranış incelenebilir. FlatCAM-Plus bu nedenle git
  remote'u olarak eklenmez.
- Yeni bağımlılık OSI onaylı bir açık kaynak lisansa sahip olmalıdır; lisansı plan.md'ye ve
  `THIRD_PARTY_LICENSES/`'a yazılır. GPL ve LGPL bağımlılıklar (ör. PyQt6, GPLv3) kabul edilir.
  AGPL bağımlılıklar yalnızca opsiyonel extra olarak eklenir ve izin verici bir alternatif
  değerlendirildikten sonra seçilir.
- Non-commercial, kapalı kaynak veya dağıtılamayan kod ve ikili dosyalar (ör. üretici SDK'ları)
  repoya konmaz. İleride gerekirse, kullanıcının ayrıca kurduğu opsiyonel bir bağımlılık olarak ve
  kendi spec'iyle eklenir.

## Teknik Kısıtlar

- **Python**: CPython 3.13.x, 64-bit. Doğruluk kaynağı `.python-version` dosyasıdır; 3.13'ten yeni
  sözdizimi veya stdlib özelliği kullanılmaz. Free-threaded build hedeflenmez. Python minor sürüm
  yükseltmesi (3.14) kendi spec'iyle yapılır.
- **Yığın**: PyQt6, VisPy, Shapely 2.x, NumPy 2.x. Sürümler `requirements*.txt` içinde `==` ile
  sabitlenir ve `pip check` temiz olmalıdır.
- **Platform**: Birincil hedef Windows 11 x64; Linux ikincil. macOS kendi spec'i olmadan kapsam
  dışıdır.
- **Thread'ler**: Arka plan worker'ları Qt widget'larına dokunmaz; sonuçları sinyalle GUI
  thread'ine gönderir. `core` ve alan kodu global değiştirilebilir durum tutmaz.
- **Kod boyutu**: Yeni modül 600, yeni fonksiyon 80 satırı aşmaz. Aşım Complexity Tracking'de
  gerekçelendirilir.
- **Kod stili**: `mikrocam` public API'si type hint taşır. Kod, isimler ve docstring'ler
  İngilizcedir. UI metinleri mevcut çeviri sistemi (`_()`) üzerinden geçer.

## Geliştirme Akışı ve Kalite Kapıları

- **Spec-kit ne zaman kullanılır**: Yeni kullanıcı özelliği, yeni paket veya modül, yeni kalıcı
  format ve her türlü makine/lazer davranışı için tam akış uygulanır: `/speckit-specify` →
  (`/speckit-clarify`) → `/speckit-plan` → `/speckit-tasks` → (`/speckit-analyze`) →
  `/speckit-implement`.
- **Spec gerekmeyen işler**: Hata düzeltmesi, davranışı değiştirmeyen refactor, bağımlılık patch
  güncellemesi ve doküman değişikliği. Bunlar doğrudan yapılır; yine de testle birlikte gelir.
- **Feature boyutu**: Bir feature, tek başına teslim edilebilen tek bir değer sunar. En fazla 3 user
  story ve 40 görev içerir; aşarsa bölünür. Roadmap fazları feature değildir; iş
  `docs/ROADMAP.md`'deki dilimlerden seçilir.
- **Plan kapısı** — plan.md'deki "Constitution Check" bölümü şu soruları evet/hayır olarak
  yanıtlar. Her "hayır", Complexity Tracking'de gerekçe ve reddedilen basit alternatifle yer alır:
  1. Yeni mantık `mikrocam/` altında mı ve katman yönüne uyuyor mu? (I)
  2. Legacy dosyalara yalnızca düzeltme/bağlantı kodu mu ekleniyor ve toplam +50 satırın altında
     mı kalıyor? (II)
  3. Her yeni soyutlamanın iki somut kullanımı var mı? Yeni bağımlılık gerekçeli, sabitlenmiş ve
     lisansı yazılı mı? (III, VII)
  4. Birim, transform, parametre ve format tek kaynaktan mı geliyor? Yeni kalıcı format şema sürümü
     taşıyor mu? (IV)
  5. Testler donanımsız ve ekransız çalışıyor mu? Test görevleri uygulamadan önce mi? (V)
  6. Makine veya lazer davranışı varsa tehlike analizi, durum makinesi ve stop yolu testi var mı?
     (VI)
  7. Dış kaynaklı kod varsa lisansı uygun mu, kaydı tutuldu mu, temiz oda kuralına uyuluyor mu?
     (VII)
  8. Feature en fazla 3 user story ve 40 görev içeriyor mu?
- **Merge kapısı**: `pytest` yeşil; import-sınır ve legacy büyüme testleri yeşil; GUI'ye
  dokunulduysa smoke test yeşil; dış kod kullanıldıysa `THIRD_PARTY_CHANGES.md` güncel.
- **Commit**: Her commit tek bir mantıksal değişiklik içerir. Upstream port'ları ayrı commit olarak
  yapılır.

## Governance

- Bu anayasa, roadmap dahil diğer tüm dokümanlardan üstündür. Roadmap ile çelişirse anayasa
  geçerlidir ve roadmap güncellenir.
- Değişiklikler `/speckit-constitution` ile yapılır ve semantik sürümlenir: MAJOR = ilke kaldırma
  veya yeniden tanımlama, MINOR = yeni ilke veya bölüm, PATCH = ifade düzeltmesi.
- **Karmaşıklık incelemesi**: Her MikroCAM minor sürümünden önce kullanılmayan feature flag'ler
  silinir, tek uygulaması kalmış soyutlamalar sadeleştirilir, legacy satır bütçesi ve bağımlılık
  listesi gözden geçirilir.
- Günlük çalışma rehberi `CLAUDE.md`, feature sırası `docs/ROADMAP.md` dosyasındadır.

**Version**: 1.1.0 | **Ratified**: 2026-09-26 | **Last Amended**: 2026-09-26
