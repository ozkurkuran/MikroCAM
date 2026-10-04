# Feature specification — Fiducial hizalama (kamera hazırlığı)

Branch: `039-camera-fiducial-alignment`; base origin/main `70800e5b`; 2026-10-04.
Roadmap 1.0 sıra 33: “2 noktayla öteleme ve dönme, 3+ noktayla affine düzeltme; placement
transform'u genişletir” (bağımlılık 4 `placement-transform`). Kullanıcı talimatı
(04.10.2026): “gerçek cihaz onayı beklemeyen tüm görevleri tamamla”. Bu dilimde soru
sorulabilecek kullanıcı yoktur; açık noktalar aşağıda **uygulama varsayımı** olarak
kaydedilmiştir, kullanıcı kararı değildir.

## Kapsam

Kamera görüntüsü yakalama/algılama gerçek kamera gerektirir ve bu dilimin dışındadır
(WAITING). Bu dilim kamerasız tamamlanabilen bütün zinciri teslim eder: fiducial çiftlerinden
transform hesaplama, artık (residual) raporu ve red eşikleri, sürümlü fiducial seti dosyası,
tasarım noktalarını yüklü nesneden seçme veya yazma, makine noktasını yazma veya mevcut tek
iletişim sahibinin (MachineController) son taze durumundan yakalama, UI paneli ve sonucun
önizleme/preflight, dry-run, auto-level, gerçek CNC akışı ve lazer işine **aynı** `Placement`
tipiyle uygulanması.

## User scenarios and acceptance

### US1 — Fiducial çiftlerinden doğrulanmış hizalama (P1)
Operatör en az iki fiducial için tasarım (CAM) koordinatını ve ölçülmüş makine (MPos)
koordinatını girer; yöntemi seçer ve hizalamayı hesaplar.
Bağımsız kabul: 2 noktada rijit (öteleme+dönme) veya açık ölçek politikalı benzerlik;
3+ noktada en küçük kareler affine. Her nokta için artık, RMS/maks artık, dönme, ölçek,
eksen ölçekleri ve fazlalık (redundancy) raporlanır. Eşik aşımı, ayna, aşırı ölçek, yakın
noktalar ve doğrusal (collinear) dizilim reddedilir; reddedilen sonuç uygulanamaz.

Acceptance:
1. İki noktalı rijit/benzerlik ve 3+ noktalı affine, bilinen transformu 1e-9 mm içinde geri bulur.
2. Gürültülü 4+ nokta en küçük kareler çözümü verir; artıklar `Placement.apply_point` ile hesaplanır.
3. Eksik ölçüm, tek nokta, çakışan/doğrusal tasarım noktaları sonuç üretmeden hata verir.
4. Artık, ölçek sapması, ayna veya minimum aralık eşiği aşılırsa sonuç `accepted=False` ve
   gerekçeli olur; tam belirli çözümde (fazlalık 0) “ölçüm hatası görünmez” uyarısı gösterilir.

### US2 — Fiducial setini kaydetme ve noktaları toplama (P2)
Operatör tasarım noktasını seçili Excellon delik merkezlerinden veya Gerber flash
pedlerinden seçer ya da yazar; makine noktasını yazar veya bağlı makinenin taze Idle
durumundan yakalar; seti kaydeder ve yeniden açar.
Bağımsız kabul: `mikrocam.fiducial-set` şema 1 dosyası roundtrip olur; kayıtlı v1 fixture
açılır; bilinmeyen/gelecek sürüm, fazla/eksik alan, inch birim, sonsuz sayı reddedilir.
Yakalama yalnız bağlı, birimi doğrulanmış, taze ve Idle anlık görüntüden yapılır; hiçbir
seri komut göndermez. FakeGRBL ile test edilir.

### US3 — Hizalamayı iş hattına uygulama (P1)
Kabul edilen hizalama preflight kurulumuna tek `Placement` olarak aktarılır. Önizleme ve
preflight zarf kontrolü bu transformu kullanır. Gerçek akış için, orijinal incelemeden ayrı,
XY koordinatları aynı transformla yeniden yazılmış ve yayları kiriş toleransıyla doğrusal
parçalara bölünmüş “hizalanmış iş” türetilir; açıkça girilen/yakalanan G54 XY ile kendi
preflight'ı ve `PreparedJob` doğrulamasından geçer. Dry-run bu türetilmiş işi kullanır;
auto-level ve lazer işi aynı `Placement`'ı doğrudan kullanır.
Bağımsız kabul: hizalanmış iş FakeGRBL'de yalnız türetilmiş blokları gönderir, son konum
transformla uyumludur, Stop mevcut tek sahip yolunu kullanır (Pause/Resume aynı değişmemiş yoldur), gerçek G54 uyuşmazlığında hiçbir
blok gönderilmez; auto-level çıktısı aynı XY'yi üretir; lazer planı aynı noktaları üretir.

