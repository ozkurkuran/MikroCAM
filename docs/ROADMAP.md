# MikroCAM Yol Haritası

Bu dosya, "MikroCAM Geliştirme ve Repo Birleştirme Yol Haritası" (26.09.2026) dokümanını verilen
kararlarla günceller ve spec-kit feature'larına böler. Orijinal araştırma dokümanı
`docs/research/mikrocam-yol-haritasi.md` konumuna eklenecektir; gerekçe ve ayrıntı için oraya
başvurulur. Kurallar `.specify/memory/constitution.md` dosyasındadır; çelişki olursa anayasa
geçerlidir.

## Verilen kararlar (26.09.2026)

| # | Konu | Karar |
| --- | --- | --- |
| K0 | Taban kod | **FlatCAM Evo.** MikroCAM, `mekatrol/flatcam`'in fork'u olur. Python 3.13'e taşınmış FlatCAM 8.994 ayrı bir repoda altın referans olarak kalır. |
| K1 | Lisans ve dağıtım | **Açık kaynak, GitHub'da herkese açık, MIT.** Satış planı yok. PyQt6'nın GPLv3 lisansı açık kaynak dağıtımla uyumludur. |
| K2 | Doğrudan galvo kontrolü | **Sona ertelendi.** Lazer işleri LightBurn veya EZCAD'e export edilerek çalıştırılır. |
| K3 | Makine kontrolü | **GRBL + Serial** yeterli. Mach3 ileride düşünülebilir (aşağıdaki nota bakın). |
| K4 | Öncelik | Önce ilk gerçek lazer PCB'ye giden kısa yol; ardından mekanik CAM stabilizasyonu ve GRBL kontrolü. |
| K5 | Sona ertelenenler | Arayüzün baştan tasarımı (Faz 3), feature flag sistemi, termal zamanlayıcı, galvo kontrolü. |

## Orijinal yol haritasından farklar

- **Python sürümü:** Python 3.11 geçen her yer **3.13** olarak okunur (CI dahil). "NumPy 1.26"
  yerine NumPy 2.x kullanılır.
- **Klasör yapısı:** Yeni kod, yol haritasındaki legacy içi klasörlere (`appPlugins/ToolLaserCAM/`
  gibi) değil, anayasa I'deki `mikrocam/` katmanlarına yazılır. Evo tarafına yalnızca ince bağlantı
  kodu eklenir. Böylece upstream Evo güncellemeleri çakışmasız alınır.
- **Sıra:** Lazer 0.5'ten 0.2'ye çekildi, import (Neo S2) 0.5'e kaydı, Faz 3 UI ertelendi.
- **Neo S2 port'ları:** Neo S2 8.994 soyundan geldiği için Evo'ya port daha zordur. Her özellik için
  önce Evo'da bir karşılığı olup olmadığına bakılır; karşılığı varsa port edilmez.
- **kpkrisnop düzeltmeleri:** Evo'ya doğrudan uygulanabilir. Bunlar hata düzeltmesi olduğu için spec
  gerektirmez (anayasa: Geliştirme Akışı). Cherry-pick, regresyon testi ve `THIRD_PARTY_CHANGES.md`
  kaydı yeterlidir.
- **LaserJobObject:** Baştan yeni bir FlatCAM nesne tipi eklenmez. Önizleme mevcut Geometry nesnesiyle
  yapılabiliyorsa o kullanılır (anayasa III).
