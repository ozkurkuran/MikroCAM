# Feature Specification: Evo Python 3.13 çalışma tabanı

**Feature Branch**: `001-evo-py313-baseline`

**Created**: 2026-09-26

**Status**: Implemented — doğrulama sonuçları [validation.md](validation.md) içinde

**Input**: User description: "MikroCAM'in tabanı olan FlatCAM Evo, Windows 11'de CPython 3.13 (64-bit) ile
kurulup çalışmalı. Geliştirici sanal ortamı kurup uygulamayı tek komutla açabilmeli; bağımlılıklar
sabit sürümlerle kurulmalı ve `pip check` temiz olmalı. 8.994 portunda kullanılan duman testi
(Gerber/Excellon yükleme, isolation ve G-code üretme, projeyi kaydetme ve yeniden açma) Evo'da da
geçmeli; Evo'nun mevcut testleri yeşil olmalı. Kapsam: yalnızca çalışan bir taban; yeni özellik ve
yeniden adlandırma yok."

**Taban kararı**: Kullanıcının son seçimiyle Bitbucket `Beta_1.0` dalındaki
`e046a2a33926003765f83d6402b96fe6c5c3bcf7` kullanılır. Değiştirilmemiş snapshot:
`upstream-evo-beta1-baseline`. İlk mekatrol fork'u `upstream-evo-baseline` tag'inde korunur.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Temiz ortamda kurulum ve başlatma (Priority: P1)

Geliştirici, repoyu yeni bir dizine klonlayıp yazılı Windows kurulum adımlarını izleyerek
diğer projelerden bağımsız bir çalışma ortamı oluşturabilmeli. Kurulumdan sonra tek bir
belgelenmiş komutla uygulamayı açabilmeli ve normal biçimde kapatabilmeli.

**Why this priority**: Tekrarlanabilir bir kurulum olmadan sonraki geliştirmeler için güvenilir
bir taban veya karşılaştırılabilir hata raporu oluşmaz.

**Independent Test**: Daha önce kurulmuş FlatCAM ortamı bulunmayan bir dizinde yalnızca
kurulum rehberi izlenir; bağımlılık kontrolü ve tek komutla açma/kapatma doğrulanır.

**Acceptance Scenarios**:

1. **Given** Windows 11 x64, standart CPython 3.13 x64 ve temiz bir klon, **When** geliştirici
   belgelenmiş sanal ortam ve kurulum adımlarını uygular, **Then** elle paket sürümü seçmeden
   kurulum tamamlanır ve `pip check` sıfır hatayla biter.
2. **Given** kurulmuş ortam, **When** geliştirici belgelenmiş tek başlatma komutunu çalıştırır,
   **Then** Evo ana penceresi kullanılabilir hâle gelir; yakalanmamış istisna oluşmaz ve normal
   kapatma sonrasında uygulamaya ait worker süreçleri/thread'leri açık kalmaz.
3. **Given** aynı repo commit'inden iki temiz ortam, **When** kurulum aynı rehberle tekrarlanır,
   **Then** sabitlenmiş bağımlılık sürümleri aynı olur ve iki ortamda da kontrol temiz çıkar.

---

### User Story 2 - Temel PCB CAM akışını tamamlamak (Priority: P2)

PCB hazırlayan kullanıcı, bir Gerber ve bir Excellon örneğini açıp izolasyon geometrisi ve
G-code oluşturabilmeli. Projeyi kaydedip yeniden açtığında ürettiği çalışma korunmalı.

**Why this priority**: Uygulamanın açılması tek başına yeterli değildir; kullanılabilir taban,
MikroCAM'in üzerine kurulacağı temel CAM akışını da çalıştırmalıdır.

**Independent Test**: Sabit referans dosyalarıyla bu uçtan uca akış çalıştırılır; oluşturulan
nesneler, çıktı ve yeniden açılan proje gözlenir. Fiziksel makine gerekmez.

**Acceptance Scenarios**:

1. **Given** altın referans portunun duman testinde kullanılan Gerber ve Excellon örnekleri,
   **When** kullanıcı dosyaları Evo'da yükler, **Then** iki nesne beklenen türde, boş olmayan
   geometriyle oluşur ve kanvasta görüntülenebilir.
2. **Given** yüklenmiş Gerber, **When** aynı referans iş parametreleriyle isolation ve CNC işi
   üretilir, **Then** boş olmayan izolasyon geometrisi, G-code metni ve ayrıştırılmış takım
   yolu oluşur; işlem istisnasız tamamlanır.
3. **Given** Gerber, Excellon, izolasyon geometrisi ve CNC işi bulunan proje, **When** proje
   kaydedilip yeniden açılır, **Then** nesne adları ve türleri korunur, G-code metni değişmez,
   nesneler yeniden görüntülenebilir ve kullanıcıya ait diğer projeler/ayarlar değiştirilmez.

---