## Functional requirements

- FR001 `Placement` tek CAM→makine tipidir; mevcut rijit alanlar korunur, opsiyonel tam
  `affine` katsayıları (a, b, d, e, xoff, yoff) eklenir. İkisi birlikte verilemez;
  tersinmez/sonsuz katsayı reddedilir. Ayrı transform tipi veya kopya transform kodu yoktur.
- FR002 Rijit sonuç rijit `Placement(origin, translation, rotation_deg)` olarak ifade edilir;
  benzerlik/affine sonucu `Placement(affine=...)` olur.
- FR003 Yöntemler: `rigid` (≥2), `similarity` (≥2), `affine` (≥3); varsayılan seçim 2 noktada
  rigid, 3+ noktada affine. En fazla 64 çift.
- FR004 Politika: maks artık (mm), maks ölçek sapması (oran), min nokta aralığı (mm). Rijit
  yöntemde bile gözlenen benzerlik ölçeği raporlanır ve eşikle denetlenir. Ayna (det<0) her
  zaman reddedilir.
- FR005 Doğrusal/çakışan tasarım noktaları ve eksik ölçüm sonuç üretmez (ValueError).
- FR006 Sonuç raporu: çift başına tasarım, ölçülen, hesaplanan, artık vektörü/büyüklüğü;
  RMS, maks, dönme (°), gözlenen ölçek, eksen ölçekleri, determinant, fazlalık, ret gerekçeleri
  ve uyarılar. Reddedilen sonuç `require_placement()` ile alınamaz.
- FR007 `mikrocam.fiducial-set` JSON şema 1: ad, birim mm, yöntem, politika, çiftler (ad,
  tasarım, ölçülen veya null, kullanım). Katı okuma; v1 fixture testi; gelecekteki sürüm ve
  bilinmeyen alan reddi.
- FR008 Tasarım adayları bridge üzerinden seçili Excellon delik ve Gerber flash
  merkezlerinden mm olarak okunur (en fazla 1000); host nesnesi değiştirilmez.
- FR009 Makine yakalama yalnız `MachineSnapshot` okur: CONNECTED, IDLE, stale değil, birim
  doğrulanmış ve MPos mevcut olmalıdır; hiçbir komut/hareket üretmez.
- FR010 Preflight kurulumu kabul edilen hizalamayı açıkça etkinleştirir ve temizler;
  etkinken rijit alanlar devre dışıdır, her değişiklik önceki incelemeyi geçersiz kılar.
- FR011 Hizalanmış iş türetme: kesin taze izinli orijinal preflight, öteleme-dışı placement,
  açık G54 XY, açık kiriş toleransı (0.0001–0.1 mm). Çıktı mm/mutlak/G54, yaylar kirişe
  bölünür, her satır orijinal satıra veya üretilmiş satıra eşlenir; türetilmiş sınırlar
  orijinal incelenmiş sınırları aşmaz; kendi preflight + `PreparedJob` doğrulaması geçer.
- FR012 Dry-run yalnız türetilmiş hizalanmış işe uygulanır; doğrudan affine/dönmeli
  placement reddi korunur. Auto-level, preflight, motion bounds ve lazer planlayıcı aynı
  `Placement`'ı kullanır; yay sınırları affine altında elips ekstremumlarıyla hesaplanır.
- FR013 Rijit alan saklayan mevcut formatlar (lazer job JSON, görsel reçete, görsel export
  manifest) affine placement'ı açıkça reddeder; formatlar ve eski dosyalar değişmez.
- FR014 Kamera yakalama/algılama bu dilimde yoktur; soyut kamera arayüzü eklenmez (anayasa
  III: tek gerçek kullanım doğrulanamıyor). WAITING olarak belgelenir.
- FR015 Testler önce yazılır; Qt'siz core/codec, FakeGRBL akış ve Qt panel testleri; tam suite,
  mimari, pip check ve masaüstü smoke.

## Uygulama varsayımları (kullanıcı kararı değil)

