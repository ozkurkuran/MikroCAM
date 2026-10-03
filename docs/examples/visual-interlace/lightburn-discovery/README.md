# LightBurn uyumluluk keşfi için hazır kaynak seti

**Durum: kaynak görüntüler doğrulandı; bütün native LightBurn sonuçları NOT_RUN.**
Bu klasörde `.lbrn2` yoktur. Tam ürün hedefinin kalan uygulama testi için örneklerdir.
Sürüm ve cihaz türü belirtilmediği, yerel program bulunmadığı için çalışan profil
varsayılmaz. Genel prosedür: [native sözleşme](../../../design/visual-interlace/lightburn-contract.md).

## Hazır örnekler

| Klasör | Amaç | Canvas |
| --- | --- | --- |
| asymmetric-13x10-N1 … N8 | N=1–8, farklı köşeler, beyaz satırlar ve tek piksel | 13×10 px;0,65×0,50 mm |
| asymmetric-13x10-N3 | Karışık sıra 0,2,1; bu sırayla 7/10/7 siyah piksel | Aynı 13×10 canvas |
| short-13x2-N8 | H<N; 2 etkin ve 6 boş grup, cropping/kayma kontrolü | 13×2 px;0,65×0,10 mm |
| cycles-13x10-N3-R2 | İki tur, değişen mixed sıra; her piksel 2 kez | 6 planlı katman; 3 farklı PNG |

Bütün örneklerde pitch 0,05 mm / DPI 508. Her alt klasörde `master.png`, **aynı boyutlu**
`group-00.png`…grupPNG'leri ve `groups.zip` vardır. ZIPte portableJSON ve istenen plan
bulunur; native ayarlar uygulanmış sayılmaz. Ana 13×10 örneğinde 24 siyah piksel,
aktif satırlar 0,2,4,5,8,9; satırlar 1,3,6,7 beyazdır. Üst-sol 1 piksel, üst-sağ 2,
alt-sol 3 ve alt-sağ 4 piksellik işaretler ayna/öteleme kontrolü sağlar.

`expected-cases.json` mantıksal mask hash'ini, boyutu, etkin/boş grubu, istenen sırayı
ve kaynak satır paritesini verir. `profile-template.json` gözlem kaydıdır; null değeri
**bilinmiyor** demektir, unsupported veya destekleniyor demek değildir.

## Gerçek uygulamada kaydedilecek kanıt

1. LightBurn sürümünü ve cihaz ailesini (galvo/fiber veya GCode/DSP) kayda girin.
   Makine kalibrasyonu/seri numarası/lisans/token paylaşmayın. Bu test dosya ve yazılım
   Preview içindir; Start veya fiziksel Framing bu prosedürün parçası değildir.
2. Yeni boş test projesine N=1 master PNG'yi **Import** edin. Canvas boyutunu yukarıdaki
   mm ölçüsüyle ayarlayın. Katmanı Image yapın; önceden hazırlanan görüntü için
   **Pass-Through** seçin. Çözünürlüğün boyutla bağlı olması ve 180° üstten alta tarama
   anlamı resmi Image Mode belgesinde açıklanır. NegativeImage kapalı, passes 1;
   dot-width/image adjustment gibi pikseli değiştiren seçenekleri kayda girin.
   [Image Mode](https://docs.lightburnsoftware.com/latest/Reference/CutSettingsEditor/ImageMode/)
3. Çalışır kullanıcı şablonunun cihaz/güç/hız ayarlarını kullanın ve dosyaya not edin;
   bu sette üretim değerleri yoktur. Genel katman seçenekleri cihazlara göre değişebilir.
4. `.lbrn2` olarak **Save As** yapın. Sonraki proje kontrolleri **File→Open** ile açılır;
   proje Import etmek çizimleri alır fakat işlem/proje ayarlarını yüklemez.
   [File Management](https://docs.lightburnsoftware.com/latest/Reference/FileManagement/)
5. N=3 örneğin üç groupPNG'sini ayrı Image katmanlarına koyun; bütün görüntüler aynı
   anchor/X/Y ve aynı boyutta olsun. İçerik kenarından crop veya otomatik hizalama yok.
   Katman çalışma sırasını 0,2,1 olarak kaydedin; liste rengi/sırası tek başına kanıt değildir.
6. Aynı projede birer seçenek değiştirip ayrı dosyalar kaydedin: Output, çalışma sırası,
   bidirectional, scanangle, tek piksel öteleme ve varsa native interpass delay.
   Böylece dosya alanları ve gömülü bitmap kodlaması farklarla belirlenebilir.
7. N=1–8 ve short-N8 örneklerini kaydedip **Open→Save→Open→Preview** yapın. Canvas,
   üstten alta sıra, boş katman Output=off ve beyaz satırların hareketsiz atlanmasını
   ayrı gözlemler olarak kaydedin. Katı kaynak paritesi helper hesabıdır; LightBurn'ün
   gerçek davranışı aynı değilse capability True yazmayın.
8. İki tur örneğinde etkin sıra `[0,2,1,1,0,2]` olmalıdır. Katman başına tekrar 2 vererek
   `[0,0,2,2,1,1]` oluşturmak farklıdır. Altı ayrı Image katmanına aynı üç PNG yeniden
   kullanılabilir; test edilmiş kapasiteyi ve gerçek Preview sonucunu kaydedin.
9. Bekleme için yalnız gerçek laser-off geçişler arası ms desteğini sınayın. Galvo
   jump/marking µs ayarını bu bekleme sanmayın; olmayan desteği not/metadata ile taklit
   etmeyin. Kanıt yoksa native destek alanı null kalır.

Saved fixture'ları, Preview ekranlarını ve doldurulmuş gözlemleri ayrı bir profil
klasöründe tutun. Native exporter ancak bu kanıtla yapılacak; kaynak setinin varlığı
ve Python piksel doğruluğu G02'yi tamamlamaz.
