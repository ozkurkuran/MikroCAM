# Güvenli Z düzleminde kuru çalışma

Kuru çalışma, seçili G-code'un ayrı bir kopyasını üretir. Önce gerekiyorsa Z eksenini yalnızca
yukarı taşır; ardından XY yollarını seçtiğiniz sabit yükseklikte izler. Kaynak iş ve kesme
derinlikleri değiştirilmez. Bu, gerçek hareket üreten bir mekanik CNC işidir.

1. **G-code preflight** panelinde kaynak işi ve kurulumu analiz edin. Kaynağın ön kontrolü geçmeli.
2. **Dry run** seçeneğini açın. Kuru çalışma yüksekliğini **makine koordinatlarında, mm** olarak
   girin. Alan başlangıçta boştur; değer mevcut makine Z'sinden ve beyan edilen güvenli rapid
   Z'sinden küçük olamaz, Z hareket sınırlarının içinde kalmalıdır.
3. Hazırlamayı başlatın. Kaynak ve üretilen işin kimliklerini, seçilen düzlemi, yeni sınırları ve
   nominal süreyi inceleyin. Önizleme en fazla 200 satır gösterir; toplam satır sayısı ayrıca görünür.
   Üretilen başlangıç satırları ile kaynağa karşılık gelen satırlar ayrı işaretlenir.
4. İncelediğiniz kuru işi açıkça **Machine** paneline aktarın. Kaynak, kurulum veya yükseklik
   değişirse bekleyen hazırlık ve henüz kabul edilmemiş başlatma isteği geçersiz olur.
5. Mekanik ekipman onayını bu başlatma için yeniden verin. **Start job**, mevcut göndericideki
   G54, başlangıç konumu, birim, startup blokları ve çıkış-kapalı kontrollerini uygular.

Kaynak M3/M4 spindle, M7/M8 soğutma açma komutları ve S değerleri üretilen işten çıkarılır;
M5/M9 kapatma komutları korunur ve başlangıçta eklenir. Kaynaktaki Z hareketleri kaldırılır.
İnç/mm, mutlak/artımsal modlar, XY sırası, ilerleme ve yaylar korunur; helisel yaylar aynı XY
yayı olarak sabit Z düzlemine yansıtılır. Yalnızca Z içeren bir satırdaki mod veya ilerleme
bilgisi sonraki XY hareketini etkileyebileceği için korunur. Takım numarası metadata'sı çıkarılır.
M0/M1, takım değiştirme ve bilinmeyen anlamdaki komutlar bu dilimde desteklenmez.

Üretilen iş kendi ön kontrolünden ve gönderim hazırlığından yeniden geçer. Başlangıçtaki yukarı
hareket, yeni süre ve sınırlara dahildir. İlk Z hareketinin ACK alması tek başına Z'nin fiziksel
olarak tamamlandığını göstermez; denetleyici hareketleri sırasıyla yürütür. İlerleme ekranındaki
satır numarası, kuru işin önizlemesine aittir; kaynak satır eşlemesi bu önizlemede gösterilir.

Saf G54 ötelemesi, sıfır G92/TLO, açık rapid hızları ve göndericinin sayısal/satır/süre sınırları
burada da geçerlidir. Aşağı doğru bir başlangıç hareketi üretilmez. Yükseklik göndericide doğru
temsil edilemiyorsa veya üretilen yol sınırlara sığmıyorsa işlem reddedilir; kaynak kesme işi
otomatik olarak gönderilmez. Ayrıntılar: [iş gönderimi](JOB_STREAMING.md).

**Pause**, **Resume**, **Stop** ve uygulama kapanışı mevcut tek iletişim sahibini kullanır.
Bağlantı koptuğunda durdurma komutu makineye ulaşamayabilir; bu belirsizlik ekranda korunur.
Güvenli yükseklik, bağlama elemanı ve takım açıklığı operatörün beyanıdır; yazılım bunları ölçmez.
Çıkış-kapalı bilgisi denetleyici raporudur. Lazer kullanımı, fiziksel spindle kapanması ve çarpışma
güvenliği bu akışın donanımsız testlerinden çıkarılamaz.
