# G-code ön kontrolü

**G-code preflight**, seçilen metni verilen başlangıç konumu, yerleşim ve makine sınırları
altında çevrimdışı inceler. Makineye bağlanmaz, komut göndermez, kaynak metni düzeltmez veya
değiştirmez. Analiz sonucu bir işi çalıştırma izni değildir.

## Kaynak ve kurulum

1. **Plugins → G-code preflight** panelini açın. Yeni metinlerin çevirisi yoksa düğmeler
   İngilizce görünebilir. Paneli açmak analiz veya makine bağlantısı başlatmaz.
2. **Load file** ile UTF-8 G-code dosyası yükleyin ya da koleksiyonda bir CNC job seçip
   **Use selected CNC job** düğmesine basın. CNC job kaynağının tam `source_file` metni
   kullanılır; eksik bir gövdeyle sessizce devam edilmez.
3. Aşağıdaki sayısal alanları açıkça doldurun. Gerekli alanlar boş başlar; sıfır dahil
   hiçbir değer sizin yerinize varsayılmaz. Makine sınırları nesne geometrisinden alınmaz.
4. **Analyze** ile inceleyin. **Cancel** sonucu geçersiz kılar ve analizi durdurmasını
   ister. Analiz sürerken kaynak veya kurulum değişirse eski sonuç gösterilmez.

| Alan | Anlamı |
| --- | --- |
| Initial program position X/Y/Z | Metnin ilk hareketinden önceki program/iş konumu; her zaman mm. |
| Machine minimum / maximum X/Y/Z | Makine koordinatlarında bildirilen hareket zarfı, mm. Her eksende minimum maksimumdan küçük olmalıdır. |
| Safe rapid Z | Makine koordinatlarında güvenli kabul edilen minimum hızlı hareket yüksekliği, mm; Z sınırları içinde olmalıdır. |
| Z translation | Program Z konumuna eklenecek açık Z ötelemesi, mm. |
| Origin X/Y | Programdaki yerel yerleşim başlangıcı, mm. |
| Translation X/Y | Bu başlangıcın makine XY koordinatlarında karşılığı, mm. |
| Rotation | Yerel XY'nin saat yönünün tersine dönüşü, derece. |
| Mirror local X | Dönüşten önce yerel X'i ters çevirir; yerel Y ekseni etrafındaki yansıma. |
| Optional rapid rates X/Y/Z | Eksen başına nominal hızlı hareket hızı, mm/dakika. Üçünü de boş bırakın veya üçünü de pozitif girin. |

Başlangıç konumu makine sınırları dışında olabilir; bu durum analizde bir hata olarak
gösterilir, konum sınıra çekilmez. Program `G20` kullansa da paneldeki konumlar, ofsetler,
sınırlar ve hızlar mm / mm/dakika cinsindedir. Programdaki inch değerleri analiz sınırında
bir kez mm'ye çevrilir. XY dönüşümü mevcut Placement modeliyle yapılır.

**Kurulumun temel varsayımı:** başlangıç G92 geçici ofseti, takım boyu ofseti ve takım
kompanzasyonları sıfırdır. Verilen yerleşim, G54 program koordinatlarının makineye eşlemesini
tanımlar. Analiz gerçek denetleyiciyi okumaz; bu varsayımları ölçmez veya doğrulamaz.
`G54`, `G40`, `G49` metindeki uyumlu bildirimlerdir; denetleyiciye gönderilmezler.
G49 bloğu eksen, yay merkezi/yarıçapı veya hareket sözcükleriyle birleştirilemez.

## Sonucu okuma

- **Declared-setup geometry checks passed**: desteklenen metin, bildirilen kurulum altında
  tamamıyla yorumlanmış ve hata bulunmamıştır. Uyarıları yine de okuyun.
