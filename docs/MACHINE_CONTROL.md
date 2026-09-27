# Machine paneli: salt okunur GRBL bağlantısı

Bu panel GRBL 1.1 denetleyicisine seri port üzerinden bağlanır; durum ve konum bilgilerini
okur. Bu dilimde hareket, jog, sıfırlama, homing, unlock, reset, spindle/lazer kontrolü,
iş gönderimi veya ham komut alanı yoktur. Gönderilen istekler yalnızca durum sorgusu
`?` ve ayar okuması `$$` olur; ayar ataması yapılmaz.

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
oluşturabilir.** MikroCAM reset/wake komutu göndermez ve bağlantı dizisi olarak DTR/RTS
değiştirmez; sürücü veya kartın port açmaya tepkisi yine de reset olabilir.

## Konumları okuma

**Machine XYZ (mm)** makine, **Work XYZ (mm)** çalışma koordinat sistemindeki X/Y/Z
konumudur. İkisi de mm cinsindedir; panel koordinat sıfırı veya iş ofseti ayarlamaz.

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

## Zaman aşımı, hata ve bağlantıyı kesme

Ayar okuması üç saniyede tamamlanmazsa birim bilinmiyor olarak kalır. Port otomatik
yeniden açılmaz ve sürekli `$$` tekrarları yapılmaz. Port seçimini/denetleyiciyi ve tanıyı
kontrol edin; **Disconnect**, ardından açık bir **Connect** ile yeniden deneyin. Geç veya
istenmeden gelen birim bilgisi doğrulanmış bir oturum yerine geçmez.

Meşgul port, kopan kablo, eksik yazma veya okuma hatası iletişim hatası olarak gösterilir;
önceki koordinatlar kaldırılır. `error:`/`ALARM:` başarı veya Idle yerine denetleyicinin
tanısı olarak görünür. Kapatma hatası gizlenmez; port serbest bırakılmış varsayılmaz.

**Disconnect** iletişimi ve sahip olunan worker'ı kapatır. Paneli veya uygulamayı kapatmak
da temizliği ister. **Disconnect hareket durdurma veya fiziksel acil durdurma (E-stop)
değildir**; başka bir kaynakla çalışan denetleyicideki hareketi durdurmaz.
Makinenin fiziksel durdurma prosedürü ayrı kalır.

Otomatik doğrulama FakeGRBL ve mocked seri-adaptör testlerini kullanır; gerçek bir
denetleyiciyle bağlantı veya fiziksel makine çalışması doğrulanmış değildir.
Geliştirici komutları ve fake enjeksiyonu:
[010 quickstart](../specs/010-machine-connect-grbl/quickstart.md).