### User Story 3 - Tabanın regresyon durumunu doğrulamak (Priority: P3)

Bakım yapan geliştirici, Evo'nun mevcut testleri ile 8.994 portundan uyarlanan uyumluluk ve
duman kontrollerini tekrarlayarak bu tabanın hangi doğrulamalardan geçtiğini görebilmeli.

**Why this priority**: Sonraki dilimlerdeki değişiklikleri değerlendirmek için testlerin
kapsamı ve sonuçları görünür, tekrarlanabilir olmalıdır.

**Independent Test**: Belgelenmiş doğrulama komutları hedef ortamda çalıştırılır ve kaynak
test envanteriyle karşılaştırılan bir sonuç özeti üretilir.

**Acceptance Scenarios**:

1. **Given** sabitlenmiş geliştirme ortamı ve seçilen Evo snapshot'ının testleri, **When**
   mevcut test paketi çalıştırılır, **Then** hedef platform için uygulanabilir tüm testler
   geçer; başarısız testler silinerek, devre dışı bırakılarak veya koşulsuz atlanarak gizlenmez.
2. **Given** `legacy8994` referansındaki `tests/test_runtime_compatibility.py` ve
   `tests/smoke_app.py` davranışları, **When** Evo'ya uyarlanmış kontroller çalıştırılır,
   **Then** korudukları davranışlar hedef ortamda doğrulanır ve Gerber'den yeniden açılmış
   projeye kadar duman akışının her aşaması başarılı olarak raporlanır.
3. **Given** tekrar çalıştırılacak doğrulamalar, **When** testler yürütülür, **Then** fiziksel
   CNC/lazer veya canlı güncelleme servisi gerekmez; kullanıcı ayarları ve verileri korunur.
   Grafik bağlamı gerektiren duman testinin ortam koşulları ayrıca belirtilir.

### Edge Cases

- Yanlış Python minor sürümü, 32-bit veya free-threaded yorumlayıcı: desteklenen yorumlayıcı
  koşulları kurulum rehberinde açıkça görünür; bu ortamlar başarı kanıtı sayılmaz.
- Eksik Tcl/Tk, grafik sürücüsü veya OpenGL bağlamı: gereken önkoşul ve başarısız aşama
  belirtilir; GUI duman testi çalışmadığında geçti olarak raporlanmaz.
- Paket kaynağına erişilememesi veya seçilen platform için dağıtım bulunmaması: kurulum
  başarısızlığı görünür kalır; sessizce farklı bir sürüme geçilmez.
- Önceden kurulu global paketler veya kullanıcı FlatCAM ayarları: temiz ortam doğrulaması
  bunlara dayanmaz; testler var olan kullanıcı ayarlarını ve projelerini ezmez.
- Geçersiz giriş dosyası veya yazılamayan proje yolu: başarısız işlem görünür hata üretir;
  eksik çıktı başarılı round-trip olarak kabul edilmez.
- Platforma özgü upstream testleri: varsa uygulanamazlık gerekçesi ve etkilenen testler
  sonuç kaydında listelenir; yeni hataları gizlemek için skip/xfail eklenmez.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Taban, seçilen Evo `Beta_1.0` snapshot'ından ilerlemeli ve Windows 11 üzerinde
  standart CPython 3.13.x x64 ile kurulup açılmalıdır. Denenen patch sürümü `.python-version`
  dosyasında tek kaynak olarak kaydedilmelidir. Kabul: Story 1 / 1–2.
- **FR-002**: Kurulum rehberi önkoşulları, temiz sanal ortam oluşturmayı, bağımlılık kurulumunu
  ve kurulum sonrası tek komutla başlatmayı içermelidir. Kabul: Story 1 / 1–2.
- **FR-003**: Runtime ve geliştirme bağımlılıkları `requirements*.txt` içinde `==` ile
  sabitlenmeli; iki temiz kurulum aynı sabitlenmiş sürümleri kullanmalıdır. Kabul: Story 1 / 3.
- **FR-004**: Hedef ortamdaki `pip check` sıfır çıkış koduyla, bozuk bağımlılık bildirmeden
  tamamlanmalıdır. Kabul: Story 1 / 1, 3.
- **FR-005**: Başlatma ve normal kapatma tamamlanmalı; yakalanmamış istisna veya açık kalan
  uygulama worker'ı bulunmamalıdır. Kabul: Story 1 / 2.
- **FR-006**: Gerber ve Excellon yükleme, isolation ve G-code üretme akışı sabit referans
  girdileriyle boş olmayan sonuçlar üretmelidir. Kabul: Story 2 / 1–2.
- **FR-007**: Kaydedilen ve yeniden açılan proje dört referans nesnesinin adını/türünü ve
  üretilmiş G-code'u korumalı, yeniden görüntülenebilmelidir. Kabul: Story 2 / 3.
