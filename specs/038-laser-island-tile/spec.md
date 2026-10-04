# Feature specification — Lazer ada (island) ve dama tahtası (checkerboard) tarama

Branch: `038-laser-island-tile`; base `70800e5b`; 2026-10-04.
Roadmap: 0.7 “Lazer olgunlaştırma”, dilim 29 `laser-island-tile` (bağımlılık: 6
`laser-contour-hatch`). Kullanıcı hedefi (04.10.2026): “gerçek cihaz onayı beklemeyen
tüm görevleri tamamla”. Bu dilim yol üretir ve export eder; fiziksel kupon ölçümü ayrıdır.

## User scenarios and acceptance

### US1 — Büyük dolu alanı adalara bölerek tarama (P1)
Kullanıcı hatch'li bir dolgu için ada döşemesini açar; döşeme boyu, örtüşme, tek
paritedeki döşemeler için açı adımı ve sıra (dama tahtası / satır satır) seçer.
Bağımsız kabul: 10×10 mm kare, 5 mm döşeme ve 90° adımla dört döşeme oluşur; komşu
döşemelerin hatch yönü diktir; dama tahtası sırasında kenar paylaşan döşemeler art arda
taranmaz; örtüşme 0 ve açı adımı 0 iken ada hatch'inin birleşimi normal hatch ile aynıdır
(eksik veya çift çizgi yoktur); aynı girdi her çalıştırmada aynı yolları üretir.

### US2 — Export ve kayıt kalıcılığı (P1)
Kullanıcı ada planını her pass için SVG veya DXF ZIP'e aktarır, reçete JSON'unu kaydedip
yeniden açar ve aynı planı tekrar üretir.
Bağımsız kabul: her pass dosyası plan sırasını korur; manifest ada ayarlarını yeni şema
sürümüyle (3) kaydeder ve kayıpsız geri okunur; ada kapalıyken manifest v1/v2 çıktısı
byte düzeyinde değişmez; main kodundan üretilmiş eski v1/v2 manifest dosyaları aynen
açılır ve v3 biçimine kayıpsız yükseltilir; reçete/job JSON formatı değişmez.

### US3 — Laser CAM paneli (P2)
Kullanıcı Laser CAM dock'unda “Island tiling” seçeneğini ve dört ayarı görür.
Bağımsız kabul: ayar değişikliği mevcut önizlemeyi/export'u geçersiz kılar; hatch
kapalıyken ada seçimi açık hata verir; üretilen plan panelde seçilen ayarları taşır;
gerçek masaüstünde Gerber → ada önizlemesi → SVG/DXF ZIP → manifest v3 doğrulanır.

## Functional requirements

- FR-001: `IslandSettings(tile_size_mm, overlap_mm, angle_step_deg, order)` değişmez,
  doğrulanmış düz veridir: döşeme > 0 ve sonlu, 0 ≤ örtüşme < döşeme, açı adımı sonlu,
  sıra `checkerboard` veya `raster`. Ada yalnız hatch ile ve döşeme ≥ hatch aralığı iken geçerlidir.
- FR-002: Döşeme ızgarası kaynak mm orijinine sabitlenir (hücre `[c·T, (c+1)·T)`), bölge
  sınırlarından bağımsızdır; placement plan sonunda bir kez uygulanır.
- FR-003: Hücreler yarı açıktır; örtüşme her hücreyi her yönde `örtüşme/2` genişletir.
  Bir hatch parçası yalnız tamamen hücrenin üst/sağ kenarı üzerindeyse o hücreden düşer;
  böylece örtüşme 0'da kenar çizgisi tam bir döşemede kalır.
- FR-004: Döşeme açısı `hatch açısı + açı adımı × ((sütun + satır) mod 2)`; çizgiler
  orijine sabitli tarama indisleriyle normal hatch ile aynı kuralda kırpılır; cross
  hatch her döşemede iki aileyi korur.
- FR-005: Konturlar önce gelir. `checkerboard`: önce çift parite, sonra tek parite;
  her sınıf içinde satır (y) sonra sütun (x) artan. `raster`: satır sonra sütun.
  Boş döşemeler atlanır. Interlace N her döşemenin kendi hatch'ine uygulanır.