- UV1 Ölçülen koordinatlar makine koordinatıdır (MPos, mm). `PreflightSetup.placement`
  zaten CAM→makine dönüşümüdür; WPos girilirse öteleme hatası oluşur (UI etiketi MPos der).
- UV2 Tasarım koordinatları G-code kaynak çerçevesindedir; FlatCAM nesne koordinatları ile
  aynı varsayılır (CNC işinde ek ofset yoksa). Inch nesneler bridge'de mm'ye çevrilir.
- UV3 Varsayılan eşikler: maks artık 0.05 mm, maks ölçek sapması %0.5, min aralık 10 mm;
  doğrusallık oranı (merkezlenmiş tasarım tekil değerleri) 0.05 sabittir.
- UV4 Ayna hizalaması desteklenmez: alt yüz işleri CAM'de aynalanmış kaynakla gelir; ölçüm
  ayna gösteriyorsa çift sırası hatası kabul edilir.
- UV5 Hizalanmış işte yaylar her zaman kirişe bölünür (affine altında yay elips olur);
  varsayılan kiriş toleransı 0.005 mm, açıkça değiştirilebilir.
- UV6 G54 XY otomatik seçilmez: boş başlar, kullanıcı yazar veya taze durumdaki WCO'dan
  doldurur. Başlatmada mevcut G54 doğrulaması (±0.005 mm) gerçek değeri yeniden kontrol eder.
- UV7 Fiducial seti ölçülen değerleri saklar; bunlar yalnız aynı bağlama/homing için
  geçerlidir. UI yükleme sonrası yeniden ölçüm uyarısı verir.
- UV8 Şema 1 ilk sürümdür; henüz migration adımı yoktur. v1 fixture testi gelecekteki
  şema değişikliğinin migration kapısıdır.
- UV9 Panel preflight dock'undan açılır; yeni legacy menü satırı eklenmez.

## Tehlike analizi (transform makineyi hareket ettirir)

| Tehlike | Neden | Azaltma | Kalan risk |
| --- | --- | --- | --- |
| Yanlış konumda kesme | Çiftlerin karışması | Artık, ölçek, ayna eşikleri; fazlalık 0 uyarısı; ≥3 nokta önerisi | Tam belirli çözümde hata görünmez |
| Sabit öteleme hatası | WPos yerine MPos, eski homing | MPos etiketi, yakalama yalnız taze Idle; dry-run önerisi | Fiziksel referans kayması algılanamaz |
| Hareket halindeyken yakalama | Bayat/çalışan durum | CONNECTED+IDLE+fresh+birim şartı | Mekanik boşluk |
| inch/mm karışıklığı | Yanlış birim | Gözlenen ölçek eşiği; dosya yalnız mm | — |
| Aşırı çarpıtma | Yanlış affine | Eksen ölçeği eşiği, doğrusallık reddi | Eşik içinde küçük hata |
| G54 uyuşmazlığı | Yanlış G54 XY | Başlatmada canlı G54/G92/TLO doğrulaması, aksi halde 0 blok | — |
| Zarf dışı hareket | Dönmüş iş sınırı aşar | Orijinal ve türetilmiş preflight zarf kontrolü, float32 kontrolü | Bildirilen zarf yanlışsa |
| Yay yaklaşıklığı | Kiriş hatası | Açık tolerans, türetilmiş sınırlar orijinal içinde | Tolerans kadar sapma |
| Bayat hizalama | Kart yerinden oynadı | Ayar değişince inceleme geçersiz; belgede yeniden ölçüm | Fiziksel kayma algılanmaz |

Stop/Pause/Abort ve bağlantı kopması mevcut tek iletişim sahibinin yolunu kullanır;
yeni gönderici yoktur. Yazılım kontrolleri fiziksel E-stop/interlock yerine geçmez.

## Success criteria

- SC001 Analitik transformlar 1e-9 mm, gürültülü veriler en küçük kareler optimumu ile geri bulunur.
- SC002 Her ret/degenerate durumda placement uygulanamaz ve akışa 0 bayt gider.
- SC003 Hizalanmış iş, auto-level ve lazer planı aynı `Placement` noktalarını üretir (≤ kiriş toleransı).
- SC004 Mevcut placement, preflight, dry-run, auto-level, lazer ve görsel testleri değişmeden geçer.
- SC005 Fiziksel kamera, makine veya lazer doğrulaması iddia edilmez.
