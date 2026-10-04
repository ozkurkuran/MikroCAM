# SVG içe aktarma: fiziksel ölçek, dönüşümler ve çizgi kalınlığı

SVG dosyasını mevcut **Import SVG** işlemiyle **Geometry** veya **Gerber** olarak açın.
Yeni bir sihirbaz veya makineye gönderme işlemi yoktur. İçe aktarmadan sonra nesnenin
ölçülerini ve boşluklarını kontrol edin; dosyanın görünümü tek başına üretime uygunluk kanıtı değildir.
Menü ve bildirim adları uygulama diline göre çevrilebilir.

## Boyut ve koordinatlar

Desteklenen uzunluk birimleri `mm`, `cm`, `in`, `pt`, `pc` ve `px`'tir. Birimsiz değerler ve
`px`, **96 px/inç** CSS temelini kullanır. `em`, `ex` ve tanınmayan birimler tahmin edilmez.
Eleman uzunlukları yerel SVG koordinatlarına dönüştürülür; ardından kök viewport ve
`viewBox` eşlemesi uygulanır. Dosyadaki boyutları ve koordinat sistemini birlikte değerlendirin.

Kök `width` ve `height` fiziksel viewport boyutunu belirler. `viewBox` başlangıcı sıfır olmak
zorunda değildir; başlangıç ofseti de hesaba katılır. Örneğin:

```xml
<svg xmlns="http://www.w3.org/2000/svg"
     width="100mm" height="50mm" viewBox="0 0 200 100">
  <rect x="20" y="20" width="40" height="20"/>
</svg>
```

Bu dikdörtgen, dikey çevirme olmadan **20 × 10 mm** boyutunda, `(10, 10)`–`(30, 20)` mm
sınırlarındadır. Mevcut içe aktarma yolunun dikey çevirme seçeneği açıksa, 50 mm viewport
yüksekliği çevresinde bir kez çevrilir ve sınırlar `(10, 30)`–`(30, 40)` mm olur.

Varsayılan `preserveAspectRatio="xMidYMid meet"`, oranı koruyup çizimi viewport içinde ortalar;
kenarlarda boşluk oluşabilir. Dokuz hizalama seçeneğinin `meet` biçimi desteklenir. `none`
seçeneği X ve Y'yi bağımsız ölçekleyebilir. `slice`, `defer` ve iç içe viewport desteklenmez.

İki kök boyutu da eksikse geçerli `viewBox` boyutları piksel olarak kullanılabilir. Tek boyut
eksikse `viewBox` oranından çıkarılabilir. Bu çıkarımlar bildirimle açıklanır. `viewBox` yoksa
iki boyut da gerekir. Amaçlanan fiziksel boyutu garanti etmek için kök boyutlarını açıkça yazın.

Illustrator tarzı XMP `MaxPageSize` kaydı, kökün doğrudan SVG `metadata` bölümünde bulunuyorsa
eksik kök boyutlarını tamamlayabilir. Kök boyutu yüzde ise geçerli XMP zorunludur: `50%` gibi
bir değer, bilinmeyen dış viewport'un yarısı sayılmaz; ilgili XMP sayfa boyutu kullanılır.
Tek ve eksiksiz kayıttaki `w`, `h`, `unit` alanları okunur; mm, cm, inç, point, pica ve pixel
adları/birimleri desteklenir. Her eksen ayrı değerlendirilir: açık kök boyutu XMP ile çelişirse
kök değeri korunur ve bildirim gösterilir. Bozuk açık boyut XMP ile onarılmaz. Gerekli XMP
eksik, belirsiz veya geçersizse içe aktarma başarısız olur. Tam açık boyutlar varken kullanılmayan
bozuk XMP yalnızca uyarı üretir. Özgün boyut ifadeleri raporda korunur.

İçe aktarma sonucu önce mm cinsinden hesaplanır, sonra mevcut mm/inç çalışma birimine bir kez
çevrilir. Ek elle ölçekleme yapmayın. SVG kaynak dönüşümü, sonraki CAM→makine **Placement**
dönüşümünden ayrıdır; makine yerleşimini veya iş sıfırını değiştirmez.

## Şekiller, gruplar ve çizgi kalınlığı

`path`, dikdörtgen/yuvarlatılmış dikdörtgen, daire, elips, line, polyline ve polygon desteklenir.
`matrix`, `translate`, `rotate` (isteğe bağlı merkezle), `scale`, `skewX` ve `skewY` dönüşümleri
liste, grup ve eleman sırasıyla uygulanır. Yerel `use`/`#id` referansları ve X/Y ofsetleri
desteklenir; kullanılmayan tanımlar çizilmez. Eksik, yinelenen veya döngülü referanslar hata verir.

