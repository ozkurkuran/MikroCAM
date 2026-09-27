# Üretim dosyalarını birlikte içe aktarma

File → Import → Production file set ile pencereyi açın. Gerber ve Excellon dosyalarını
pencereye bırakın veya Add files ile seçin. Inspect, içerik, FileFunction metadata ve dosya
adını ayrı kanıtlar olarak gösterir. Dosya bırakmak tek başına nesne oluşturmaz.

Her satırda biçimi, katman rolünü ve nesne adını inceleyin. Roller F.Cu, B.Cu, PTH, NPTH,
Edge.Cuts ve Other'dır. Belirsiz veya çelişkili önerileri açıkça düzeltin; bilinmeyen kaplama
PTH sayılmaz ve iç bakır dış katman olarak önerilmez. Gerber delik çizimi Gerber olarak kalır.
Birimi bulunamayan dosyada mevcut ayrıştırıcının birim varsayımı görünür; ölçek veya hizalama
dönüşümü bu pencerede yapılmaz.

Seçili satırlar için Review, sonra Import kullanın. Kaynak değişirse yeniden Inspect ve Review
gerekir. Her dosya mevcut nesne oluşturma yoluyla, güncel hedef varsayılanlarıyla açılır.
İlk başarısız dosyada işlem durur: tamamlanan nesneler kalır, sonraki dosyalar bekler.
Tamamlanan satırlar kilitlenir; kalan seçimleri tekrar inceleyerek devam edin. İşlem sırasında
pencereyi düzenleme ve kapatma kilitlidir.

Aynı yerel yol tekrarlanmaz; farklı konumdaki aynı adlı veya aynı içerikli dosyalar korunur
ve uyarılır. En fazla64 dosya, dosya başına16MiB ve toplam64MiB kabul edilir. Arşivler ve
dizinler açılmaz. Sınırlı komut/satır okuması ve çıktı geometri denetimleri vardır; eski CAM
ayrıştırıcısı ayrı bir süreç veya süre/bellek kotası içinde çalışmaz.

Kaynak dosyanın tam baytları ve şema1 kaynak/rol/birim raporu projede saklanır. Nesnenin kaynak
raporu sonradan dosyaya erişmeden okunabilir. Rapor özgün içe aktarma kanıtıdır; nesnenin daha
sonraki geometrik düzenlemeleriyle yeniden sınıflandırılmaz. Eski projelerde rapor olmayabilir.

Bu dilim katmanları otomatik hizalamaz veya alt bakırı aynalamaz. KiCad üretim paketi aktarımı
yol haritasının30. dilimindedir.
