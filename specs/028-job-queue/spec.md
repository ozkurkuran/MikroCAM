# Feature Specification: İş kuyruğu

**Feature Branch**: `028-job-queue`

**Created**: 2026-10-02

**Status**: Draft — one transition-policy clarification pending

**Input**: User objective "diğer fazları tamamla!"; MACHINE_CONTROL_ROADMAP C2 and
ROADMAP slice 27: sıralama, iş başına durum, makine durumu kontrolü.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sırayı hazırlama (Priority: P1)

Operatör doğrulanmış CNC işlerini sıraya ekler, çalıştırmadan önce sıralar ve her işin
adını ve durumunu görür. Sıraya eklemek makine hareketi başlatmaz.

**Why this priority**: Birden fazla hazır işi açık ve denetlenebilir sırada tutar.

**Independent Test**: Bağlantısız oturumda üç hazır işi ekle, ikinciyi ilk sıraya taşı,
birini çıkar; sıra ve iş kimlikleri korunur ve makineye komut gönderilmez.

**Acceptance Scenarios**:
1. **Given** üç doğrulanmış iş, **When** sıraya eklenip sıralanır, **Then** görünür sıra
   istenen sıradır ve bütün işler Bekliyor durumundadır.
2. **Given** aynı kaynak iki kez eklendi, **When** bir kayıt çıkarılır, **Then** yalnızca
   o kayıt çıkarılır; iki kayıt farklı kimlik taşır.
3. **Given** aktif iş var, **When** sıra düzenleme veya aktif kaydı çıkarma istenir,
   **Then** işlem reddedilir ve aktif iş değişmez.

### User Story 2 - Makine durumuyla başlatma ve iş geçişi (Priority: P1)

Operatör kuyruğu bilinçli başlatır. Her iş kendi hazır kaynak bilgisi, ilerlemesi ve
sonucuyla izlenir. Sonraki işe geçiş yalnızca öncekinin doğrulanmış tamamlanması ve
makinenin yeniden hazır olmasıyla mümkündür.

**Why this priority**: Kuyruk mevcut çalıştırma ön kontrollerini atlamamalıdır.

**Independent Test**: İki kısa işte ilk işin son kaynak onayını ver; ikinci işin
başlamadığını göster. Son çıkış kapatma onayı ve taze uygun durumdan sonra aşağıdaki
seçilen geçiş politikasını doğrula.

**Acceptance Scenarios**:
1. **Given** bağlantı kopuk, durum eski veya Idle dışında, **When** başlatma istenir,
   **Then** hiçbir kaynak satırı gönderilmez ve reddin nedeni görünür.
2. **Given** bir işin son kaynak satırı onaylandı fakat son çıkış-kapalı ve Idle kanıtı
   yok, **When** sonraki iş değerlendirilir, **Then** ilk iş Tamamlandı sayılmaz ve
   ikinci iş başlamaz.
3. **Given** ilk iş doğrulanmış Tamamlandı ve makine uygun, **When** geçiş yapılır,
   **Then** FR-006'da seçilecek politika uygulanır; aynı anda yalnızca bir iş aktiftir.
4. **Given** sıradaki işin hazırlık/koordinat/mekanik koşulları artık uygun değil,
   **When** sıra ona gelir, **Then** kuyruk durur, nedeni gösterir ve iş gönderilmez.

### User Story 3 - Hata, hold ve operatör durdurması (Priority: P2)

Operatör hangi işin başarısız olduğunu ve kalan sırayı görür. Hata, kesinti veya Stop
sonrası makine ve kuyruk kendiliğinden yeniden başlamaz.

**Why this priority**: Bir işteki hata sonraki işe taşınmamalıdır.

**Independent Test**: İki işlik sıranın ilk işinde alarm/kopma/timeout üret; ikinci
kaynağın hiç gönderilmediğini, sonuçların korunduğunu ve geç onayın yeniden başlatmadığını göster.