- **FR-008**: 8.994 portunun uyumluluk ve duman testleri Evo'ya uyarlanmalı; korunan her
  davranışın Evo karşılığı doğrulama kaydında tanımlanmalıdır. Kabul: Story 3 / 2.
- **FR-009**: Seçilen Evo snapshot'ının mevcut testleri korunmalı ve hedef platformda
  uygulanabilir olanların tamamı geçmelidir; updater testleri de bu kapsama dahildir.
  Kabul: Story 3 / 1.
- **FR-010**: Test çalıştırma rehberi komutları, grafik gereksinimlerini ve sonuçların nasıl
  okunacağını açıklamalıdır. Doğrulama kaydı ortamı, geçen/kalan/atlanan testleri ve varsa
  uyarıları içermelidir. Kabul: Story 3 / 1–3.
- **FR-011**: Doğrulamalar kullanıcı verisini/ayarlarını değiştirmemeli, fiziksel donanım
  veya canlı updater servisi gerektirmemelidir. Kabul: Story 2 / 3 ve Story 3 / 3.
- **FR-012**: Dilim yalnızca kurulum, uyumluluk düzeltmeleri ve tabanın doğrulanmasını
  kapsamalıdır. Ürün adı/arayüz kimliği değişikliği, yeni CAM/makine/lazer özelliği,
  yeni proje formatı, guardrail altyapısı ve MikroCAM updater geliştirmesi kapsam dışıdır.
  Kabul: değişiklik envanterinin bu sınırlarla incelenmesi.

### Key Entities

- **Çalışma tabanı**: Seçilen upstream commit'i, hedef ortamı ve sabit bağımlılık sürümleriyle
  tanımlanan tekrar üretilebilir uygulama snapshot'ı.
- **Referans CAM işi**: Kaynağı sabit Gerber/Excellon dosyaları, iş parametreleri ve beklenen
  nesneleri içeren doğrulama örneği; mevcut Evo proje formatını kullanır.
- **Doğrulama kaydı**: Ortam bilgisi, kurulum ve test sonuçları, uyarlanan test kapsamı ve
  açıklanmış sınırlamalar; yeni bir uygulama içi veri modeli veya format gerektirmez.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: İki ayrı temiz kurulum, rehber dışında elle düzeltme gerektirmeden tamamlanır;
  aynı sabitlenmiş bağımlılık sürümleriyle sıfır bağımlılık uyuşmazlığı raporlanır.
- **SC-002**: Kurulum sonrası tek komut uygulamayı açar; art arda üç açma/kapatma denemesi
  yakalanmamış hata ve geride kalan uygulama worker'ı olmadan tamamlanır.
- **SC-003**: Referans CAM akışının altı aşaması (Gerber yükleme, Excellon yükleme, isolation,
  G-code üretme, kaydetme, yeniden açma) aynı çalıştırmada başarılıdır; yeniden açılan
  projede beklenen dört nesne ve aynı G-code bulunur.
- **SC-004**: Hedef platform için uygulanabilir mevcut ve uyarlanmış kontrollerin tamamı
  geçer; sıfır başarısızlık vardır ve varsa her atlamanın gerekçesi sonuç kaydındadır.
- **SC-005**: Değişiklik envanterindeki her değişiklik kurulum, uyumluluk, doğrulama veya
  bunların dokümantasyonuyla açıklanır; yeni kullanıcı özelliği ve yeniden adlandırma sayısı sıfırdır.

## Assumptions

- Hazırlıkta yayımlanan repo/tag'ler ve remote'lar [hazırlık kaydında](../../docs/PREPARATION.md)
  belirtilmiştir. İlk mekatrol tabanı ile seçilen Beta_1.0 snapshot'ı farklı referanslardır.
- Kurulum sırasında paket indirmek için internet erişimi vardır. Doğrulama çalıştırması
  fiziksel donanıma veya canlı güncelleme servisine bağlanmaz.
- GUI duman testi, uygun grafik sürücüsü ve masaüstü/OpenGL bağlamıyla çalıştırılır.
  Ekransız CI altyapısı `foundation-guardrails` diliminde ele alınır.
- Altın referansın `baseline-8.994-py313` tag'indeki örnekler ve test davranışları uyarlama
  kaynağıdır. İki farklı Evo/8.994 sürümünün G-code metninin birebir eşitliği bu dilimde
  aranmaz; geniş veri seti ve sürümler arası toleranslı karşılaştırma `reference-dataset` kapsamıdır.
- Beta_1.0 ile gelen özellikler korunur; uyumluluk için gerekli düzeltmeler yapılabilir.
  MikroCAM'e özgü dağıtım/otomatik güncelleme davranışı bu dilimde geliştirilmez.
- Orijinal araştırma belgesi henüz sağlanmamıştır; bu spec'in kapsamı kullanıcının hazır
  komutu, son taban seçimi, roadmap ve anayasa v1.1.0 ile yeterince tanımlanmıştır.
