# Machine konsolu: salt okunur sorgular ve iletişim kaydı

**Plugins → Machine** panelinin altındaki **Console — read-only queries** bölümü başlangıçta
kapalıdır. Başlığa tıklayarak açın. Paneli veya konsolu açmak port açmaz ve sorgu göndermez.
Port seçimi ve açık **Connect** işlemi için [Machine rehberine](MACHINE_CONTROL.md) bakın.
Menü ve düğme adları uygulama diline göre çevrilebilir.

Listeden sorguyu seçip **Send query** düğmesine basın:

| Sorgu | GRBL 1.1 cevabı |
|---|---|
| `?` | Taze durum raporu |
| `$$` | Ayarlar; yazma veya değiştirme yapılmaz |
| `$G` | Parser modal durumu |
| `$#` | Koordinat/ofset parametreleri |
| `$N` | Kayıtlı başlangıç blokları; değiştirilmez |
| `$I` | Denetleyici sürüm/build bilgisi |
| `$CD` | Yalnız FluidNC (044): `Config/Dump` YAML yapılandırması; salt okunur, uygulama yorumlamaz |

FluidNC'de `$N` gönderilmez: FluidNC'de başlangıç satırı sorgusu değildir, adında “n” geçen
ayarları listeler. FluidNC başlangıç makroları her hareket işleminden önce otomatik ve salt
okunur doğrulanır ([Machine rehberi](MACHINE_CONTROL.md#fluidnc-044)). `$CD` GRBL'de reddedilir.
`$$` cevabındaki `$130-$132` (azami eksen hareketi) satırları `$13` önekini paylaşır ama birim
kanıtı sayılmaz (044 hotfix; GRBL ve FluidNC).

Serbest komut girişi yoktur. Konsol hareket, spindle/lazer açma, homing, unlock, reset veya
ayar yazma yolu değildir. Sorgular mevcut tek iletişim worker'ından geçer; konsol ayrı port,
okuyucu veya yazıcı oluşturmaz. Taze, birimi doğrulanmış **Idle** ve başka bekleyen işlem
bulunmaması gerekir. İş veya manuel işlem sürerken sorgu düğmesi kullanılamaz.

Tanı satırında **Pending**, **Complete** veya **Failed** durumunu okuyun. Olağan sorgunun
cevabı üç saniye içinde tamamlanmalıdır. `$$` için önceki doğrulanmış birimle aynı, tek ve
geçerli `$13` satırı ile `ok` gerekir. Eksik, bozuk veya çelişkili cevap başarı sayılmaz;
konum/birim kanıtı geçersizleşebilir. Otomatik tekrar yapılmaz. Geç ACK, reset, alarm veya
iletişim hatası sonraki sorguları kilitleyebilir; tanıyı inceleyip açıkça yeniden bağlanın.
Bir durum poll'u zaman aşımına uğrarsa, GRBL cevaplarında istek kimliği olmadığından konsol
yeni cevapları güvenle ilişkilendiremez; yeniden bağlantıya kadar sorgular kapalı kalır.

Kayıt **TX**, **RX** veya **IO** yönünü, sıra numarasını, monotonik saat zamanını ve sonucu gösterir.
Bu zaman UTC/duvar saati değildir. RX
satırları ham okuma parçalarıdır; bir GRBL satırının tamamı olmak zorunda değildir. Baytlar
Python `repr` biçiminde kaçışlarla görünür: örneğin `b'ok\r\n'`. HTML veya terminal renk/kontrol
dizileri çalıştırılmaz. **TX/complete** yalnızca transport'un tüm baytları kabul ettiğini
gösterir; denetleyicinin kabulü veya fiziksel yürütme kanıtı değildir. **TX/uncertain** kısa
yazma ya da hata nedeniyle teslimin belirsiz olduğunu gösterir; komut otomatik tekrarlanmaz.

Oturum kaydı en fazla **512 kayıt**, toplam **256 KiB ham bayt**, kayıt başına **4096 bayt**
tutar. Eski kayıtlar ve fazla baytlar atılır; sayaçları görünür. **Clear view** yalnızca mevcut
sıra numarasına kadar olan kayıtları bu görünümde gizler; denetleyicinin kaydını veya durumunu
değiştirmez. Sonraki kayıtlar görünür. Yeni bağlantı oturumu görünümün bu sınırını sıfırlar.
Hata veya Disconnect son kaydı ve sorgu tanısını korur. Atılan kayıtlar nedeniyle görünüm
tam bir iletişim dökümü değildir. Dosyaya kaydetme/export yoktur.

**Disconnect iletişimi kapatır; fiziksel E-stop değildir.** Seri port açılışı donanımsal reset
ve kayıtlı başlangıç bloklarının çalışmasına yol açabilir. Yazılım fiziksel E-stop veya
interlock yerine geçmez. Bu özellik donanımsız FakeGRBL testleriyle doğrulanmıştır; gerçek
donanım doğrulaması yapıldığı iddia edilmez.
