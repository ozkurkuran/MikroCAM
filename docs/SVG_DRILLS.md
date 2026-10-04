# SVG’den delik adayları

Dosya / İçe aktar / SVG drill candidates menüsünden bir SVG seçin. Dikey çevirme seçeneği,
normal SVG içe aktarmasındaki gibi fiziksel sayfa yüksekliği üzerinden bir kez uygulanır.
Analyse sonrasında merkezleri ve çapları mm olarak inceleyin; istediğiniz satırları işaretleyin,
yeni Excellon adını girin ve Create selected drills düğmesine basın. İlk seçim boştur.

Adaylar, daha büyük eş merkezli renkli pad içinde beyaz dolgulu, çizgisiz dairelerdir.
Bu çizim yorumu gerçek delik niyetinin kanıtı değildir. Kare bir sınırlayıcı kutu yeterli değildir:
daire/ellipse eksenleri veya kapalı path’in tüm çevresi fiziksel ölçekte kontrol edilir. Path için
radyal/kiriş toleransı 0,01 mm ile yarıçapın %2’sinin küçüğüdür. Merkez toleransı 0,02 mm,
pad içinde kalma payı 0,01 mm’dir. Yetersiz çözünürlük, açık/çoklu path, çizgili beyaz şekil,
elips, tek başına beyaz şekil ve çelişen üst üste delikler aday olmaz; nedenleri gösterilir.

Proteus, delikleri `Z` ile kapatılmamış ama başlangıç noktasına dönen dört kübik Bezier ile yazar
(spec 041). Tek alt yolun bitişi başlangıca **1e-6 mm** içinde dönüyorsa yol bu uçta kapatılır ve
aynı daire ölçütleriyle sınanır: tek yönde, ≤45° adımlarla tam **360°** dönmeli ve kendini
kesmemelidir. 3/4 yay, 0,001 mm bile açık kalan yol, iki tur atan yol veya iki ayrı alt yoldan
oluşan daire aday olmaz. Dört kübikli daire gerçek daireden en fazla yarıçapın %0,027'si kadar
dışarıdadır; bildirilen çap bu yaklaşımı içerir (Proteus'ta 1 mm delik için ≤0,0003 mm).

Pad desteği: dairesel pad kuralı aynen geçerlidir ve önceliklidir. Dairesel destek yoksa, ağırlık
merkezi delik merkezine 0,02 mm içinde olan ve beyaz daireyi 0,01 mm payla tamamen içeren beyaz
olmayan dolu tek poligon (ör. Proteus sekizgen/DIL pad, dikdörtgen pad) destek sayılır; birden
çoksa en küçük alanlı olan gösterilir. Delik merkezi ve çapı her zaman beyaz daireden gelir; pad
şeklinden delik çıkarılmaz ve pad tek başına aday olmaz. Merkezi uzakta kalan bakır döküm alanları,
clip uygulanmış, beyaz veya yalnız stroke'lu şekiller destek sayılmaz.

Tekrarlanan eşdeğer delikler birleştirilir. Çap gruplarında en büyük/en küçük farkı en fazla
0,01 mm’dir; önerilen takım çapı grubun ortalamasıdır ve oluşturmadan önce gösterilir.
Dosya yolu veya flip değişince eski seçim temizlenir. Yeni Excellon normal proje kaydı,
Drilling ve dışa aktarma akışlarını kullanır; diğer nesneleri ve kaynak SVG’yi değiştirmez.
Kaynak adı/hash’i inceleme sırasında gösterilir; Excellon mevcut proje biçiminde saklanır.

Kaynak sınırı 16 MiB, SVG sınırları 10.000 öğe/500.000 nokta; dairesel kanıt sınırı 1.000’dir.
Çok karmaşık dosyayı kaynak düzenleyicide sadeleştirin. İşlem cihazla iletişim kurmaz.
Dışa aktarmanın mevcut birim/ondalık ayarları geçerlidir; mevcut exporter metrik takım çaplarını
iki ondalık, inch takım çaplarını dört ondalık yazar. Üretim öncesi çıktının ölçülerini kontrol edin.

`tests/reference/svg-drills.svg` özgün MIT analitik çizimdir. Ayrıca gerçek, değiştirilmemiş bir
Proteus PCB SVG'si (Apache-2.0, [kaynak kaydı](../tests/reference/cad-source/proteus-breath-analyzer/))
doğrulanır: 25 beyaz deliğin tamamı, dosyanın ham koordinatlarından bağımsız hesaplanan merkezlerle
1e-6 mm içinde ve Ø1,00 mm (tek takım grubu) olarak bulunur; bu, dosyanın yanındaki Proteus CADCAM
notundaki `D=1mm` ile uyumludur. Fiziksel delme ve diğer Proteus sürümleri doğrulanmadı.
Genel geometriyi Excellon’a dönüştürme ayrı dilimdedir.

Aynı yoldaki dosyanın içeriği değişirse hash kontrolü oluşturmayı durdurur ve yeniden analiz ister. Takım grubu ortalaması yeni bir delik çakışması doğurursa seçim reddedilir.
