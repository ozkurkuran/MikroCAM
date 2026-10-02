# LightBurn dışa aktarma sözleşmesi

Bu belge planın en önemli entegrasyon sınırıdır. Dosyaları üretmek MikroCAM'in, gerçek tarama hareketlerini yürütmek LightBurn'ün sorumluluğudur. Native proje desteği gerçek uygulama testi olmadan tamamlandı sayılmaz.

## Sabit çıktı kuralları

1. Varsayılan çıktı tek `.lbrn2` dosyasıdır; görüntüler gömülüdür. Harici PNG yolu bağımlılığı yoktur.
2. R=1 için N ayrı Image nesnesi ve N ayrı Image katmanı bulunur. Aynı katmana N resim koymak geçerli değildir.
3. Her görüntü W×H, `W*pitch_mm` × `H*pitch_mm`, aynı X/Y ve aynı ortak transform ile yazılır.
4. Beyaz padding korunur. İçerik bounding-box'ına göre kırpma, otomatik yerleşim, piksel sayısını N'e bölme yoktur.
5. Kazınacak pikseller siyah, diğerleri beyazdır. Dosyadaki Negative Image kapalıdır; ters renk zaten ana maskede uygulanmıştır.
6. Pass-Through açılır. N=3 örneğinde efektif DPI 508 ve pitch 0,05 mm olarak kalır; 0,15 mm yazılmaz. Kesin dosya alanları fixture ile belirlenir.
7. Yatay üstten alta scan hedeflenir; açı 180°, Angle Increment=0 ve Auto-Rotate kapalı semantiği doğrulanır. Export sonrası döndürme/boyut değiştirme bu sözleşmeyi geçersiz kılar.
8. Output sırası `effective_orders` ile aynı olmalıdır. Katman renk numarası, XML düğüm sırası ve kullanıcıya görünen liste sırası eşanlamlı varsayılmaz; gerekli alanların hepsi kanıtla yazılır.
9. Her etkin geçiş bir kez çalışır. Number of Passes=1; örtük global tekrarlar 1/kapalı olarak sabitlenir.
10. Boş grup aynı canvas ile korunur fakat Output kapalıdır; hareket veya bekleme üretmemelidir.
11. Kaynak proje kullanıcı profili/şablonundan gelen güç, hız ve cihaz parametreleri korunur; sabit üretim değerleri icat edilmez.
12. Recipe/master-mask/thumbnail gibi yardımcı görseller aktif iş katmanı olarak eklenmez.

Örnek isimler: `Geçiş 1 — Grup 0`, `Geçiş 2 — Grup 1`, `Geçiş 3 — Grup 2`. Mixed sıra için görünen sıra `Grup 0, Grup 2, Grup 1` olur. V4'te isim `Tur 2 — Geçiş 1 — Grup 0` gibi genişler.

## G02 uyumluluk keşfi

Bu keşif native exporter yazılmadan önce yapılır. Hedef LightBurn sürümü ve cihaz ailesi açıkça kaydedilir; kullanıcı yanıtı yoksa bütün sürümler destekleniyor varsayılmaz. Kurulum bulunursa yalnız dosya açma/kaydetme/önizleme kullanılır, fiziksel iş başlatılmaz.

1. Özgün 600×360 1-bit örnek ve asimetrik 13×10 köşe/tek-satır örneği oluştur.
2. LightBurn'de tek Image katmanlı proje oluştur; 30×18 mm, Pass-Through ve hedef profil ayarlarıyla kaydet.
3. Birer ayar değiştirerek kaydet: iki/üç katman, ters katman sırası, bir piksel öteleme, Output kapalı, bidirectional, scan angle, repeat, varsa delay. Dosya farklarını incele.
4. Gömülü bitmap kodlaması, katman kimliği, fiziksel ölçü, transform/origin, etkinlik ve optimizasyon alanlarının gerçek adlarını manifest'e yaz.
5. Dosya formatını kullanıcı tarafından üretilmiş örneklerden ve kamuya açık birincil açıklamalardan çıkar; hayali XML etiketleriyle ilerleme.
6. Aynı semantiği yazan minimal dosyayı LightBurn'de **File → Open** ile aç, kaydet, yeniden aç ve Preview ile doğrula. Import ile ayarların taşındığı varsayılmaz.
7. H=10,N=3 ve H=2,N=8 örnekleriyle üstten alta satır sırası, padding, pasif boş katmanlar ve beyaz satır atlamayı kontrol et.
8. En az 8 katman aç/kaydet/önizle testi yap. İlk profilin `tested_layer_limit` değeri ölçülen kapasitedir; uygulamanın gerçek maksimumunu tahmin etme.

