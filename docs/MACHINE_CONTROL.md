# Machine paneli: GRBL bağlantısı, jog ve G54 iş sıfırı

Bu panel GRBL 1.1 denetleyicisine seri port üzerinden bağlanır; durum ve konum bilgilerini
okur. Açık bir kullanıcı eylemiyle tek eksende sınırlı jog, G54 seçimi ve seçilen eksenlerde
kalıcı G54 iş sıfırı ayarı yapılabilir. Bağlanmak veya paneli açmak hareket başlatmaz,
G54 seçmez ve iş sıfırını değiştirmez. Homing, unlock, resume, iş gönderimi, çıkış açma
veya ham komut alanı yoktur. Abort bir durdurma isteğidir; genel bir reset ayarı değildir.

## Bağlanma

1. **Plugins → Machine** menüsünden paneli açın. Menü/düğme adları uygulama diline göre
   çevrilir; çevirisi bulunmayan yeni metinler İngilizce kalabilir. Paneli açmak veya
   tekrar öne getirmek bağlantı başlatmaz.
2. **Refresh ports** ile listeyi yenileyin. Yalnızca işletim sisteminin port metaverisi
   okunur; portlar açılıp denenmez. Port yoksa veya liste okunamıyorsa Connect kullanılamaz.
3. Bilinen GRBL 1.1 cihazınızın fiziksel portunu seçin; örneğin Windows'ta `COM7`.
   Ağ/URL portları desteklenmez. Seçimin tek başına bağlantı etkisi yoktur.
4. **Connect** düğmesine basın. Hız sabit **115200 baud**; seri okuma zaman aşımı 50 ms,
   yazma zaman aşımı 500 ms'dir. Portun açılması ile doğrulanmış durum/koordinat alınması
   farklı aşamalardır. Connect etkin oturum boyunca devre dışıdır; Disconnect kullanılabilir.
5. **Connection**, **Machine state** ve tanı alanlarını birlikte değerlendirin.
   Connected görmek makinenin Idle veya harekete hazır olduğunu göstermez.

**Port açılması bazı USB-seri adaptörlerde veya denetleyicilerde donanımsal reset
oluşturabilir.** MikroCAM bağlantı sırasında reset/wake komutu göndermez ve bağlantı dizisi olarak DTR/RTS
değiştirmez; sürücü veya kartın port açmaya tepkisi yine de reset olabilir.

## Firmware tanıma (042)

Port açıldıktan sonra MikroCAM ilk ayar okumasından (`$$`) hemen önce tek bir salt okunur `$I`
sorgusu gönderir; hareket, ayar yazma, wake veya reset göndermez. **Firmware** satırı aileyi,
sürümü, build tarihini, bildirilen RX tamponunu, karakter sayımı bütçesini ve hareketin açık
olup olmadığını gerekçesiyle gösterir; ayrıntılar (belgelenmiş gerçek zamanlı komutlar, ek
durumlar, durum alanları, ham `$I` satırları) ipucunda, ham bayt alışverişi wire log'dadır.

| Gösterim | Anlamı | Hareket |
| --- | --- | --- |
| `GRBL 1.1x` | gnea GRBL 1.1 biçimi (`[VER:1.1x.YYYYMMDD:]`, üç alanlı OPT) | Açık (mevcut davranış) |
| `grblHAL 1.1f` | `GrblHAL` karşılaması veya `[FIRMWARE:grblHAL]` | Kapalı; spec 043 (D2) doğrulayana kadar |
| `FluidNC x.y.z` | `[VER:x.y FluidNC vx.y.z…:]`; karşılama “Grbl” ile başlasa da | Kapalı; spec 044 (D3) doğrulayana kadar |
| `Unknown` | Kanıt yok, bozuk, çelişkili, `error:` veya 3 s içinde cevap yok | Kapalı |

