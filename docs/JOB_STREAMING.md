# İncelenmiş mekanik CNC işi gönderme

Bu akış GRBL 1.1 tabanlı **mekanik iş mili** içindir. İş mili/PWM çıkışına lazer
bağlıysa kullanmayın. Laser CAM bu akıştan ayrıdır; burada lazer işi gönderilmez.
Ekrandaki konum ve çıkış bilgileri kontrolcünün bildirimidir, fiziksel ölçüm değildir.
Donanımsal acil durdurma ve makinenin güvenlik prosedürü kullanılabilir durumda olmalıdır.

## İnceleme ve açık başlatma

1. `G-code preflight` panelinde seçili CNCJob kaynağını veya dosyayı yükleyin.
   Başlangıç XYZ, makine sınırları, Safe-Z, Z ofseti ve yerleştirme değerlerini
   gerçek kurulum için açıkça girin. Gönderme için üç hızlı hareket hızı da gereklidir.
   G92 ve takım uzunluk ofsetinin sıfır olduğu varsayılır; canlı kontrol bunu doğrular.
2. Analizi çalıştırın ve bulguları inceleyin. Başarılı analiz fiziksel güvenlik onayı
   değildir. Gönderme yalnızca XY ötelemesini destekler; döndürme ve aynalama kullanılamaz.
3. `Load reviewed job into Machine` ile o kaynağı ve raporu aktarın. Hazırlık sırasında
   rapor yeniden hesaplanır ve bütün alanları karşılaştırılır. Kaynak, ayarlar veya
   inceleme değişirse yeni analiz ve aktarım gerekir; metin otomatik düzeltilmez.
4. `Machine` panelinde doğru portu seçip bağlanın. Port açılması kontrolcüyü sıfırlayabilir
   ve yapılandırılmış başlangıç bloklarını çalıştırabilir. Konumlar güncel ve birimleri
   doğrulanmış olmalıdır. Her `Start job` için mekanik ekipman kutusunu yeniden onaylayın.
   Aktarım veya bağlantı kendi başına işi başlatmaz.

Başlatmadan önce canlı kontrol boş N0/N1 başlangıç bloklarını, `$13` rapor birimini,
`$32=0` mekanik kipini, `$31..$30` iş mili aralığını ve kaynakta kullanılan her aktif
S değerini doğrular. M5/M9 sonrası kip okuması G54 ve çıkışların kapalı olduğunu
bildirmelidir. G54 ofseti, başlangıç makine konumu, sıfır G92/TLO ve eksiksiz ofset
envanteri kontrol edilir. Konum/ofset karşılaştırma toleransı 0,005 mm'dir.
Etkin iş sırasında elle jog, sıfırlama veya başka iş başlatma engellenir.

## Desteklenen kaynak ve sınırlar

Ön kontrolün desteklediği açık G20/G21, G90/G91, G17, G94 kipleri ve G54 ile
G0/G1/G2/G3 hareketleri kullanılır. Yaylar XY düzlemindedir; G4 beklemesi desteklenir.
M3/M4 için önceden veya aynı blokta açık, pozitif S gerekir. M8 yalnızca mekanik
ekipman onayıyla kullanılabilir. M7 tamamen dışlanmıştır; M0/M1 program duraklatmaları
gönderilemez. Desteklenmeyen kip, makro veya sorgu gönderilmez.

- Bir gönderilen blok, son LF dahil en fazla 79 ASCII bayttır. Yorumlar ve boşluklar
  kaldırılır, harfler büyütülür; sayıların yazımı korunur.
- Her sayı en fazla sekiz rakam içerebilir; baştaki sıfırlar da sayılır, işaret ve
  nokta sayılmaz. Daha uzun yazım GRBL'nin sayı kırpması nedeniyle reddedilir.
  Float32 dönüşümünde sonlu olmayan veya sıfıra kaybolan sayılar da reddedilir.
- Muhafazakâr float32 hedef hesabı, incelenen hedefe göre 0,001 mm'den fazla saparsa
  veya tanımlanan zarf/Safe-Z sınırını aşabilirse hazırlık reddedilir. Bu kontrol
  firmware yay interpolasyonu, adım yuvarlama veya fiziksel doğruluk garantisi değildir.
- Nominal süre bilinen, pozitif ve en fazla 8640 saniye olmalıdır. Kaynak sınırları
  16 MiB, 250.000 satır ve satır başına 4096 karakterdir.

Kaynak EOF ile bitebilir; M2/M30 zorunlu değildir. Son kaynak ACK'sinden sonra uygulama
açık M5/M9 gönderir, kapalı çıkış kipini yeniden okur ve son hedefte yeni Idle bildirimi
bekler. Bu sıra tamamlanmadan `Complete` gösterilmez.

## İlerleme, bekleme ve durdurma

`Accepted blocks` kontrolcünün ACK verdiği blok sayısıdır; fiziksel işleme yüzdesi
değildir. Planlayıcıda hareketler hâlâ bekliyor olabilir. Normal sorgu yanıt süresi
3 saniye, konum güncelliği sınırı 2 saniyedir. Kaynak ve son M5/M9 ACK bekleme süresi
`max(30, 10 × nominal süre + 30)` saniyedir ve en fazla 24 saattir. Doğrulanmış
duraklamanın süresi bu beklemeye eklenir. Yavaş hız geçersiz kılması veya ivmelenme
bu süreyi aşabilir; hata halinde otomatik tekrar gönderme yapılmaz.

`Pause job` yeni blok beslemeyi keser ve `!` ile feed hold ister. Hold:1 duruyor
anlamına gelmez; yeni Hold:0 veya Idle bildirimi beklenir. Duraklama iş mili ve
soğutucunun kapalı olduğunu garanti etmez. `Resume job` aynı iş/oturum için açık
komuttur; Hold:0 durumunda `~` gönderilir. Bekleyen ACK korunur, blok yeniden gönderilmez.

`Stop job`, hata veya etkin işi bağlantıdan ayırma, uygulamadaki kalan gönderim kuyruğunu siler
ve işi yeniden başlatmaya kapatır. Doğrulanmış boş başlangıç blokları varsa reset,
yoksa safety-door isteği kullanılır; safety-door yapılandırılmış park hareketi yapabilir.
Ekranda **physical stop unverified** kalır. Bu bir fiziksel durma kanıtı değildir.
Makineyi kendi güvenlik prosedürüyle kontrol edin; devam etmek için yeniden bağlanıp
yeniden inceleyin. Kısmi yazma, bağlantı kaybı veya hata yanıtından sonra tekrar gönderilmez.

Uygulama kapanışı iletişim sahibini durdurup en fazla dört saniye bekler; sürücü bu
sınırı aşarsa pencere ve canlı iş parçacığı tutulur. Bağlantının kapanması harici
hareketi durdurma garantisi vermez. Kontrolcüye ait reset/door isteği de donanımsal
acil durdurmanın yerine geçmez.