- FR-006: Bölge dışına çizgi çıkmaz; döşemelerin kırpılmış alanlarının birleşimi bölgeyi
  tam kapsar; her bölge noktası hatch aralığı mesafesinde bir çizgiye sahiptir.
- FR-007: En fazla 10 000 aday döşeme, mevcut 50 000 aday tarama çizgisi ve 200 000 yol
  sınırı; aşım açık hata; iptal kısmi sonuç yayınlamaz.
- FR-008: SVG/DXF dosyaları her pass için plan sırasını korur; manifest şema 3 `island`
  ve null olabilen `device` alanı taşır; README ada sırasının hedef optimizasyonuyla
  bozulabileceğini yazar. Ada kapalı export'lar eski v1/v2 çıktısını aynen üretir.
- FR-009: Manifest okuyucu 1, 2 ve 3'ü okur; bilinmeyen/eksik alan ve gelecek sürüm
  reddedilir; `upgrade_manifest` v1/v2'yi `island: null` ile v3'e kayıpsız taşır.
- FR-010: Reçete/job JSON şemaları değişmez; reçete JSON kaydet/aç sonrası aynı ada planı üretilir.
- FR-011: UI ince kalır; ayarları toplar, alan fonksiyonunu çağırır, hatayı gösterir.
- FR-012: Test-first; mimari sınır/legacy büyüme, tam paket, masaüstü smoke ve PR
  final-head Windows CI kanıtı ile teslim edilir.

## Uygulama varsayımları (kullanıcı kararı değildir)

Kullanıcıya soru sorulamadığından açık noktalar aşağıdaki uygulama varsayımlarıyla
kapatıldı; her biri ileride kendi spec'iyle değiştirilebilir.

- UV-1: Açı rotasyonu dama tahtası paritesine bağlıdır (çift: taban açı, tek: taban +
  adım). Döşeme sırasına göre artan (ör. 67°) rotasyon kapsam dışıdır.
- UV-2: Örtüşme komşu iki döşeme arasındaki toplam örtüşme genişliğidir.
- UV-3: Ada ayarları reçeteye değil geometrik plan seçeneklerine (`PlanOptions`) aittir;
  006/007'deki hatch aralığı/açı/interlace gibi panel girdisidir. Kalıcı kayıt export
  manifest'idir (interlace_n gibi). Reçete/job JSON değişmez; 037 reçete DB ile çakışma
  bu yüzden en aza indirilir.
- UV-4: Dama tahtası garantisi aynı parite sınıfı içindeki ardışık döşemeler içindir;
  iki sınıf arasındaki tek geçişte komşuluk küçük ızgaralarda kaçınılmaz olabilir.
- UV-5: Interlace N ada ile birlikte kullanılabilir ve her döşeme içinde uygulanır.
- UV-6: Panel başlangıç değerleri (5 mm döşeme, 0 mm örtüşme, 90° adım, dama tahtası)
  geometrik başlangıç değeridir; malzeme/cihaz preset'i değildir.
- UV-7: Konturlar adalara bölünmez; yalnız hatch dolgusu döşenir.

## Tehlike analizi

Bu dilim yalnız yol geometrisi, sıralama ve dosya export'u üretir; makineyi hareket
ettirmez, seri port/kamera/lazer açmaz, ARM veya emisyon yapmaz. Riskler: (1) yanlış
kapsama — eksik/çift tarama yanlış ısıl yük veya yetersiz işleme doğurabilir; kapsama ve
yineleme testleri ile ele alınır. (2) Hedef uygulamanın yol optimizasyonu ada sırasını
bozabilir; README/doküman bunu açıkça yazar. (3) Isı dağıtımı iddiası yoktur: dama
tahtası sıralaması fiziksel ısıl doğrulama değildir; fiziksel kupon ölçümü WAITING kalır.

## Success criteria

- SC-001: Kapsama/eşdeğerlik/sıra/determinizm testleri Qt'siz geçer.
- SC-002: Eski v1/v2 manifest fixture'ları byte-kayıpsız açılır, v3 roundtrip eşittir.
- SC-003: Tam paket, mimari testler ve masaüstü smoke PASS; fiziksel doğrulama iddiası yok.
