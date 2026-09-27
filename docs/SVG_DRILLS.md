# SVG’den delik adayları

Dosya / İçe aktar / SVG drill candidates menüsünden bir SVG seçin. Dikey çevirme seçeneği,
normal SVG içe aktarmasındaki gibi fiziksel sayfa yüksekliği üzerinden bir kez uygulanır.
Analyse sonrasında merkezleri ve çapları mm olarak inceleyin; istediğiniz satırları işaretleyin,
yeni Excellon adını girin ve Create selected drills düğmesine basın. İlk seçim boştur.

Adaylar, daha büyük eş merkezli renkli dairesel pad içinde beyaz dolgulu, çizgisiz dairelerdir.
Bu çizim yorumu gerçek delik niyetinin kanıtı değildir. Kare bir sınırlayıcı kutu yeterli değildir:
daire/ellipse eksenleri veya kapalı path’in tüm çevresi fiziksel ölçekte kontrol edilir. Path için
radyal/kiriş toleransı 0,01 mm ile yarıçapın %2’sinin küçüğüdür. Merkez toleransı 0,02 mm,
pad içinde kalma payı 0,01 mm’dir. Yetersiz çözünürlük, açık/çoklu path, çizgili beyaz şekil,
elips, tek başına beyaz şekil ve çelişen üst üste delikler aday olmaz; nedenleri gösterilir.

Tekrarlanan eşdeğer delikler birleştirilir. Çap gruplarında en büyük/en küçük farkı en fazla
0,01 mm’dir; önerilen takım çapı grubun ortalamasıdır ve oluşturmadan önce gösterilir.
Dosya yolu veya flip değişince eski seçim temizlenir. Yeni Excellon normal proje kaydı,
Drilling ve dışa aktarma akışlarını kullanır; diğer nesneleri ve kaynak SVG’yi değiştirmez.
Kaynak adı/hash’i inceleme sırasında gösterilir; Excellon mevcut proje biçiminde saklanır.

Kaynak sınırı 16 MiB, SVG sınırları 10.000 öğe/500.000 nokta; dairesel kanıt sınırı 1.000’dir.
Çok karmaşık dosyayı kaynak düzenleyicide sadeleştirin. İşlem cihazla iletişim kurmaz.
Dışa aktarmanın mevcut birim/ondalık ayarları geçerlidir; mevcut exporter metrik takım çaplarını
iki ondalık, inch takım çaplarını dört ondalık yazar. Üretim öncesi çıktının ölçülerini kontrol edin.

`tests/reference/svg-drills.svg` özgün MIT analitik çizimdir; gerçek Proteus çıktısı değildir.
Bu dilimde Proteus’un beyaz delik çizim kuralı test edilir; gerçek Proteus SVG örneğiyle doğrulama
ve fiziksel delme henüz yapılmadı. Genel geometriyi Excellon’a dönüştürme sonraki dilimdedir.

Aynı yoldaki dosyanın içeriği değişirse hash kontrolü oluşturmayı durdurur ve yeniden analiz ister. Takım grubu ortalaması yeni bir delik çakışması doğurursa seçim reddedilir.
