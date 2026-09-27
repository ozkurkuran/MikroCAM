# İçe aktarma raporu

SVG'den oluşturulan Geometry veya Gerber nesnesini seçin. **Properties** bölümündeki
**Import report** düğmesini açın. Rapor, dosya içe aktarılırken kaydedilen bilgileri gösterir.

Raporda kaynak dosyanın adı ve özeti, özgün width/height birimleri, viewBox ve oran politikası,
fiziksel viewport boyutu, kaynak koordinatlarının mm'ye dönüşümü ve dikey çevirme bilgisi bulunur.
Malzemenin mm sınırları viewport boyutundan ayrı gösterilir; çizim tüm sayfayı kaplamak zorunda değildir.
Boyut dosyada yoksa “Absent”, elde olmayan bir ölçüm için “Unavailable” görülür. Boyut çıkarımı
varsa ilgili bildirim de korunur.

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

Desteklenen SVG kapsamı ve açık sınırlamalar için [SVG içe aktarma rehberine](SVG_IMPORT.md) bakın.