**Acceptance Scenarios**:
1. **Given** ilk iş aktif, **When** error/alarm/reset/kopma veya zaman aşımı oluşur,
   **Then** aktif işin başarısız sonucu görünür; bekleyen işler başlamaz.
2. **Given** aktif iş hold durumunda, **When** bekleyen işler değerlendirilir,
   **Then** sıradaki iş başlayamaz; Resume yalnızca mevcut işi sürdürür.
3. **Given** aktif kuyruk, **When** Stop veya bağlantıyı kesme istenir, **Then** mevcut
   durdurma yolu çalışır; kalan işler bekler, yeniden başlama ayrı bilinçli işlem ister.
4. **Given** son iş tamamlandı, **When** kuyruk sonucu gösterilir, **Then** her işin
   sırası, kaynak kimliği ve terminal sonucu korunur; ek hareket gönderilmez.

### Edge Cases

- Boş kuyruk; oturum sınırını aşan ekleme; bilinmeyen/silinmiş kayıt kimliği.
- Aynı işin birden çok kaydı; iş kaynağının sonradan değiştirilmesi.
- Son kaynak ACK'i ile doğrulanmış fiziksel tamamlanma arasındaki süre.
- Door/Check/Sleep/Alarm, eski durum veya çalışma çerçevesinin değişmesi.
- ACK sınırının hemen altı/üstü, parçalı yanıt, geç ve yinelenen ACK.
- Hold sırasında Stop/kapatma, peş peşe reconnect, ilk/orta/son işte hata.
- Ayrı tek-iş çalıştırması, jog, probe veya konsol sahipliği varken kuyruk başlatma.
- Kuyrukta hata sonrası açık yeniden başlatma; belirsiz durdurma sonucu.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Operatör mevcut hazır CNC işlerini oturumluk bir kuyruğa ekleyebilmeli;
  her kayıt bağımsız kimlik, sıra, kaynak adı ve kaynak özeti taşımalıdır.
- **FR-002**: Aktif iş yokken bekleyen kayıtlar sıralanabilmeli/çıkarılabilmeli ve kuyruk
  temizlenebilmelidir. Aktif kuyruk düzenlemesi reddedilmelidir.
- **FR-003**: Kuyruk ekleme, sıralama ve gösterme makineyi bağlamamalı veya hareket
  başlatmamalıdır. İlk iş yalnızca operatörün açık başlatma işlemiyle başlayabilir.
- **FR-004**: Her iş başlamadan önce mevcut bağlantı, taze Idle, koordinat/iş hazırlığı,
  mekanik doğrulama ve tek iletişim sahibi ön koşulları yeniden uygulanmalıdır.
- **FR-005**: Son kaynak ACK'i tamamlanma sayılmamalıdır; işin mevcut çıkış-kapalı ve
  son durum kanıtları alınmadan sıradaki iş başlayamaz.
- **FR-006**: Doğrulanmış tamamlanmadan sonraki iş geçişi
  [NEEDS CLARIFICATION: Kuyruk bir kez açıkça onaylandıktan sonra sonraki uygun iş otomatik mi başlasın, yoksa her iş için ayrı Start/Next ve mekanik onay mı gereksin?]
- **FR-007**: İş başına Bekliyor, Hazırlanıyor, Çalışıyor, Hold, Tamamlanıyor,
  Tamamlandı, İptal veya Hata durumu ve mevcut ilerleme/neden görünmelidir.
- **FR-008**: Hata, alarm, reset, kopma, zaman aşımı ve Stop sonraki işe geçişi
  engellemelidir. Yeniden bağlanma veya geç ACK kuyruk/iş yeniden başlatmamalıdır.
- **FR-009**: Pause/Resume yalnızca aktif işi yönetmeli; Stop ve kapatma mevcut
  durdurma yoluna gitmelidir. Belirsiz durdurma sonucu yeni başlatmayı engellemelidir.