Desteklenen sunum özellikleri gruptan miras alınır; elemanın inline `style` değeri ilgili
sunum niteliğini geçersiz kılar. Gömülü SVG stylesheet için basit etiket, `*`, `.class`, `#id`
ve virgülle ayrılmış seçiciler desteklenir. Öncelik `!important`, seçici özgüllüğü ve kaynak
sırasına göre çözülür; inline normal değer normal kurallardan, inline important ise stylesheet
important değerinden önceliklidir. Metadata içindeki style ve yabancı ad alanındaki style
çizimi etkilemez; `defs` içindeki gerçek SVG style kuralları uygulanabilir. Harici veya koşullu
CSS, birleşik seçiciler ve CSS üzerinden geometri değişikliği desteklenmez. Uygulanan dolgu/çizgi
değerleri ilgili elemanda doğrulanır. `display:none` alt ağacı gizler; `visibility:hidden`
miras alınır ve çocukta tekrar visible yapılabilir. Görünür katman etiketleri rapor bildirimlerinde
tutulur; ayrı katman seçme arayüzü yoktur.

`fill` ve `stroke`, pozitif üretim malzemesi oluşturur.
**Beyaz renk boşluk açmaz**; renkler elemanlar arasında boolean çıkarma talimatı değildir.
Bu CAM renk politikası bildirimde açıklanır.

Stroke, kaynak koordinatlarında belirtilen genişlikte katı alana genişletilir; sonra scale/skew
uygulanır. Böylece eşit olmayan ölçekleme çizgi kalınlığını da SVG dönüşümüyle birlikte değiştirir.
`butt`, `round`, `square` uçlar ve `miter`, `round`, `bevel` birleşimler desteklenir.
`stroke-miterlimit` için bu içe aktarıcının kabul aralığı **0–1000**'dir; varsayılan 4'tür.
Miter oranı sınırı aşarsa birleşim bevel olur. `stroke="none"` veya sıfır genişlik katı stroke
eklemez; negatif genişlik hata verir.

`nonzero` ve `evenodd` dolgu kuralları desteklenir; iç içe, dokunan, örtüşen veya kendi kendini
kesen compound konturlar kaynak yönü ve dolgu kuralıyla değerlendirilir. Kesişimler için sınırlı
topoloji hesabı yapılır; keyfi snapping veya geometri onarımı uygulanmaz. En az üç farklı noktası olan açık bir yol dolgu için
örtük kapatılabilir; kaynak yolun açık/kapalı bilgisi değiştirilmez.

**Geometry**, aksi halde boyanmayan açık merkez çizgilerini açık bir bildirimle tutabilir.
**Gerber** yalnızca katı malzemeyi alır; yalnızca boyanmayan çizgiler içeren dosya boş Gerber
olarak başarıyla açılmaz. Bir çizgiyi Gerber malzemesi yapmak istiyorsanız açıkça stroke ve
genişlik tanımlayın.

## Yerel clipping

Yerel `clip-path="url(#id)"` başvuruları, `userSpaceOnUse` ve `objectBoundingBox` çerçevelerinde
desteklenir. Clip içindeki temel şekiller birleşim oluşturur; üst ve alt elemanın clip uygulamaları
birlikte kesişim olarak uygulanır. Tanımın kendi `clip-rule` mirası kullanılır. Clip silueti
oluşturulurken fill, stroke, opacity ve stroke görünüm değerleri kullanılmaz; display ve visibility
etkilidir. Boş veya tümü gizli bir clip, ilgili malzemenin tamamını keser.

`objectBoundingBox`, çizgi kalınlığı eklenmeden önceki kaynak yollarının sınırını kullanır; grup
clip'i grubun tamamını değerlendirir. Bu normalize çerçevede yüzde uzunluklar desteklenir, fiziksel
birimli uzunluklar desteklenmez. Sıfır genişlik/yükseklik hata verir. Clip tanımında temel şekil ve
yerel temel şekil `use` başvurusu kullanılabilir; metin, grup ve tanım içinde başka clipping yoktur.
Harici, eksik veya döngülü başvuru başarısız olur. Kaynak yol bilgisi değişmez; rapor malzeme sınırları
clipping sonrasını gösterir. SVG drill incelemesi clipping uygulanmış dairelerden tam delik çıkarmaz.

## Yaklaşım sınırı ve kaynak korunması