Hareket kapalıyken jog, G54 seçimi/sıfırı, iş, kuyruk ve probe başlatılamaz. Cancel jog, Stop,
Abort ve Disconnect her zaman kullanılabilir. Salt okunur konsol sorguları tanı için açıktır.
Karşılama satırı tek başına kimlik sayılmaz: FluidNC karşılaması ayarla değiştirilebilir ve
grblHAL uyumluluk modunda `Grbl 1.1f` der. Oturum ortasında aynı firmware'in karşılaması gelirse
yalnız `$$` yeniden okunur; farklı/doğrulanamayan bir karşılama `$I` ile yeniden tanıma başlatır.
Otomatik tekrar veya yeniden bağlanma yoktur; bilinmeyen sonuçta Disconnect/Connect yapın.
Gerçek grblHAL/FluidNC kartlarında tanıma henüz doğrulanmadı
([saha protokolü H042](hardware/GRBL_VALIDATION.md)).

## Konumları okuma

**Machine XYZ (mm)** makine, **Work XYZ (mm)** çalışma koordinat sistemindeki X/Y/Z
konumudur. İkisi de mm cinsindedir; G54 sıfır düğmeleri yalnızca açık kullanıcı isteğiyle
çalışma ofsetini değiştirir, fiziksel makine konumunu taşımaz.

Rapor birimi, `$$` cevabındaki geçerli `$13` değeri ve tamamlanmış ayar cevabı (`ok`)
ile doğrulanır: `$13=0` mm, `$13=1` inch raporudur. Inch konumları mm'ye çevrilir.
Bu doğrulama tamamlanmadan sayısal mm konumu sunulmaz; yalnızca `$13` satırını görmek
yeterli değildir. Birimler doğrulandıktan sonra taze durum raporu beklenir.

Denetleyici yalnızca bir koordinat sistemini bildiriyorsa, diğerinin hesaplanması için
geçerli çalışma ofseti gerekir. Bu kanıt yoksa yalnızca doğrudan bildirilen sistem
görünür. **Unavailable** (kullanılamıyor) sıfır anlamına gelmez. Eksik veya geçersiz
koordinat uydurulmaz. Tanınmayan durum ham metniyle görünür; Unknown, Idle sayılmaz.

Geçerli durum raporu iki saniye gelmezse bilgi **Stale** (eski) olur ve eski konum/ofset
kullanılmaz. Durum sorguları devam edebilir; yeni geçerli rapor konumu yeniden sağlar.
Başlangıç/reset bildirimi önceki birim ve konum kanıtını temizler, yeni ayar okuması
başlatır; tamamlanmış birim doğrulaması ve taze durum gelene kadar koordinatlar kullanılamaz.

## Tek adımlı jog

Önce takımın hareket yolu, bağlama elemanları ve makine sınırlarını kontrol edin. **Step (mm)**
0.1, 1 veya 10 mm; **Feed (mm/min)** 100, 300 veya 600 mm/dak seçeneklerini sunar.
Başlangıç seçimi 0.1 mm / 100 mm/dak'tır. **X−/X+**, **Y−/Y+**, **Z−/Z+** düğmelerinden
birine basmak yalnızca seçilen eksende bir adım ister. Inch raporu veya mevcut parser modu
bu mm isteğini değiştirmez. Basılı tutarak tekrar veya hareket kuyruğu yoktur; işlem sürerken
yeni jog ve sıfır istekleri kilitlenir. Bu sınırlar güvenli hareket alanını garanti etmez.

Manuel işlem için bağlantı açık, birimler/konum doğrulanmış, durum taze **Idle** ve başka
işlem bulunmuyor olmalıdır. Denetleyicinin `$N0` / `$N1` başlangıç blokları da okunup ikisinin
boş olduğu doğrulanır. Dolu veya belirsiz blok varsa işlem reddedilir; uygulama bunları silmez.
Seri port açılışındaki donanımsal reset, bu kontrol yapılmadan önce kayıtlı blokları çalıştırabilir.

Jog öncesinde spindle/lazer ve coolant kapatma komutu gönderilir; kabul ve modal cevapla
kapatma doğrulanır, ardından taze Idle beklenir. Bu, fiziksel güç ölçümü değildir.
Jog cevabındaki `ok` yalnızca kabul demektir: hedef konumu doğrulayan daha sonraki taze
Idle raporu alınmadan **Complete** gösterilmez. Tanıyı ve işlem durumunu birlikte okuyun.

## G54 seçimi ve kalıcı iş sıfırı

