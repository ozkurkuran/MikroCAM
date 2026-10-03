# Görsel interlace gereksinimleri

Tarih: 2026-10-02. Uygulama hedefi: Evo tabanlı MikroCAM, Windows 11, CPython 3.13.x.

Bu belge kullanıcıyla netleşen davranışın kaydıdır. Bir resim, SVG veya PDF sayfası seçilir; kazınacak siyah alan hazırlanır; satırlar N tamamlayıcı görüntüye ayrılır; LightBurn'de sıralı Image katmanları olarak açılacak proje üretilir. Kaynak biçimi işlem algoritmasını değiştirmez.

## Terimler

- **Kaynak:** Kullanıcının seçtiği dosya veya ileride Gerber geometrisi.
- **Ana maske:** Son ölçü, dönüşüm, eşik ve ters renk uygulanmış 1-bit kazıma görüntüsü.
- **Satır indeksi:** Ana maskede üstten alta `0..H-1`; boş satırlar da numaraya dahildir.
- **Grup:** `row_index % N` değeri. Gruplar `0..N-1` kimliklerini korur.
- **Geçiş:** Bir grubun bir turda işlenmesi.
- **Tur:** N grubun birer kez tamamlanması. N=3, tur=2 toplam altı planlı geçiştir.
- **Etkin geçiş:** En az bir kazınacak piksel içeren geçiş.
- **Birleşim:** Pozitif kazıma maskelerinin mantıksal OR'u. Beyaz opak resimlerin normal alfa üst üste bindirilmesi değildir.

## Kaynak desteği

| Biçim | İlk kapsam | Açık sınır |
|---|---|---|
| PNG/JPEG/BMP/TIFF/WebP/GIF | Evet | Renkli/gri/1-bit görüntü; çok kareli dosyada açık kare seçimi |
| SVG | Evet | Statik, kendi kendine yeterli çizim; desteklenmeyen öğeler raporlanır |
| PDF | Evet | Seçilen tek sayfanın görünümünü rasterleştirme; sayfa ölçüsü korunur |
| Gerber/Geometry | Ek adaptör | Mevcut nesneden maske; kaynak seçicide dosyalardan ayrı seçenek |
| HEIC/RAW/PSD gibi diğer biçimler | İlk sürüm dışında | Açık desteklenmeyen biçim hatası; uzantı değiştirerek kabul edilmez |

Fotoğraf açılabilir; ilk sürümde gri görüntüden ayarlanabilir eşikle 1-bit maske elde edilir. Fotoğraf dithering'i, gri tonla güç kontrolü ve 3D dilimleme kapsam dışıdır. Animasyon oynatılmaz; seçilen kare sabitlenir. SVG metninin fontu eksikse kullanıcıya bildirilir; sessiz font değişimiyle üretime hazır denmez.

## Gereksinimler

| Kimlik | Zorunlu davranış | Dilim |
|---|---|---|
| FR-001 | Kullanıcı KiCad/Gerber olmadan dosya açabilmeli | V1,V2 |
| FR-002 | RGBA, gri, paletli ve 1-bit kaynaklardan tek ana maske hazırlanmalı | V1 |
| FR-003 | SVG görünümü stroke, fill, delik, transform ve clipping örnekleriyle korunmalı | V2 |
| FR-004 | PDF sayfa seçimi, sayfa dönüşü ve fiziksel ölçü korunmalı | V2 |
| FR-005 | mm ölçüsü, DPI, eşik ve ters renk kullanıcıya gösterilip işte saklanmalı | V1 |
| FR-006 | N tamsayı 1..8; yeni işte 3; bool, kesirli ve aralık dışı değer reddedilmeli | V1 |
| FR-007 | Grup k yalnız `r % N == k` satırlarını taşımalı; diğer pikseller beyaz olmalı | V1 |
| FR-008 | Her parça ana maskeyle aynı W,H, konum, pitch ve tuval sınırını korumalı | V1,V3 |
| FR-009 | Her satır bir grupta; her kazınacak piksel tur başına tam bir geçişte bulunmalı | V1 |
| FR-010 | N=1 ana maskeyle piksel bazında birebir aynı olmalı | V1 |
| FR-011 | Ardışık ve deterministik karışık sıra desteklenmeli | V1,V3 |
| FR-012 | Boş satırlar yeniden numaralandırılmamalı; boş geçiş hareket üretmemeli | V1,V3 |
| FR-013 | Önizleme tek geçişi, birleşimi, planlanan sırayı ve etkin/boş geçiş sayılarını göstermeli | V1 |
| FR-014 | Tek `.lbrn2`, gömülü görüntüler, ayrı Image katmanları ve ortak yerleşim üretmeli | V3 |
| FR-015 | 1 piksel satırı = 1 tarama satırı hedef profilde doğrulanmalı | V3 |
| FR-016 | Ayarlar ve ana maske kaynak dosya taşınsa da kaydedilip geri açılabilmeli | V1 |
| FR-017 | Spot çapı biliniyorsa pitch < spot için yalnız bilgi notu gösterilmeli | V1 |
| FR-018 | Tam tur sayısı 1..999; grup tekrarları tur sırasını bozmamalı | V4 |
| FR-019 | Turdan tura sıra değişimi açık, deterministik ve kalıcı olmalı | V4 |
| FR-020 | Bekleme 0..600000 ms; yalnız ardışık etkin geçişler arasında uygulanmalı | V4 |
| FR-021 | Desteklenmeyen export ayarı açıklanıp export reddedilmeli; sessiz kayıp yasak | V3,V4 |
| FR-022 | Piksel doğruluğu, dosya doğruluğu ve LightBurn uyumluluğu ayrı test edilmeli | V1–V4 |
| FR-023 | Geometri/sıra önizlemesi makine hareketi tahmini diye sunulmamalı | V1,V3 |
| FR-024 | Kısmi yazım/iptal mevcut iş veya export dosyasını bozmamalı | V1,V3 |