Eğriler ve yuvarlak stroke bölümleri doğrusal parçalara yaklaştırılır. Fiziksel eğri bütçesi
**0,01 mm**'dir: eğri düzleştirme ve yuvarlak stroke örneklemesi ayrı ayrı **0,005 mm** kullanır.
Bütçe, kaynak dönüşümünün hata büyütmesi hesaba katılarak yerel koordinatlara çevrilir.
Bu bir tarayıcıyla piksel eşitliği veya makinenin fiziksel doğruluğu iddiası değildir.

Kaynak dosya değiştirilmez. Başarılı içe aktarmada kaynak metni nesnede tutulur; UTF-8,
isteğe bağlı BOM ve satır sonları korunur. Ölçek çıkarımı ve desteklenmeyen davranışlar için
bildirimleri okuyun. Geçersiz veya desteklenmeyen dosya kısmi başarı üretmez ve mevcut nesneleri
değiştirmez.

Kaynak 16 MiB, XML 10.000 eleman/64 derinlik, yerel referans 32 derinlik ile sınırlıdır.
Eleman başına 100.000, belge başına 500.000 üretilmiş koordinat ve eleman başına 256 kapalı
halka sınırı vardır. Aşırı karmaşıklık, sonlu olmayan sayılar veya tekil dönüşümler açık hata verir.

Gömülü CSS toplam 65.536 karakter ve 256 genişletilmiş seçiciyle sınırlıdır. Clip zinciri en fazla
8 uygulama, her tanım en fazla 64 şekildir; uygulama sayısı × eleman sayısı en fazla 500.000 olabilir.
Clip overlay ön kontrolünde 2.048 segment ve 32.768 kesişen segment çifti sınırı vardır. Karmaşık
compound dolgu için 2.048 segment, 32.768 kesişen çift, 2.048 yüz ve 2.000.000 yüz/segment işlemi
sınırı uygulanır. Clip ve sonuç koordinatları mevcut belge bütçesine dahildir. Bu sınırlarda hata
alırsanız kaynak çizimi sadeleştirin.

## Desteklenmeyen görünüm

Aşağıdakileri kaynak editörde sadeleştirip yeniden dışa aktarın; içe aktarıcı bunları sessizce
görmezden gelerek benzer bir çizim üretmez:

- Kendi kendini kesen veya üst üste binen stroke yolları; desteklenen compound dolgu bu
  stroke kısıtını kaldırmaz.
- Metin ve font yerleşimi: metni önce vektör editörde **path/outline** biçimine dönüştürün.
- Harici/koşullu stylesheet, karmaşık CSS seçicileri, harici referanslar, fontlar, görüntüler ve script.
  Basit gömülü kurallar, genel CSS desteği anlamına gelmez.
- `clip`, mask, filter, marker, gradient/pattern/paint server ve renk/compositing çıkarımları.
- Kesikli stroke/dash, non-scaling stroke, özel paint-order ve CSS üzerinden geometri dönüşümü.
- `DOCTYPE` veya entity bildirimi. Birçok Illustrator sürümü standart SVG 1.1 DOCTYPE satırını
  yazar; geometri içe aktarıcısı bunu da reddeder. Dosyayı DOCTYPE olmadan yeniden dışa aktarın.
  Proteus SVG çıktısındaki `vector-effect="non-scaling-stroke"` nitelikleri de non-scaling stroke
  kapsamında hata verir.
- Görünür malzemede kısmi opacity ve belirtilen kök/XMP veya bbox-clip kapsamı dışındaki yüzde/font birimleri. Tam saydamlık görünmez malzeme,
  tam opaklık normal malzeme olarak ele alınır; `display:none`/`visibility:hidden` çizilmez.

İçe aktarma hata verirse bildirilen özelliği kaynakta düzeltin. Dosyanın uzantısını değiştirmek
veya uyarıyı yok saymak fiziksel ölçeği ya da malzeme sınırını doğrulamaz.

Illustrator'ın kökte yazdığı `enable-background` bildirimi yalnız filtre arka planını hazırlar.
Geçerli SVG 1.1 sözdizimi doğrulanır ve malzemeyi değiştirmediği için yok sayılır; filtreler yine
desteklenmez ve bozuk değerler hata verir.

Illustrator tarzı clip/compound örnekleri MikroCAM tarafından yazılmış analitik test çizimleridir.
Ayrıca lisansı ve kaynağı kayıtlı iki gerçek Illustrator dışa aktarımı doğrulanır: yalnız XMP
`MaxPageSize` ile 50 mm sayfa veren bir çizim ve katman, gömülü CSS, compound harfler ve stroke
çerçeve içeren bir çizim ([kaynak kayıtları](../tests/reference/cad-source/)). Gerçek Illustrator
clip örneği bulunamadı; tüm Illustrator dosyalarıyla uyumluluk veya fiziksel üretim doğrulaması
iddia edilmez.