- **Blocked**: bulgu veya eksik yorumlama vardır. Eksik yorumlamada sınırlar yalnızca
  yorumlanabilen başlangıç/prefix hareketlerini kapsar; **Partial interpreted bounds** tam
  programın sınırları değildir. Toplam süre bu durumda bilinmez.
- Sınırlar; ilk konumu, doğru/hızlı hareketleri ve yayların iç ekstremalarını içerir.
  Yalnızca yay uçlarına bakılmaz. Z değerleri açık Z ötelemesinden sonraki makine değerleridir.
- Rapor hareket/blok sayıları, toplam yorumlanan yol, görülen birimler/mesafe modları,
  kaynak adı ve analize giren metnin SHA256 özetini gösterir.
- Bulgu satırları kaynakta 1'den başlar; satır **0** kurulum/program geneli içindir.
  İlk 200 bulgu gösterilir; toplam bulgu ve hata sayıları kırpılmaz. Gösterilen ilk
  bulgular yalnızca uyarı olsa bile daha sonraki bir hata programı engelleyebilir.

Dosya sonucu **yüklenen metin kopyasına** aittir; daha sonra diskte değişen dosya kendiliğinden
yeniden yüklenmez. Yeniden yükleyip analiz edin. Seçili CNC job kaynağının değişmesi, silinmesi
veya seçimin başka nesneye geçmesi sonucu geçersiz kılar; kaynak sonuç gösterilmeden önce ve
panel açıkken periyodik olarak tekrar kontrol edilir. Kurulum alanındaki her değişiklik de
sonucu temizler. Eski veya iptal edilmiş worker sonucu güncel sonuç olarak kabul edilmez.

## Desteklenen metin

Bu bir genel G-code yorumlayıcısı değildir. Standart üç eksenli GRBL yönelimli altküme:

- Hareket: `G0`, `G1`, XY düzleminde `G2` / `G3`; helical Z değişimi desteklenir.
- Birim: `G20` / `G21`; mesafe: `G90` / `G91`. Hareketten önce açıkça bildirilmelidir.
  Kesme/ilerleme hareketinden önce `G94`, yaydan önce `G17` gerekir; makine modal varsayılanı
  devralınmaz. `G91.1` artımlı yay merkezi bildirimidir.
- Yay merkezleri `I/J` ile başlangıca göre artımlıdır; `G90` bunları mutlak yapmaz.
  Eksik I veya J sıfır kabul edilir ama en az biri bulunmalıdır. `R` pozitifse küçük,
  negatifse büyük yay seçilir. `R` ile `I/J` birleştirilemez.
- Tam daire `I/J` ile mümkündür. Her yayda açık `X` veya `Y` uç sözcüğü gerekir;
  yalnızca Z veya merkez yazmak yeterli değildir. R ile tam daire, sıfır/olanaksız yarıçap,
  `K`, yay turu `P` ve 0,005 mm'den fazla yarıçap tutarsızlığı engellenir.
  Farklı uçlar arasında 10⁻⁶ radyandan küçük süpürmeler, tam daireyle karışabilecek
  sayısal belirsizlik nedeniyle desteklenmez.
- `F` pozitif, fiziksel mm/dakika olarak tutulur. Yeni bir F verilmeden birim değişirse
  önceki fiziksel ilerleme korunur. Eksik F bilinen hareket geometrisini gösterebilir ama
  hata oluşturur; süre bilinmez. Sıfır/negatif F hareket olmasa da hatadır.
- `G4 P...` saniye cinsinden beklemedir; P zorunlu ve negatif olmayan değerdir.
  Aynı blokta hareket/eksen/merkez sözcüğü olamaz.
- `M3/M4/M5`, `M7/M8/M9`, negatif olmayan `S`, 0–255 tam sayı `T`, `M0/M1/M2/M30`
  metaverisi tanınır. İsteğe bağlı satır numarası N, 0–9.999.999 aralığında tam sayıdır.
  Çıkış açma içeriği uyarı oluşturur; **hiçbiri gönderilmez**. T takım değişimi yapmaz.
  M0/M1 operatör beklemesidir; toplam süre bilinmez. M2/M30 sonrasındaki yürütülebilir metin engellenir.