- **FR-010**: İşin hazırlanmış kaynak/çerçeve bilgisi kayıt boyunca değişmemeli;
  tekrar çalıştırma yeni açık ekleme/başlatma gerektirmelidir.
- **FR-011**: Mevcut tek-iş, probe, autolevel ve konsol işlemleri korunmalı; başka
  aktif sahip varken kuyruk hiçbir komut yazmamalıdır.
- **FR-012**: Operatör kaynak adını, sırayı, terminal sonucu ve başarısızlık nedenini
  görebilmeli; iş geçişleri mevcut tanı kayıtlarında kaynak kimliğiyle izlenebilmelidir.

### Key Entities

- **Kuyruk kaydı**: Bağımsız kimlik, sıra, değişmez hazır iş, kaynak adı/özeti ve sonuç.
- **Kuyruk gözlemi**: Sıralı kayıtlar, tek aktif kayıt, ilerleme ve başlatma/stop uygunluğu.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Üç iş eklenip sıralandığında görünen ve yürütülen sıra yüzde 100 aynı olur.
- **SC-002**: Test edilen bütün başlangıç ve iş geçişlerinde en fazla bir iş aktif olur;
  uygunsuz makine durumlarında sıfır kaynak satırı gönderilir.
- **SC-003**: Her hata matrisi senaryosunda bekleyen işlerden sıfır satır gönderilir;
  yeniden bağlanma/geç yanıt sıfır otomatik yeniden başlatma üretir.
- **SC-004**: Tamamlanan üç işlik kuyrukta üç ayrı kaynak kimliği ve terminal sonuç
  görünür; kaynak son onayından önce veya eksik son kanıtla sıfır erken geçiş olur.
- **SC-005**: Mevcut tek-iş/probe/konsol iş akışlarının testleri ve masaüstü smoke'u geçer.

## Assumptions

- İlk sürüm oturumluk ve en fazla 32 kayıtlı CNC işini kapsar; yeniden açma sonrası
  kalıcılık, otomatik kurtarma ve lazer/galvo kuyruğu kapsam dışıdır.
- Hazır işler mevcut doğrulama ve mekanik çalıştırma kurallarından gelir. Kuyruk bu
  kuralları gevşetmez; yeni transport veya kontrolcü türü eklenmez.
- C1 matrisinin tamamlanması ve ACK deadline düzeltmeleri uygulama başlangıç koşuludur.
  B ve C1 ayrı PR'lardır; bu taslak B üzerine kurulmuştur ve C1 entegrasyonu planlanacaktır.
- FR-006 seçilmeden plan/tasks/uygulama tamamlanmış sayılmaz; iki davranış birden
  varsayılan seçenek olarak uygulanmaz.

## Tehlike analizi

| Tehlike | Önlem | Kabul kanıtı |
| --- | --- | --- |
| Birden fazla iş/sahip aynı anda hareket gönderir | Tek aktif iş ve mevcut sahiplik denetimi | Çakışan sahipte sıfır yazma |
| Önceki iş yalnızca ACK verdiği için sonraki iş başlar | Mevcut son çıkış-kapalı ve taze durum kanıtı | Eksik kanıtta sıfır geçiş |
| Yanlış çalışma çerçevesi veya değiştirilmiş kaynak | Kayıt değişmezliği ve her işte mevcut kontroller | Değişiklikte açık ret |
| Hata/kopma/hold sonrası beklenmeyen yeniden hareket | Kuyruk ilerlemesini kes, otomatik replay/restart yapma | Hata matrisi ve geç ACK testleri |
| Operatör FR-006 politikasını yanlış anlar | Spec'te açık seçim ve çalıştırma öncesi açıklama | Seçilen politikanın masaüstü kabul senaryosu |

Yazılım kanıtı fiziksel durdurma veya saha doğrulaması yerine geçmez; H protokolü uygulanır.