**Use G54**, açıkça G54 sistemini seçer ve seçimi doğrular; hiçbir ekseni sıfırlamaz.
**Set G54 zero XY**, **Z** veya **XYZ**, mevcut noktada yalnızca adlandırılan çalışma
eksenlerini sıfırlar. Bu işlem denetleyicide **kalıcı G54 ofsetini değiştirir**; seçilmeyen
eksenler ve G55–G59 sistemleri korunur. Takım uzunluğu ve geçici G92 ofseti hesaba katılır.
İşin referans noktasını doğrulamadan bu düğmelere basmayın.

Sıfır için etkin G54, tam ofset okuması ve taze konum gerekir. Başarı, yazma kabulünden sonra
ofsetlerin yeniden okunması ve yeni çalışma konumunun doğrulanmasıyla belirlenir. Eksik/geç
cevap, hata veya uyuşmazlık başarı sayılmaz. Belirsiz kalıcı yazma otomatik tekrarlanmaz;
yeniden denemeden önce denetleyicinin gerçek ofsetlerini ve tanıyı kontrol edin.

## Cancel jog, Abort ve bağlantıyı kesme

**Cancel jog** sahip olunan jog'u iptal eder ve bekleyen hareket isteğini kaldırır. İptal
yavaşlayarak durmayı gerektirebilir; taze **Idle** cevabı olmadan durma doğrulanmış sayılmaz.
**Door** durumu parking hareketi içerebilir: doğrulanmış iptal değildir, kontroller kilitli
kalır ve süre dolarsa başarısızlık/Abort yolu izlenir. İptal yeni bir hareketi yetkilendirmez.

**Abort** bağlı oturumda bekleyen işlemleri ve konum/birim kanıtını geçersiz kılar. Boş başlangıç
blokları o oturumda doğrulanmışsa reset ister; aksi halde safety-door isteği kullanır ve olası
parking/durmanın doğrulanamadığı açıkça belirtilir. Reset konum güvenilirliğini kaybettirebilir.
Uygulama otomatik resume, unlock veya homing yapmaz. **Stop is unverified**, fiziksel durmanın
doğrulanmadığı anlamına gelir; başarı veya güvenli Idle anlamına gelmez.

Sahip olunan hareket sırasında **Disconnect** veya panel/uygulama kapatma, iletişimi kapatmadan
önce sınırlı iptal ve gerektiğinde Abort girişimi yapar. Kablo kopması komutun teslimini ve
durmayı doğrulamayı engelleyebilir. Worker kapanamazsa pencere korunur ve tanı gösterilir.
**Disconnect fiziksel acil durdurma (E-stop) değildir**; dışarıdan başlatılan hareketi durdurma
garantisi vermez. Fiziksel E-stop, muhafaza ve interlock'ların yerini yazılım almaz.

## Zaman aşımı ve hata

Ayar okuması üç saniyede tamamlanmazsa birim bilinmiyor olarak kalır. Port otomatik
yeniden açılmaz ve sürekli `$$` tekrarları yapılmaz. Port seçimini/denetleyiciyi ve tanıyı
kontrol edin; **Disconnect**, ardından açık bir **Connect** ile yeniden deneyin. Geç veya
istenmeden gelen birim bilgisi doğrulanmış bir oturum yerine geçmez.

Meşgul port, kopan kablo, eksik yazma veya okuma hatası iletişim hatası olarak gösterilir;
önceki koordinatlar kaldırılır. `error:`/`ALARM:` başarı veya Idle yerine denetleyicinin
tanısı olarak görünür. Kapatma hatası gizlenmez; port serbest bırakılmış varsayılmaz.

İşlem hatası, belirsiz yazma veya eski durum, yeni manuel istekleri kilitleyebilir. Otomatik
hareket tekrarı veya yeniden bağlantı yapılmaz. Fiziksel durum/ofsetleri ve tanıyı inceleyin;
uygun kurtarma sonrasında açık Disconnect/Connect ile yeni oturum başlatın.

Otomatik doğrulama FakeGRBL ve mocked seri-adaptör testlerini kullanır; gerçek bir
denetleyiciyle bağlantı veya fiziksel makine çalışması doğrulanmış değildir.
Geliştirici komutları ve fake enjeksiyonu:
[011 quickstart](../specs/011-jog-and-work-zero/quickstart.md).