- Büyük/küçük harf, bitişik sözcükler, boşluk/tab, boş satır, tek satırlı iç içe olmayan
  parantez yorumları ve noktalı virgülden satır sonuna yorumlar desteklenir.

Desteklenmeyen sözcükler sessizce atlanmaz. Örneğin `G93`, `G18/G19`, `G90.1`, `G53`,
`G55..G59`, `G10`, `G28/G30`, `G92`, `G43.1`, canned cycle/probing, `M6`, makrolar,
değişkenler, checksum ve yüzde sarmalayıcılar engellenir. G/M gruplarındaki çelişkiler,
tekrarlanan diğer sözcükler ve kullanılmayan eksen/yay/bekleme sözcükleri de hatadır.
ASCII dışı içerik ve kontrol/realtime karakterleri yorum içinde bile engellenir.
Sayılar ondalıktır; üslü sayı biçimi kullanılmaz.

Kaynak sınırları: UTF-8 metin 16 MiB, 250.000 satır, satır başına 4.096 karakter,
sayısal sözcük başına 64 karakter; desteklenen koordinat/ilerleme büyüklüğü en fazla 10⁹.
Sınır aşımı tam bir başarılı rapor üretmez. CAM'den gelen bir dosyanın otomatik olarak
bu altkümeye uyduğu varsayılmaz.

## Hızlı hareket ve nominal süre

Makine sınırları ilk konum ve tüm yol boyunca, 10⁻⁹ mm sayısal toleransla kapsayıcı
kontrol edilir. Yatay bileşeni olan bir `G0` için başlangıç/bitiş Z'nin küçüğü Safe rapid Z
altındaysa hareket güvensizdir. Yalnızca Z'de aşağı hızlı hareket de altına inemez.
Yalnızca Z'de yukarı çekilme aşağıdan başlayabilir; makine zarfı kontrolü yine geçerlidir.

Nominal ilerleme süresi `60 × yol / ilerleme`, hızlı hareket süresi eş zamanlı eksen varsayımıyla
`60 × max(|makine eksen farkı| / o eksenin hızlı hızı)` olarak hesaplanır. Yay/helix yol uzunluğu
analitiktir; bekleme P saniye ekler. Sıfır olmayan bir rapid için hızlar verilmemişse veya
M0/M1 varsa toplam **Unknown** olur; sıfır saniye olarak gösterilmez.
İvme, köşe yavaşlaması, override, denetleyici zamanlaması, spindle hızlanması ve operatör
süresi hesaba katılmaz.

## Analitik örnek

Aşağıdaki örnek yalnızca raporu anlamak içindir; fiziksel bir makinede çalıştırma önerisi değildir.
Initial XYZ `(0, 0, 5)`, makine minimum `(-10, -10, -2)`, maksimum `(20, 20, 10)`, Safe Z `5`,
Z translation `0`, origin/translation `(0, 0)`, rotation `0`, mirror kapalı ve rapid hızları
`(600, 600, 120)` değerlerini açıkça girin:

```gcode
G21 G90 G17 G94 G54 G40 G49
G1 Z-1 F60
G1 X10 F120
G0 Z5
M2
```

Yorumlanan sınırlar `(0, 0, -1)` ile `(10, 0, 5)`, yol 22 mm, nominal süre 14 saniyedir.
Bu sonuç takım/stock/bağlama çarpışmasını, fiziksel açıklığı, limitlerin doğruluğunu, denetleyici
uyumluluğunu veya gerçek G92/TLO durumunu doğrulamaz. Panelde run/send düğmesi yoktur.
Cancel yalnızca analizi iptal eder; gerçek makine hareketini durduran bir E-stop değildir.