## Kullanıcı senaryoları

Feature başına en fazla üç hikâye sınırı [görevlerde](tasks.md) uygulanır. Aşağıdakiler bütün ürünün kabul yolculuklarıdır.

1. 600×360 1-bit PNG, 508 DPI, N=3 açıldığında üç 30×18 mm parça ve birebir birleşim görülür; LightBurn projesi aynı sonucu verir.
2. Aynı 30×18 mm çizimin SVG ve PDF sürümü açılır; kaynak formatını değiştirmek interlace algoritmasını değiştirmez. Renderer farkları kaynak rasterleştirme testinde, satır dağılımı ayrı testte ölçülür.
3. İş kaydedilir, kaynak dosya başka yere taşınır, iş yeniden açılır; maske, parça piksel içerikleri, ölçü, sıra ve kullanıcı ayarları aynı kalır.

## Piksel ve satır değişmezleri

Ana maskeyi `M`, parça maskelerini `P[k]` olarak gösterirsek:

```text
P[k].shape = M.shape
P[k][r,c] = M[r,c] and (r % N == k)
OR(P[0], ..., P[N-1]) = M
sum(int(P[k][r,c]) for k in 0..N-1) = int(M[r,c])
```

H=10,N=3 için gruplar tam olarak `[0,3,6,9]`, `[1,4,7]`, `[2,5,8]` olmalıdır. H<N veya H%N!=0 geçerlidir. H=0 algoritma testinde boş plan üretir; sıfır boyutlu dosya kullanıcı akışında reddedilir.

“Resim birebir” sözü **ana maskeye** göre ölçülür. Renkli fotoğrafın eşikleme öncesi tonlarını veya SVG'nin sonsuz çözünürlüğünü birebir koruma iddiası değildir. N=1 için legacy G-code veya `.lbrn2` byte eşitliği iddia edilmez; bu kaynaklar için önceden mevcut native raster export yoktur.

## Boş alan ve yön kuralları

Satır silmek, kalan satırları yukarı taşımak, içerik sınırına göre her parçayı ayrı kırpmak yasaktır. Boş grup planda bulunur; `.lbrn2` içinde aynı tuvalle Output kapalı tutulur. Tamamen beyaz iş önizlenip kaydedilebilir, ancak çalışacak içerik olmadığı için LightBurn export düğmesi devre dışıdır.

Çekirdekte istenen satır yönü `r` çiftse sağa, tekse sola olarak hesaplanır. N çiftse aynı grubun bütün satırları aynı yöne bakabilir; boş satırlar bu hesabı değiştirmez.

Kullanıcının netleştirdiği Image katmanı yaklaşımında gerçek satır içi hareket LightBurn'e devredilir. İlk export modu `lightburn_managed` olarak açıkça adlandırılır. Katı `source_row_parity` koşulu istenirse yalnız bu davranışı doğrulanmış profil kabul eder; destek yoksa hata verir. Önizleme yön okları profil doğrulanmadan gerçek makine yolu gibi gösterilmez. Boş satır atlamanın gerçek davranışı da profil kabul testidir.

## İşleme sırası

`sequential`: `[0,1,...,N-1]`.

`mixed`: N'yi kapsayan en küçük 2 kuvvetinin bit tersleme sırası; N'den büyük/eşit değerleri çıkar. N=3: `[0,2,1]`; N=4: `[0,2,1,3]`; N=5: `[0,4,2,1,3]`. Bu bir termal optimizasyon veya “komşuluk asla olmaz” garantisi değildir.

V4 sıra değişiminde tur t için temel sıranın her grup kimliğine t eklenip N'ye göre mod alınır. Örnek N=3,mixed: `[0,2,1]`, `[1,0,2]`, `[2,1,0]`. Ardışık turlardaki sınır grupları aynı olabilir; plan bunu gizlemez. Kullanıcı bu opsiyonu kapatırsa her tur temel sıra tekrarlanır.

## Gelişmiş kontroller

R tur ve A etkin grup için toplam etkin geçiş `R*A` olur. Bekleme toplamı `max(R*A-1,0)*delay_ms` olarak hesaplanır; son geçişten sonra bekleme yoktur. Boş grup bekleme oluşturmaz. Her turda kullanılan tam grup sırası kalıcı iş kaydına yazılır.

V1–V3 ekranında henüz uygulanmayan tur/bekleme kontrolleri değiştirilebilir sahte seçenekler olmaz. Modelde alanlar bulunur; 1 tur ve 0 ms dışındaki kayıtlar kayıpsız açılır fakat V4/profile desteği yoksa LightBurn export engellenir.

## Kabul koşulları

- [Test matrisindeki](validation.md) her gereksinim bir otomatik teste veya açık LightBurn kabul testine bağlıdır.
- Hiçbir kaynak Gerber nesnesine dönüştürülmeye zorlanmaz.
- MikroCAM açılışı, opsiyonel SVG veya PDF bileşeni eksik diye başarısız olmaz.
- `.lbrn2` “uyumlu” sonucu yalnız doğrulanmış sürüm ve cihaz ailesi için verilir.
- N'ye bölme ısı birikimini azaltmayı amaçlar; malzemede ölçülmüş soğuma başarısı ayrı deneydir.

## Kapsam dışı işler

Makineye bağlanma veya iş başlatma, yeni `.mcam` formatı, fotoğraf dithering'i, OCR, PDF vektör çıkarma, SVG animasyonu, resimden vektör izleme, sınırsız katman sayısı, otomatik termal zamanlayıcı ve her cihaz için kesin süre hesabı bu mimarinin ilk uygulamasına dahil değildir.
