# MikroCAM alıştırmaları

Bu üç örnek, Gerber içe aktarma, delik hizalama, izolasyon ve kart kesimi
işlemlerini denemek için hazırlanmıştır. Kartlar CAM eğitim desenleridir;
elektronik devre olarak tasarlanmamıştır. Tüm koordinatlar ve çaplar **mm** cinsindedir.

| Örnek | Kart boyutu | Delikler | Alıştırma |
| --- | --- | --- | --- |
| [01 — Temel pad ve izler](practice/01_basic/) | 36 × 22 mm | 8 adet, Ø0,8 mm | İçe aktarma, hizalama, tek geçiş izolasyon |
| [02 — DIP ve konnektörler](practice/02_connectors/) | 50 × 35 mm | 24 adet: 14 × Ø0,8; 8 × Ø1,0; 2 × Ø3,2 mm | Takım seçimi, iki geçiş izolasyon, kesim köprüleri |
| [03 — Bakır dolgu](practice/03_copper_pour/) | 40 × 30 mm | 12 adet: 8 × Ø0,8; 4 × Ø1,6 mm | Boşluklar, bakır adaları, iç/dış izolasyon |

Her klasörde üç dosya bulunur:

- `copper.gbr`: bakır pad, iz veya dolgu katmanı.
- `outline.gbr`: kapalı kart sınırı; belirtilen boyutlar çizginin merkezine aittir.
- `drill.drl`: aynı orijini kullanan Excellon delik dosyası.

## Hızlı deneme

1. MikroCAM'i proje kökünden `./run-flatcam.ps1` ile aç.
2. Yeni bir projede birimi **MM** seç.
3. **File → Scripting → Run Script** (`Shift+S`) ile aşağıdaki dosyalardan birini çalıştır:
   - [practice_01.FlatScript](practice_01.FlatScript)
   - [practice_02.FlatScript](practice_02.FlatScript)
   - [practice_03.FlatScript](practice_03.FlatScript)
4. Görünümü tüm nesnelere sığdır. Bakır, kart sınırı, delikler, izolasyon ve
   dört köprülü kesim geometrisi olmak üzere beş nesne oluşmalıdır.

Nesne adları örnek numarasına göre `ex01_`, `ex02_` veya `ex03_` ile başlar.
Scriptler Ø0,2 mm izolasyon takımıyla sırasıyla 1, 2 ve 3 geçiş üretir;
çoklu geçiş örtüşmesi %30'dur. Kesim takımı Ø1,0 mm, köprü genişliği 2,0 mm'dir.
Kesim hesabı `outline.gbr` üzerinden `-margin 0` ile yapılır: takım, 0,1 mm sınır
çizgisinin dış kenarından keser. Evo'da negatif margin kesimi kartın içine kaydırır.

Aynı scripti yeniden çalıştırmadan önce çalışmanı kaydet ve yeni proje aç.
Scriptler var olan aynı adlı örnek nesnelerini algıladığında durur.
Örnekler arasında geçiş yapmak için de yeni proje açmak görünümü sade tutar.

## 01 — Temel pad ve izler

Script kullanmadan denemek için `01_basic/copper.gbr` ve `outline.gbr` dosyalarını
**Open Gerber**, `drill.drl` dosyasını **Open Excellon** ile aç.

1. İki sırada toplam sekiz pad say. Her sıranın ilk padi kare, diğerleri yuvarlaktır.
2. Delikleri görünür yap; sekiz deliğin pad merkezlerinde olduğunu kontrol et.
3. Bakır nesnesinden Ø0,2 mm takımla bir geçiş izolasyon üret.
4. Ø0,4 mm takımla ikinci bir geometri üret ve yolların bakırdan uzaklığını karşılaştır.
5. İzolasyon geometrisinden CNC Job oluştur; önizlemede kesme ve boşta hareketleri incele.

Beklenen: birbirinden ayrı iki bakır ağı, tek delik takımı ve her pad/iz çevresinde
kesintisiz izolasyon yolları. Kartın sol alt köşesi `(0, 0)` olmalıdır.

## 02 — DIP ve konnektörler

1. Ortadaki DIP deseninde 14 delik, iki konnektörde toplam 8 delik ve köşelerde
   2 montaj deliği say. DIP sıraları arası 7,62 mm, pin aralığı 2,54 mm'dir.
2. Excellon takım listesinde Ø0,8 / Ø1,0 / Ø3,2 mm çaplarını kontrol et.
3. Yalnız Ø0,8 mm takımını seçerek delik CNC Job oluştur. Sonra diğer çapları
   ayrı ayrı seç; seçilen takımın delik sayısını önizlemede karşılaştır.
4. İzolasyonu iki geçiş ve %30 örtüşmeyle üret. Tek geçiş sonucuyla karşılaştır.
5. Kart sınırından dört adet 2 mm köprülü kesim geometrisi üret.

Beklenen: 24 delik padlerle hizalıdır; izolasyon padleri kesmez. Kesim geometrisi
kartın dört kenarında birer boşluk içerir ve montaj padlerinin çevresinden hesaplanmaz.

## 03 — Bakır dolgu ve adalar

1. Bakır katmanını tek başına göster. Büyük bakır dolgu içinde 20 × 14 mm boşluk
   ve bu boşlukta dört ayrı pad/iz çifti bulunmalıdır.
2. Delikleri aç; adalarda sekiz küçük, dolgu içinde dört montaj deliğini kontrol et.
3. Tam izolasyon (`iso_type 2`) üret. Dolgunun dış ve iç sınırları ile dört adanın
   çevresinde takım yolları oluştuğunu kontrol et.
4. Tcl Shell'de aşağıdaki iki komutu ayrı ayrı çalıştırıp sonuçları karşılaştır:

```tcl
isolate ex03_copper -dia 0.2 -passes 1 -combine True -iso_type 0 -outname ex03_outer
isolate ex03_copper -dia 0.2 -passes 1 -combine True -iso_type 1 -outname ex03_inner
```

Beklenen: dış izolasyon dolgunun ve adaların dış sınırlarını, iç izolasyon ise
dolgunun ortasındaki boşluğun sınırını izler. Gerber'in açık/koyu polaritesi
doğru okunmalı; boşluk tamamen bakırla dolmamalıdır. Montaj delikleri Excellon
katmanındadır; bakır Gerber'de ayrıca oyuk olarak gösterilmez.

## G-code ve proje kaydetme denemesi

İlk scripti çalıştırdıktan sonra Tcl Shell'de şu komutla bir önizleme CNC Job oluştur:

```tcl
cncjob ex01_iso -dia 0.2 -z_cut -0.1 -z_move 2.0 -feedrate 120 -feedrate_z 60 -pp default -outname ex01_cnc
plot_all
```

Diğer örneklerde `ex01` yerine `ex02` veya `ex03` kullan.
Bu CNC değerleri önizleme alıştırması içindir; gerçek işleme değerlerini
makinene, takımına ve malzemene göre belirle.

1. CNC Job önizlemesinde takım yollarını incele ve G-code'u dışa aktar.
2. Projeyi `.FlatPrj` olarak kaydet.
3. Yeni proje açıp kaydettiğin dosyayı tekrar yükle.
4. Beş örnek nesnesinin ve oluşturduğun CNC Job'un geri geldiğini kontrol et.
   Delik çapları, katman hizalaması ve takım yolları aynı kalmalıdır.
