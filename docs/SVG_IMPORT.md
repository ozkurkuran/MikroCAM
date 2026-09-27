# SVG içe aktarma: fiziksel ölçek, dönüşümler ve çizgi kalınlığı

SVG dosyasını mevcut **Import SVG** işlemiyle **Geometry** veya **Gerber** olarak açın.
Yeni bir sihirbaz veya makineye gönderme işlemi yoktur. İçe aktarmadan sonra nesnenin
ölçülerini ve boşluklarını kontrol edin; dosyanın görünümü tek başına üretime uygunluk kanıtı değildir.
Menü ve bildirim adları uygulama diline göre çevrilebilir.

## Boyut ve koordinatlar

Desteklenen uzunluk birimleri `mm`, `cm`, `in`, `pt`, `pc` ve `px`'tir. Birimsiz değerler ve
`px`, **96 px/inç** CSS temelini kullanır. Yüzde, `em`, `ex` veya tanınmayan birimler tahmin
edilmez. Eleman uzunlukları yerel SVG koordinatlarına dönüştürülür; ardından kök viewport ve
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

İçe aktarma sonucu önce mm cinsinden hesaplanır, sonra mevcut mm/inç çalışma birimine bir kez
çevrilir. Ek elle ölçekleme yapmayın. SVG kaynak dönüşümü, sonraki CAM→makine **Placement**
dönüşümünden ayrıdır; makine yerleşimini veya iş sıfırını değiştirmez.

## Şekiller, gruplar ve çizgi kalınlığı

`path`, dikdörtgen/yuvarlatılmış dikdörtgen, daire, elips, line, polyline ve polygon desteklenir.
`matrix`, `translate`, `rotate` (isteğe bağlı merkezle), `scale`, `skewX` ve `skewY` dönüşümleri
liste, grup ve eleman sırasıyla uygulanır. Yerel `use`/`#id` referansları ve X/Y ofsetleri
desteklenir; kullanılmayan tanımlar çizilmez. Eksik, yinelenen veya döngülü referanslar hata verir.

Desteklenen sunum özellikleri gruptan miras alınır; elemanın inline `style` değeri ilgili
sunum niteliğini geçersiz kılar. `fill` ve `stroke`, pozitif üretim malzemesi oluşturur.
**Beyaz renk boşluk açmaz**; renkler elemanlar arasında boolean çıkarma talimatı değildir.
Bu CAM renk politikası bildirimde açıklanır.

Stroke, kaynak koordinatlarında belirtilen genişlikte katı alana genişletilir; sonra scale/skew
uygulanır. Böylece eşit olmayan ölçekleme çizgi kalınlığını da SVG dönüşümüyle birlikte değiştirir.
`butt`, `round`, `square` uçlar ve `miter`, `round`, `bevel` birleşimler desteklenir.
`stroke-miterlimit` için bu içe aktarıcının kabul aralığı **0–1000**'dir; varsayılan 4'tür.
Miter oranı sınırı aşarsa birleşim bevel olur. `stroke="none"` veya sıfır genişlik katı stroke
eklemez; negatif genişlik hata verir.

Basit, kesişmeyen halkalarda `nonzero` ve `evenodd` dolgu kuralları desteklenir; iç içe
halkaların yönü ve boşlukları korunur. En az üç farklı noktası olan açık bir yol dolgu için
örtük kapatılabilir; kaynak yolun açık/kapalı bilgisi değiştirilmez.

**Geometry**, aksi halde boyanmayan açık merkez çizgilerini açık bir bildirimle tutabilir.
**Gerber** yalnızca katı malzemeyi alır; yalnızca boyanmayan çizgiler içeren dosya boş Gerber
olarak başarıyla açılmaz. Bir çizgiyi Gerber malzemesi yapmak istiyorsanız açıkça stroke ve
genişlik tanımlayın.

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

## Desteklenmeyen görünüm

Aşağıdakileri kaynak editörde sadeleştirip yeniden dışa aktarın; içe aktarıcı bunları sessizce
görmezden gelerek benzer bir çizim üretmez:

- Kendi kendini kesen/üst üste binen stroke yolları, kesişen veya dokunan dolgu halkaları ve
  genel compound-path/clip işlemleri. Bu geniş kapsam sonraki **019** dilimindedir.
- Metin ve font yerleşimi: metni önce vektör editörde **path/outline** biçimine dönüştürün.
- Harici veya gömülü stylesheet, harici referanslar, fontlar, görüntüler ve script.
  Desteklenen inline sunum `style` nitelikleri, genel CSS desteği anlamına gelmez.
- `clip`, mask, filter, marker, gradient/pattern/paint server ve renk/compositing çıkarımları.
- Kesikli stroke/dash, non-scaling stroke, özel paint-order ve CSS üzerinden geometri dönüşümü.
- Kısmi opacity ve çözümlenmemiş yüzde/font birimleri. Tam saydamlık görünmez malzeme,
  tam opaklık normal malzeme olarak ele alınır; `display:none`/`visibility:hidden` çizilmez.

İçe aktarma hata verirse bildirilen özelliği kaynakta düzeltin. Dosyanın uzantısını değiştirmek
veya uyarıyı yok saymak fiziksel ölçeği ya da malzeme sınırını doğrulamaz.
