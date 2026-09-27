# İçe aktarma raporu

SVG'den oluşturulan Geometry veya Gerber nesnesini seçin. **Properties** bölümündeki
**Import report** düğmesini açın. Rapor, dosya içe aktarılırken kaydedilen bilgileri gösterir.

Raporda kaynak dosyanın adı ve özeti, özgün width/height birimleri, viewBox ve oran politikası,
fiziksel viewport boyutu, kaynak koordinatlarının mm'ye dönüşümü ve dikey çevirme bilgisi bulunur.
Malzemenin mm sınırları viewport boyutundan ayrı gösterilir; çizim tüm sayfayı kaplamak zorunda değildir.
Boyut dosyada yoksa “Absent”, elde olmayan bir ölçüm için “Unavailable” görülür. Boyut çıkarımı
varsa ilgili bildirim de korunur.

XMP ile tamamlanan boyutlarda rapor özgün kök ifadesini korur; örneğin `100%` ve `%` birimi,
mm cinsinden seçilen viewport boyutundan ayrı gösterilir. Bildirimler hangi eksenin XMP'den alındığını,
çelişen açık boyutların korunduğunu ve görünür katman bilgisini açıklar. Clipping uygulanmış malzeme
sınırları son sonucu gösterir; açık/kapalı yol sayıları özgün kaynak yollarını anlatmaya devam eder.

Geometri bölümünde malzeme bileşenleri, geçerli/geçersiz/boş bileşen sayıları ve kaynakta açık/kapalı
yollar görünür. Dolgu için örtük kapatılmış bir yolun kaynak bilgisi yine **açık** sayılır. Geometry
olarak korunan boyanmamış merkez çizgileri ve renklerin pozitif malzeme sayılması bildirimlerde
belirtilir. Hassasiyet değeri içe aktarıcının eğri yaklaşım bütçesidir; makinenin üretim hassasiyeti değildir.

Rapor **içe aktarma anının kaydıdır**. Nesneyi sonradan ölçeklemek, düzenlemek veya makineye
konumlandırmak raporu güncel geometri denetimine dönüştürmez. Geçerli geometri sayısı, üretime ya da
makine çalıştırmaya onay anlamına gelmez. Bildirimler ve kaynak adları düz metindir.

Rapor proje ile kaydedilir ve yeniden açıldığında aynı nesneye bağlı kalır. Önceki projelerde veya
henüz bu raporu üretmeyen içe aktarma türlerinde bölüm gizlidir; eksik bilgiler tahmin edilmez.
Bozuk veya desteklenmeyen sürümlü bir kayıt varsa rapor kullanılamaz olarak gösterilir; mevcut
nesnenin normal özelliklerine erişim sürer. Raporu görüntülemek dosyayı yeniden içe aktarmaz.

Yeni kayıtlar rapor şeması **2** ile yazılır. Geçerli şema **1** kayıtları aynı alanlarla okunur ve
yeniden kayıtta şema 2 olarak yazılır; eski şemada yüzde boyut ifadeleri kabul edilmez. Eksik rapor,
bozuk kayıt veya bilinmeyen sürüm yeni ölçüm üretmek için gerekçe değildir. Projenin diğer nesne
verileri ve kaynak metni bu rapor şema geçişiyle değiştirilmez.

Desteklenen SVG kapsamı ve açık sınırlamalar için [SVG içe aktarma rehberine](SVG_IMPORT.md) bakın.