Test verileri `tests/reference/lightburn/<profile_id>/` içine konur: özgün PNG'ler, uygulamanın kaydettiği `.lbrn2` örnekleri, `manifest.json`, küçük Preview kanıtı ve beklenen semantik sonuçlar. Cihaz seri numarası, lisans anahtarı, gerçek müşteri dosyası veya makine kalibrasyon dosyası test deposuna eklenmez.

## Otomatik kontroller

- XML parse ediliyor; bütün Image nesnelerinin katman bağlantıları çözümleniyor.
- Gömülü her bitmap decode edildiğinde beklenen W,H ve 0/255 maskesini taşıyor.
- Bir turdaki bitmap birleşimi ana maskeye eşit; piksel kesişimleri boş.
- Bütün görüntülerin ölçek, konum, ayna ve canvas alanları semantik olarak eşit.
- Aktif katman listesi planın aktif geçiş listesine eşit; kapalı boş gruplar araya iş sokmuyor.
- Passthrough, inverse, scan, repeat ve sıra ayarları profil alan eşlemesine göre kontrol ediliyor.
- Exporttan sonra tekrar açıp kaydeden LightBurn'ün normalize ettiği XML ile birebir metin karşılaştırması yapılmaz; semantik karşılaştırma yapılır.

## Fiziksel satır davranışı

Görüntülerin doğru bölünmesi beyaz satırların gerçekten hareket olmadan geçildiğini veya yönün orijinal r paritesine bağlı olduğunu tek başına kanıtlamaz. Bunlar profile özgü incelemedir.

`direction_policy=lightburn_managed` ilk hedef davranıştır. UI bunun bir Image işi olduğunu açık tutar. `source_row_parity` isteyen kayıt, capability False ise `LIGHTBURN_OPTION_UNSUPPORTED` üretir. Satır yönünü düzeltmek için gizli beyaz/siyah işaretler, sahte lazer hareketleri veya hayali kontrol komutları eklenmez.

Beyaz satır skip doğrulanmazsa boş-satır hareket koşulu henüz karşılanmamıştır: profil deneysel olarak raporlanır ve tam uyumlu release hedefi sayılmaz. Sorun sadece süreye etki ediyor diye koşul sessizce silinmez.

## V4 tur ve bekleme eşlemesi

İki tur için hedef sıra N=3'te `0,1,2,0,1,2` olmalıdır. Katman başına tekrar=2 verip `0,0,1,1,2,2` üretmek yanlıştır.

İlk açık çözüm: Her `(tur,grup)` için ayrı Image katmanı; bütün katmanlarda tekrar=1. Böylece R*N katman ve N farklı bitmap içeriği bulunur. Görselleri yeniden render etme; aynı grubun PNG byte'ları tekrar kullanılabilir. Kapasite `tested_layer_limit` ile kontrol edilir. Limit aşılınca otomatik aynı katmana birleştirme, sessiz tur azaltma veya birden çok projeye bölme yoktur.

Tam iş tekrarının native olarak saklanması ileride aynı sıralı sonucu gerçek uygulamada kanıtlarsa sabit sıralı turlarda alternatif olabilir. “Global Passes” adından bunun bütün Image katmanlarını kapsadığı çıkarılmaz. G02 bunu kanıtlamadan kullanma.

Bekleme için yalnız hedef profilin etkin katmanlar arasında lazer kapalı dwell'i gerçekten saklayıp uyguladığı doğrulanırsa destek açılır. Bir XML comment'i veya recipe metadata'sı uygulanan bekleme değildir. Destek yoksa nonzero delay export'u reddedilir; alan iş kaydında korunur. Sahte çizgi, siyah piksel veya sıfır güç nesnesi ile bekleme taklidi yapılmaz.

## Süre bilgisi

MikroCAM kesin olarak piksel/satır/grup sayısını ve istenen toplam dwell'i hesaplar. Hareket süresi hedef profile bağlıdır. Doğrulanmış hız/atlama modeli yoksa `Toplam süre: LightBurn önizlemesinde hesaplanacak` gösterilir; eski süre N ile çarpılmaz. Bir hareket tahmini eklenirse lazer kapalı geçiş, satır dönüşü, katmanlar arası atlama, R tur ve dwell ayrı hesaba katılır; LightBurn karşılaştırması yapılır.

## Tamamlanma tanımı

Native export tamamlandı demek için G02 fixture'ları, otomatik semantik kontroller, hedef sürümde aç/kaydet/Preview ve N=1..8 örnekleri geçmelidir. `.lbrn2` dosyası üretemeyen PNG paketi bu hedefi tamamlamaz. İleri özellikler yalnız ilgili profil kanıtıyla tamamlandı sayılır.
