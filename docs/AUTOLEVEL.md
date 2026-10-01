# Auto-level Z telafisi

026, 025 ile kaydedilmiş **tamamlanmış** yükseklik haritasını kullanarak mekanik G-code için
ayrı, ön kontrolden geçirilmiş bir çıktı üretir. İlk doğrulama FakeGRBL ile yapılmıştır;
fiziksel CNC, prob doğruluğu, kart sabitlemesi ve takım/kelepçe açıklığı doğrulanmış değildir.

## Kullanım
1. **G-code preflight** panelinde dosyayı veya seçili CNC işini yükleyin. Başlangıç, XY placement,
   Z ofseti, makine sınırları, safe Z ve üç eksen rapid hızını açıkça girip analiz edin.
2. Başarılı ön kontrolden **Auto-level** açın; 025'in kaydettiği tam haritayı yükleyin.
3. **Reference surface work Z**: kaynak kesme derinliğinin dayandığı yüzeyin G54 iş Z yüksekliği.
   Her kesme noktasına `harita yüksekliği - referans yüksekliği` eklenir. Örneğin kaynak Z=-0,1,
   referans=0 ve ölçülen yüzey=0,04 ise çıktı iş Z=-0,06 olur (aynı Z ofsetinde).
4. Maksimum XY segmentini (.01..10 mm), yay kiriş hata sınırını ve üretilen doğrusal parçalar
   boyunca yüzey hata sınırını (.0001..0.1 mm) girin. Değerler kendiliğinden doldurulmaz.
5. **Prepare compensated job** ile ayrı çıktıyı hazırlayın. Kaynak/harita kimliğini, measured veya
   simulated kaynağını, sınırları ve ilk 200 satırlık önizlemeyi inceleyin. Kart placement'ı ve
   haritanın G54 çerçevesini doğrulama kutusunu işaretleyin.
6. Ayrı G-code kaydedin veya **Load reviewed job into Machine** ile mevcut Machine iş akışına
   aktarın. Hazırlama ve aktarım makineyi başlatmaz; mevcut mekanik onay ve **Start job** gerekir.

## Koordinatlar ve sınırlamalar
Kaynak XY önce mevcut ortak Placement ile makine koordinatına taşınır; haritanın kaydedilmiş
G54 ofseti çıkarılarak iş-mm haritasına sorgulanır. Çıktı bu haritanın G54 çerçevesinde mutlak mm
G0/G1 kodudur; dönme ve ayna yalnızca bir kez uygulanır. Harita ve kaynak aynı sabit kart/fixture
kurulumunu anlatmalıdır. Yazılım fiziksel kurulumun gerçekten eşleştiğini ölçemez.

Yalnızca G1/G2/G3 feed hareketleri telafi edilir. G0 rapid'in kaynak safe-Z yolu korunur;
telafili yüksekliklerden sonra rapid güvensiz hâle gelirse türetilmiş ön kontrol işi reddeder.
Rapid'den sonra XY kesmenin başlangıcı telafili konuma uymuyorsa önce aynı XY'de dikey G1 dalış
kullanılmalıdır; yazılım gizli bir Z geçişi eklemez.

G2/G3 yayları ve helisler yön/sweep/Z değişimi korunarak doğrusal kirişlere ayrılır. Kiriş hata
sınırı yay XY yaklaşımını, yüzey hata sınırı **üretilen doğrusal kiriş boyunca** bilineer yüzey
izlemesini sınırlar. Gerçek yay boyunca ayrıca bir yüzey hata iddiası yoktur. Eşit olmayan yay
başlangıç/bitiş yarıçapları reddedilir. Tüm yay içi sınırlar analitik olarak harita içinde olmalıdır.

Harita dışına ekstrapolasyon, yarım haritanın doldurulması, bicubic/adaptive grid, G55-G59,
G92/offset değişiklikleri, G18/G19, canned cycle, tool change, M0/M1 ve M7 bu sürümde yoktur.
Bilineer hücre kesişimleri ve yüzey eğriliği için parçalar artırılır; kaynak/çıktı en fazla 16 MiB
ve 250000 fiziksel satırdır. Serileştirme ve GRBL float32 hassasiyeti istenen hata bütçesini
sağlamıyorsa işlem reddedilir. Nominal süre fiziksel çalışma süresi tahmini değildir.

Kaynak, harita veya ayar değişirse sonuç ve dosya/aktarım onayı geçersizleşir. Kaydetme ayrı
çıktıda atomiktir; yüklenen G-code/harita yolu ve aynı dosyanın hardlink'i korunur. Girdi dosyası
sonradan düzenlenirse yüklenen snapshot değişmez; yeni içeriği kullanmak için tekrar yükleyin.
Dosya pencereleri diğer makine kontrollerini engellemez. Fiziksel E-stop ve güvenli açıklık
prosedürleri hâlâ operatörün sorumluluğundadır.


## Legacy Levelling ve GRBL

Levelling aracında GRBL seçilince eski Connect/Control/Sender sekmeleri kapalıdır;
**Open Machine panel** düğmesi mevcut Machine panelini açar. Port arama veya bağlantı
kendiliğinden yapılmaz; eski araç ayrı bir COM sahibi olamaz. Probe grid 025, auto-level 026
ve iş gönderimi 013 kendi inceleme/başlatma/durdurma kurallarıyla kullanılır. Auto-level
hazırlığı G-code preflight panelinden açılır. Yönlendirme eski haritayı veya işi otomatik
aktarmaz ve makineye bağlanmaz. MACH3/MACH4/LinuxCNC için mevcut probe G-code üretimi ve
yükseklik dosyası içe aktarma korunur. Fiziksel cihaz doğrulaması ayrıca yapılmalıdır.
