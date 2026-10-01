# GRBL gönderim modları

Machine panelindeki tek iş ve **Job queue…** pencerelerinde varsayılan **Send-response**,
her kaynak bloğu için ACK bekler. **Character counting** açıkça seçilirse aynı iletişim sahibi
birden fazla tam kaynak satırını gönderir. Seçim bağlantı veya hareket başlatmaz; Start
hazırlanmış kaynak ve mekanik onayla birlikte modu değişmez istek içine alır.

Her işte salt okunur `$I` sorgusu GRBL1.1 build ve `[OPT:flags,planner,rx]` kapasitesini doğrular.
Kapasite `min(rx,128)` byte olarak sınırlanır; eksik/hatalı kanıt veya bütçeden büyük kaynak
bloğu hareket gönderilmeden reddedilir. Varsayılan mod bu kapasite sorgusuna ihtiyaç duymaz.

FIFO tam ASCII kaynak satırı ve LF byte sayısını, kaynak indeksini ve ACK son zamanını tutar.
Yalnızca tam `ok` veya `error:` en eski kayda aittir. Durum/MSG/eksik satır kredi vermez.
Hazırlama/ayar/modal sorguları ve son M5/M9/Idle/koordinat kanıtı bu pencereye dahil edilmez.
Kabul sayısı tamamlanan fiziksel hareket sayısı değildir.

Hold yeni satırları durdurur, bekleyen ACK'lerin gelmesine izin verir. Açık Resume bütün
bekleyen son zamanlarını Hold süresiyle uzatır ve taze durum bekler. Her taşıma tesliminden
önce öncelik kontrol edilir. Hata/alarm/reset/timeout/kopma/Stop ileri gönderim ve kalan kuyruk
onayını iptal eder; retry veya yeniden bağlantıda otomatik başlatma yoktur. GRBL tamponuna
zaten alınmış hareketler yürümüş olabilir; reset girişimi fiziksel duruş kanıtı sayılmaz.

Protokol bilgileri: [GRBL 1.1 Interface](https://github.com/gnea/grbl/wiki/Grbl-v1.1-Interface).
Firmware kaynak kodu kopyalanmadı. Fake'in bounded RX/planner modeli donanım/süre emülatörü
ve hız kazancı ölçümü değildir. Gerçek GRBL doğrulaması [saha protokolündedir](hardware/GRBL_VALIDATION.md);
son durum [iş takibinde](IS_TAKIP.md). FluidNC/grblHAL/TCP/SD kapsam dışı ertelenmiş işlerdir.
