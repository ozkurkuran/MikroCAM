# Görsel satır serpiştirme kullanımı

Yerel çalışma dalı032-visual-interlace: bitmap/SVG/PDF hazırlama, satır grupları,
önizleme ve taşınabilir kayıt kullanılabilir. Native `.lbrn2` henüz desteklenmiyor;
[gerçek LightBurn profil doğrulaması](lightburn-compatibility.md) bekliyor.

## Çalıştırma

MikroCAM Evo checkout'unda Python 3.13 ve mevcut runtime kurulumu gerekir:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-visual.txt
.\.venv\Scripts\python.exe -m pip check
.\run-flatcam.ps1
```

Uygulamada Eklentiler → **Görsel satır serpiştirme** menüsünü açın.
**Resim / SVG / PDF aç…** ile kaynak seçin; çok sayfalı PDF/TIFF veya animasyonda
**Sayfa / kare** seçimini kontrol edin. Bir iş yalnız seçili sayfa/kareyi işler.

## Maskeyi hazırlama

1. Genişlik/yükseklik(mm) ve **Çıktı DPI** belirleyin. Dosya ölçüsü öneridir; metadata
   yoksa bitmap508DPI/.05 mm piksel önerisi kullanır. Ölçüler en/boy oranını korur.
2. Eşiği ayarlayın; ana maskede **siyah alan kazınacak**, beyaz alan boş kalacaktır.
   Gerekirse ters renk, ayna ve90° dönüş kullanın. Dönüş fiziksel W/H'yi takas eder.
3. Serpiştirme N=1..8 seçin; yeni iş3,1kapalı. Ardışık veya Karışık sıra seçin.
4. **Maskeyi hazırla** seçin. Kaynak, Ana maske, Tek geçiş ve Birleşim sekmelerini
   inceleyin. Geçiş seçici1tabanlı; plan listesinde Grup kimliği0tabanlıdır.
5. **Önizlemeyi yakınlaştır…** görünümünde25–800% kullanın. Büyük kaynaklarda küçük
   thumbnail büyür; export çözünürlüğü veya piksel verisi değişmez.

600×360,508 DPI örneğinde pitch.05 mm, tuval30×18 mm; N=3 parçalar yine600×360'tır.
Grup0 yalnız0,3,6…, Grup1 yalnız1,4,7…, Grup2 yalnız2,5,8… satırlarını taşır.
Diğer satırlar beyazdır. Her parça tam tuvali korur; DPI N'e bölünmez.
Birleşim, siyah/kazıma maskelerinin OR'udur; opak beyaz görüntüleri normal üst üste
koymak aynı işlem değildir. Tam bölünmeyen ölçüde sağ/altta<1 piksel padding oluşabilir.

## Kayıt ve PNG paketi

**İşi JSON olarak kaydet…** kaynak bytes ve ana maskeyi ayarlarla birlikte gömer.
**JSON işi aç…** aynı maskeyi doğrular; kaynak diskten silinse de çalışır ve kendi
kendine yeniden render etmez. DPI/ölçüde ekrandaki yuvarlama kaydı değiştirmez.

**MikroCAM projesine ekle** mevcut Geometry taşıyıcısına iş payload'ını ekler.
Ardından normal MikroCAM proje kaydını yapın. Projeyi açınca kaynak listesini yenileyip
**Projedeki görsel işi aç** seçin. Bu taşıyıcı makine çıktısı değildir.

**Geçiş PNG paketini kaydet…** ZIP içinde `group-00.png`…`group-NN.png`, `job.json`
ve `manifest.json` üretir. PNG'ler1-bit ve aynı ölçüdedir; DPI metadata korunur.
Manifest konumu, pitch'i ve istenen geçiş/tur sırasını belirtir. ZIP bir LightBurn
projesi değildir; LightBurn'e katman/recipe/bekleme ayarı uygulanmış değildir.

## Tur, bekleme ve yön

Toplam tur bütün N grupluk döngüyü tekrarlar. N=3,R2 sırası0,1,2,0,1,2'dir.
KarışıkN3 temel sıra0,2,1; turda sıra değiştirme açıkken sonraki sıra1,0,2 olur.
İstenen bekleme yalnız etkin geçişler arasında; toplam `(etkin_geçiş-1)*ms`.
Bu tercihler plan ve kayıtta korunur. Native yürütüm desteği henüz doğrulanmadı.
Gerçek hareket süresi LightBurn Preview'de hesaplanacak; panel onu tahmin etmez.

Kaynak satır paritesi helper'da rçiftse sağa, tekse sola; grup/boş satırdan etkilenmez.
Image işinin gerçek yön/boş satır atlama davranışını LightBurn hesaplar. Katı parite
isteği native profil kanıtını gerektirir. Spot çapı bilinirse pitch<spot için bilgi
notu çıkar; serpiştirme bir soğutma garantisi değildir.

## İsteğe bağlı bakır/geometri

Mevcut Gerber veya poligon Geometry kaynağını seçin; ROI X/Y min/max(mm) alanını açıkça
belirleyip **Seçilen alanı görsele dönüştür** kullanın. Siyah alan seçili bakırı temsil
eder. Bakırın dışındaki alan hedefleniyorsa **Renkleri ters çevir** ile ROI içini tersleyip
ana maskeyi inceleyin. ROI'siz sonsuz dış alan üretimi yoktur. Yeni KiCad/Gerber dosyası
bu görsel akışı kullanmak için gerekli değildir.

## Destek sınırları

PNG/JPEG/BMP/TIFF/WebP/GIF, statik SVG ve şifresizPDF desteklenir. SVG harici kaynak,
script/animasyon veya eksik fontta açık hata verir. SVG metnini path'e çevirmek font
bağımlılığını kaldırır. SVG/PDF ilk UI'de bütün seçili sayfadır; crop alanı API'de bu
biçimler için açıkça reddedilir. Bitmap16-bit gri desteklenir; bilinmeyen float/signed
örnek aralığı reddedilir. Fotoğraf tek eşikle1-bit olur; dithering/gri güç/OCR yoktur.

Kaynak64MiB, çıktı40m piksel, JSON256MiB; aşımda ölçü/DPI'ı azaltın. İptal ve hata
önceki işi korur; ayar değişince eski çıktı yeniden hazırlanmalıdır. Kaydetme/export
atomiktir. Hiçbir adım fiziksel makineyi hareket ettirmez veya lazeri çalıştırmaz.