- **Yeni proje formatı (`.mcam`):** Faz 3'le birlikte ertelendi. Evo'nun proje formatı yetmediği
  anda (ör. LaserJob'u projede saklamak gerektiğinde) kendi spec'iyle eklenir.

## Hazırlık (spec-kit öncesi, tek seferlik)

**26.09.2026 durum kaydı:** Repolar, tag'ler ve remote'lar oluşturuldu. Kullanıcı seçimiyle
fork, Bitbucket `Beta_1.0` dalının `e046a2a3` commit'ine güncellendi; ilk fork ve güncel
upstream ayrı tag'lerle korundu. Spec-kit dosyaları bu repoya aktarıldı. Orijinal araştırma
belgesinin kaynak dosyası henüz sağlanmadı. Kanıtlar ve kalan iş: [PREPARATION.md](PREPARATION.md).

1. Bu dizindeki 8.994-py3.13 portunu commit edip `baseline-8.994-py313` tag'ini at ve ayrı bir
   public repo olarak yayınla. Altın referans çıktıları bu repodan üretilecek.
2. GitHub'da `mekatrol/flatcam`'i **MikroCAM** adıyla fork et. Bu fork'un Bitbucket'taki upstream
   `marius_stanciu/flatcam_beta`'nın gerisinde kalmadığını kontrol et.
3. Hiçbir şeyi değiştirmeden `upstream-evo-baseline` tag'ini at.
4. Şu remote'ları ekle: `evo` (mekatrol), `kpkrisnop`, `neo` (Neo S2), `dwrobel` ve `legacy8994`
   (1. adımdaki repo). **FlatCAM-Plus remote olarak eklenmez**, çünkü kodunun repoya inmesi temiz oda
   kuralını (anayasa VII) deler. README'si ve ekran görüntüleri tarayıcıdan incelenir.
5. Spec-kit dosyalarını (`.specify/`, `.claude/skills/`, `CLAUDE.md`, `docs/`) ve `.gitignore`'daki
   `.claude/settings.local.json` satırını yeni repoya taşı. Orijinal araştırma dokümanını
   `docs/research/` altına ekle.

## Kilometre taşları ve dilimler

Spec-kit feature numarasını (`001-…`) sırayla verir. `Kısa ad` sütunu, `/speckit-specify` için
önerilen addır. Her kilometre taşının sonundaki "Çıktı", gerçekten kullanılabilir bir sonuç olmalıdır.

### 0.1 — Evo tabanı

**Çıktı:** Python 3.13'te çalışan, MikroCAM adını taşıyan ve koruma rayları kurulu Evo.

| Sıra | Kısa ad | Kapsam | Bağımlılık |
| --- | --- | --- | --- |
| 1 | `evo-py313-baseline` — **tamamlandı** | Evo Beta_1.0, Windows 11 / CPython 3.13 x64. Sabitlenmiş bağımlılıklar, iki temiz kurulum, 511 geçen test + 310 subtest ve üç başarılı GUI/CAM duman döngüsü. İki upstream boş Qt test taslağı hâlâ atlanır. [Doğrulama](../specs/001-evo-py313-baseline/validation.md). | Hazırlık |
| 2 | `foundation-guardrails` — **tamamlandı** | `mikrocam/core` iskeleti, Python sürüm bildirimi, import sınırı ve en büyük on legacy modül için feature başına +50 satır denetimi. Windows CI: 594 test + 310 subtest başarılı; iki upstream taslak atlanır. [Doğrulama](../specs/002-foundation-guardrails/validation.md). | 1 |
| 3 | `branding-and-notices` — **tamamlandı** | Tek ürün kimliği, MikroCAM başlık/About; kaynak MIT, FlatCAM/Evo telifleri ve 58 bağımlılığın lisansları korunur (PyQt6 GPLv3 dahil). Windows CI: 639 test + 310 subtest; gerçek GUI/CAM duman testi başarılı. Eski artwork ve opsiyonel DLL bildirim açıkları ikili paketleme öncesi NOTICE içinde kayıtlıdır. [Doğrulama](../specs/003-branding-and-notices/validation.md). | 2 |

### 0.2 — İlk lazer PCB

**Çıktı:** Gerber'den fiber lazer yolları üretilir ve LightBurn veya EZCAD'de çalıştırılarak ilk
gerçek PCB elde edilir.

**Yazılım durumu (27.09.2026):** 4–8 dilimleri tamamlandı. Gerber → önizleme → iki geçişli
SVG/DXF paketleri gerçek MikroCAM masaüstünde doğrulandı. Hedef LightBurn/EZCAD uygulamasında
içe aktarma ve fiziksel PCB kuponu henüz doğrulanmadığı için kilometre taşının fiziksel
çıktısı açıktır. [Aktarım ve doğrulama rehberi](LASER_CAM.md).

| Sıra | Kısa ad | Kapsam | Bağımlılık |
| --- | --- | --- | --- |
| 4 | `placement-transform` — **tamamlandı** | Tek core transform: origin, öteleme, dönme ve ayna; nokta/geometri uygulaması ve ters dönüşüm. Windows CI: 694 test + 310 subtest başarılı. [Doğrulama](../specs/004-placement-transform/validation.md). | 2 |
| 5 | `laserjob-model` — **tamamlandı** | Ayrı, değişmez LaserJob ve sıralı pass recipe'leri; katı şema-1 JSON; Gerber'in mevcut birimlerinden mm core verisine köprü. Windows CI: 823 test + 310 subtest başarılı. [Doğrulama](../specs/005-laserjob-model/validation.md). | 4 |
| 6 | `laser-contour-hatch` — **tamamlandı** | Dış/iç/iz/pad/kart konturları, kırpılmış açılı/çapraz hatch, açık alan seçimi, iptal edilebilir Laser CAM paneli ve Geometry önizlemesi. Gerçek masaüstü döngüsü ve Windows CI: 944 test + 310 subtest başarılı. [Doğrulama](../specs/006-laser-contour-hatch/validation.md). | 5 |
| 7 | `hatch-interlace-multipass` — **tamamlandı** | Interlace N, boşlukları koruyan sıra; her pass için açık parametreli recipe düzenleyici ve atomik JSON kaydı. İki geçişli masaüstü döngüsü; Windows CI: 995 test + 310 subtest başarılı. [Doğrulama](../specs/007-hatch-interlace-multipass/validation.md). | 6 |
| 8 | `laser-export-svg-dxf` — **yazılım tamamlandı** | Her pass için mm SVG/DXF, recipe ve şemalı eşleme içeren atomik ZIP; iptal edilebilir panel aktarımı. Windows CI: 1110 test + 310 subtest başarılı. Hedef uygulama/fiziksel doğrulama açık. [Doğrulama](../specs/008-laser-export-svg-dxf/validation.md). | 7 |

### 0.3 — Güvenilir mekanik CAM

**Çıktı:** Evo'nun Drilling, Isolation ve Milling araçları Tool DB değerleriyle doğru G-code üretir.

| Sıra | Kısa ad | Kapsam | Bağımlılık |
| --- | --- | --- | --- |
| 9 | `reference-dataset` — **tamamlandı** | Yedi CAD kaynağından 10 gerçek PCB; lisans/hash izli 60 dosya ve iki tabandan tekrarlanabilir 20 altın çıktı. Açık toleranslı geometri/yol/G-code karşılaştırması: güncel Evo için 47 eşleşme, iki boş NPTH kaydı belirsiz. Windows CI: 1315 test + 310 subtest. [Doğrulama](../specs/009-reference-dataset/validation.md). | 1 |
| — | kpkrisnop düzeltmeleri *(spec yok)* — **tamamlandı** | Kanıtlanan Tool DB aktarım/default sorunları; Excellon araç çoğaltılması ve kuyruğa alınmış drill işlerinin çıktı birikmesi; görünüm seviyesi değişirken machining değerlerinin korunması; silme sırasında worker/widget ve geç şekil gönderimi yarışları düzeltildi. Ayrı MIT uyarlama/bağımsız düzeltme commitleri ve davranış regresyonları; Windows tam test: 1369 geçen + 310 subtest, iki upstream taslak atlanır; gerçek masaüstü CAM/proje/lazer/shutdown döngüsü başarılı. [Doğrulama](MECHANICAL_CAM_VALIDATION.md). | 9 |

### 0.4 — GRBL makine kontrolü

**Çıktı:** CNC'ye MikroCAM'den bağlanılır, sıfırlanır, iş önceden doğrulanır ve güvenle çalıştırılır.

| Sıra | Kısa ad | Kapsam | Bağımlılık |
| --- | --- | --- | --- |
| 10 | `machine-connect-grbl` — **yazılım tamamlandı** | Açık port seçimiyle salt okunur GRBL bağlantısı; doğrulanmış mm makine/iş koordinatları, eski/geçersiz veriyi temizleme ve sahipli worker kapanışı. Yerel 1563 test + 310 subtest ve gerçek masaüstünde FakeGRBL döngüsü başarılı; fiziksel cihaz doğrulaması açık. [Doğrulama](../specs/010-machine-connect-grbl/validation.md). | 2 |
| 11 | `jog-and-work-zero` — **yazılım tamamlandı** | Sınırlı jog, açık G54 seçimi ve doğrulanmış XY/Z/XYZ sıfırlama; tek işlem ve öncelikli iptal/kapatma. 1967 test + 310 subtest, 10 Qt döngüsü ve gerçek masaüstünde FakeGRBL akışı başarılı; fiziksel cihaz doğrulaması açık. [Doğrulama](../specs/011-jog-and-work-zero/validation.md). | 10 |
| 12 | `gcode-preflight` — **tamamlandı** | Açık kurulumla salt okunur G-code analizi; tam doğrusal/yay sınırları, birim/mod, feed, rapid/Z ve nominal süre. 2286 test + 310 subtest; seçili CNC işi/dosya ve tehlikeli rapid için gerçek masaüstü akışı ve son commit Windows CI başarılı. [Doğrulama](../specs/012-gcode-preflight/validation.md). | 4 |
| 13 | `job-streaming` — **yazılım tamamlandı** | Ön kontrolle bağlı değişmez mekanik CNC işi, canlı G54/konum/ayar doğrulaması, tek ACK sahibi, pause/resume/stop ve gerçek tamamlanma kanıtı. 2509 test + 310 subtest; gerçek masaüstünde FakeGRBL aktarım/çalıştırma/durdurma/kapanış ve son commit Windows CI başarılı. Fiziksel cihaz doğrulaması açık. [Doğrulama](../specs/013-job-streaming/validation.md). | 11, 12 |
| 14 | `dry-run` — **tamamlandı** | Kaynak korunarak açık makine Z düzleminde ayrı XY işi; ilk yukarı Z hareketi, spindle/soğutma açma komutlarının çıkarılması, yeni ön kontrol ve kaynak satır eşlemesi. 2564 test + 310 subtest; gerçek masaüstünde FakeGRBL aktarım, yay projeksiyonu ve aktif iş kapanışı başarılı. [Doğrulama](../specs/014-dry-run/validation.md). | 13 |
| 15 | `machine-console` — **tamamlandı** | Tek iletişim sahibinde altı salt okunur sorgu; sınırlı ve kaçışlı ham TX/RX kaydı, açık yazma sonucu ve hata/kapanışta kanıt koruma. 2721 test + 310 subtest; gerçek masaüstünde sorgular, Clear ve bekleyen sorguyla kapanış başarılı. [Doğrulama](../specs/015-machine-console/validation.md). | 10 |

### 0.5 — İçe aktarma (Neo S2 port'ları)

**Çıktı:** Proteus, Illustrator ve Inkscape kaynaklı SVG/DXF dosyaları doğru ölçekte, drill'leriyle
birlikte içe aktarılır.

| Sıra | Kısa ad | Kapsam | Bağımlılık |
| --- | --- | --- | --- |
| 16 | `svg-scale-transforms` — **tamamlandı** | Fiziksel viewBox/birimler, tam dönüşüm sırası, miras alınan stroke ve katı malzeme; Geometry/Gerber kaynak koruma. 3084 test + 310 subtest ve gerçek masaüstü save/reopen ve son commit Windows CI başarılı. [Doğrulama](../specs/016-svg-scale-transforms/validation.md). | 9 |
| 17 | `import-report` — **tamamlandı** | Kaynağa bağlı ölçek/birim, geometri geçerliliği, açık/kapalı path ve hassasiyet raporu; nesne seçimi ve proje kaydı boyunca korunur. 3218 test + 310 subtest, gerçek masaüstü ve son commit Windows CI başarılı. [Doğrulama](../specs/017-import-report/validation.md). | 16 |
| 18 | `svg-drill-detection` — **yazılım tamamlandı** | Fiziksel daire/pad kanıtı, açık aday seçimi, çakışma denetimi ve çap gruplu Excellon. 3380 test + 310 subtest, gerçek masaüstünde export/proje roundtrip ve son commit Windows CI başarılı. Gerçek Proteus SVG örneği doğrulaması açık. [Doğrulama](../specs/018-svg-drill-detection/validation.md). | 16 |
| 19 | `svg-illustrator` — **yazılım tamamlandı** | XMP sayfa ölçüsü, sınırlı CSS/görünür katmanlar, bileşik dolgu ve yerel clipping. 3625 test + 310 subtest; gerçek masaüstü Geometry/Gerber kaynak/rapor kaydet-aç geçti. Örnek özgün analitik çizim; gerçek Illustrator dosyası doğrulaması açık. [Doğrulama](../specs/019-svg-illustrator/validation.md). | 16 |
| 20 | `cad-source-detector` — **teslim edildi** | DXF/SVG açık üretici metadata tespiti, Unknown/çelişki durumu ve kalıcı kaynak kanıtı. Gerçek KiCad 10.0.6 çıktıları/lisans/hash izi; 3880 test + 310 subtest, gerçek masaüstünde dört tür/biçim roundtrip. Illustrator/Proteus vendor örnek kapsamı açık. Son commit Windows CI ve ana dala birleştirme tamamlandı. [Doğrulama](../specs/020-cad-source-detector/validation.md). | 17 |
| 21 | `geometry-to-excellon` — **yazılım tamamlandı** | Güncel tek/çok takımlı Geometry çemberleri, açık seçim, fiziksel çap gruplama ve kaynak değişikliği denetimli Excellon. 4069 test + 310 subtest; gerçek masaüstünde seçili delik export/proje roundtrip ve son commit Windows CI başarılı; ana dala birleştirildi. [Doğrulama](../specs/021-geometry-to-excellon/validation.md). | 9 |
| 22 | `merge-excellon` — **teslim edildi** | Güncel delik/slot verileri, tam eşdeğer tekrar raporu, analitik çakışma kontrolü ve yeniden kurulan tool map; kaynaklar korunur. 4269 test + 310 subtest; gerçek masaüstünde iki kaynak, slot export/proje roundtrip başarılı. PR23 birleştirildi; Windows CI geçti. [Doğrulama](../specs/022-merge-excellon/validation.md). | 21 |
| 23 | `pdf-vector-import` — **teslim edildi** | Evo PDF aracı ve izin verici alternatifler değerlendirildi; BSD-3-Clause pypdf okuyucusu, tek sayfa seçimi, fiziksel kırpma/flip, bağımsız subpath, dolgu/çizgi/clip ve karmaşıklık sınırları. 4503 test + 310 subtest; gerçek masaüstünde PDF → Geometry → DXF → proje roundtrip başarılı. PR24 birleştirildi; Windows CI geçti. [Doğrulama](../specs/023-pdf-vector-import/validation.md). | 17 |
| 24 | `manufacturing-import-wizard` — **teslim edildi** | Çoklu yerel Gerber/Excellon, bağımsız içerik/metadata/ad kanıtı, açık rol incelemesi ve sıralı nesne oluşturma. Kaynak ve şema1 rapor korunur; ilk hatada kalanlar bekler. 4789 test + 310 subtest; gerçek masaüstünde dört katman ve proje roundtrip başarılı. PR25 birleştirildi; Windows CI geçti. [Doğrulama](../specs/024-manufacturing-import-wizard/validation.md). | 17 |

### 0.6 — Probe ve iş kuyruğu

**Çıktı:** Eğri PCB'lerde auto-level ile izolasyon; birden fazla işin sırayla çalıştırılması.

| Sıra | Kısa ad | Kapsam | Bağımlılık |
| --- | --- | --- | --- |
| 25 | `probe-grid-heightmap` | ProbeMap, Fake ile grid probing, kaydetme/yükleme, görselleştirme | 13 |
| 26 | `autolevel-z-compensation` | Bilineer interpolasyon, G2/G3 segmentasyonu, placement transform ile entegrasyon | 25 |
| 27 | `job-queue` | Sıralama, iş başına durum, makine durumu kontrolü | 13 |

### 0.7 — Lazer olgunlaştırma

**Çıktı:** Malzeme ve makineye göre kayıtlı recipe'ler; büyük dolu alanlarda ısıyı dağıtan tarama.

| Sıra | Kısa ad | Kapsam | Bağımlılık |
| --- | --- | --- | --- |
| 28 | `laser-recipe-db` | Malzeme, makine, lens ve recipe veritabanı ile arayüzü; 0.2'deki JSON recipe'lerin yerini alır | 5 |
| 29 | `laser-island-tile` | Ada (island) ve dama tahtası (checkerboard) tarama | 6 |

### 0.8 — KiCad 10

**Çıktı:** KiCad'den tek tıklamayla MikroCAM'e üretim paketi.

| Sıra | Kısa ad | Kapsam | Bağımlılık |
| --- | --- | --- | --- |
| 30 | `kicad-cli-export` | `kicad-cli` veya `.kicad_jobset` ile DRC, Gerber ve Drill üretip şema sürümlü transfer paketi oluşturma; paketi MikroCAM'e aktarma | 24 |
| 31 | `kicad-ipc-plugin` | MikroCAM Bridge: IPC API ve kicad-python ile ayrı süreçte çalışan eklenti; toolbar action'ı 30'u çağırır | 30 |

### 1.0 — Ürünleştirme

**Çıktı:** GitHub Releases'tan indirilip kurulabilen MikroCAM.

| Sıra | Kısa ad | Kapsam | Bağımlılık |
| --- | --- | --- | --- |
| 32 | `packaging-windows` | Installer ve portable ZIP; GitHub Releases | 3 |
| 33 | `camera-fiducial-alignment` | 2 noktayla öteleme ve dönme, 3+ noktayla affine düzeltme; placement transform'u genişletir | 4 |

## Sona ertelenenler (K5)

Aşağıdakiler 1.0'dan sonra ve yalnızca gerçek bir ihtiyaç doğduğunda, her biri kendi spec'iyle ele
alınır.

| Kısa ad | Ne zaman |
| --- | --- |
| `galvo-backend` | Galvo kartı ve SDK/protokol netleşince; ARM akışı, interlock ve framing ile birlikte (anayasa VI) |
| `focus-z-check` | Galvo backend ile birlikte |
| `thermal-scheduler` | Interlace ve island ile test kuponlarından ölçüm verisi toplandıktan sonra |
| `feature-flags` | İlk yarım özellik ortaya çıktığında, tek dosyalık basit bir hâliyle |
| `workspace-ui-redesign` (Faz 3) | Mevcut Evo arayüzü bir iş akışını gerçekten engellediğinde |
| `project-format-mcam` | Evo proje formatı yetersiz kaldığında |

**Mach3 notu:** Mach3, GRBL gibi seri porttan satır satır sürülmez. Makineyi PC'de çalışan Mach3
yazılımının kendisi sürer ve G-code dosyasını kendisi yükler. Bu yüzden "Mach3 desteği", Mach3 ile
uyumlu G-code üretmek demektir; bu da preprocessor ile yapılır. 8.994'te `Toolchange_Probe_MACH3`
preprocessor'ı var; Evo'da da bulunduğu doğrulanmalıdır. Doğrudan kontrol spec'i gerekmez.
Gerekirse yalnızca preprocessor iyileştirilir.

**İhtiyaç doğmadıkça yapılmayanlar** (anayasa III):

- TCP, HTTP ve WebSocket transport'ları; grblHAL, FluidNC, Marlin, Smoothieware ve LinuxCNC
  controller'ları
- AI Assistant, 3D önizleme, gamepad ile jog, SD kart / FluidNC dosya sistemi, makrolar
- Raster PDF vektörleştirme, adaptive grid, bikübik interpolasyon
- Otomatik güncelleyici, crash raporu, macOS paketi, Docker

## Spec-kit akışı

```text
/speckit-specify   → specs/NNN-ad/spec.md   (ne ve neden; nasıl değil)
/speckit-clarify   → belirsizlikleri soru-cevapla kapatır (opsiyonel, plan'dan önce)
/speckit-plan      → plan.md, research.md, data-model.md + Constitution Check
/speckit-tasks     → tasks.md
/speckit-analyze   → spec/plan/tasks tutarlılık raporu (opsiyonel)
/speckit-implement → görevleri uygular
```

Hazırlıktan sonra, yeni repoda ilk feature için örnek:

```text
/speckit-specify MikroCAM'in tabanı olan FlatCAM Evo, Windows 11'de CPython 3.13 (64-bit) ile
kurulup çalışmalı. Geliştirici sanal ortamı kurup uygulamayı tek komutla açabilmeli; bağımlılıklar
sabit sürümlerle kurulmalı ve `pip check` temiz olmalı. 8.994 portunda kullanılan duman testi
(Gerber/Excellon yükleme, isolation ve G-code üretme, projeyi kaydetme ve yeniden açma) Evo'da da
geçmeli; Evo'nun mevcut testleri yeşil olmalı. Kapsam: yalnızca çalışan bir taban; yeni özellik ve
yeniden adlandırma yok.
```
