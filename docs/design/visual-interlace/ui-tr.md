# Türkçe arayüz ve etkileşim metinleri

Panel adı: **Lazer için görsel hazırla**. Akış: kaynak seç → ölçü ve kazıma maskesi → geçiş önizlemesi → LightBurn'e aktar. Mevcut uygulama içinde tek panel; yeni genel çalışma alanı tasarımı yok.

Kodda mevcut `_()` çeviri düzeni kullanılır; bu dilimde Türkçe metinler fallback olarak tanımlıdır. Kullanıcıya algoritma/serializer sürümü gibi uygulama içi alanlar gösterilmez.

## Kaynak ve ölçü

| Alan veya eylem | Türkçe metin | Yardım |
|---|---|---|
| Dosya aç | Görsel aç… | Resim, SVG veya PDF seçin. |
| Nesneden al | Seçili nesneyi kullan | Gerber veya geometri nesnesinden kazıma alanı hazırlayın. |
| Kaynak etiketi | Kaynak | Dosya adı ve türü |
| Sayfa | Sayfa | Önizlenen sayfa işlenecektir. |
| Kare | Kare | Animasyonun veya çok sayfalı görüntünün tek karesini seçin. |
| Genişlik | Genişlik (mm) | İçeriğin gerçek genişliği |
| Yükseklik | Yükseklik (mm) | İçeriğin gerçek yüksekliği |
| Oran | En/boy oranını koru | Varsayılan açık |
| Çözünürlük | Çözünürlük (DPI) | Kazıma görüntüsünün piksel yoğunluğu |
| Pitch | Satır aralığı (mm) | DPI ile birlikte değişir. |
| Piksel boyutu | Çıktı boyutu | Örnek: 600 × 360 piksel — 30 × 18 mm |
| Yuvarlama | Çıktı tuvali | Seçilen çözünürlük nedeniyle sağda veya altta çok küçük bir boşluk eklenebilir. |
| Eşik | Siyah-beyaz eşiği | Önizlemede siyah görünen alanlar kazınacaktır. |
| Negatif | Siyah ve beyazı ters çevir | Yalnız seçili alan içinde uygulanır. |
| Ayna | Yatay ayna / Dikey ayna | Bütün geçişlere aynı şekilde uygulanır. |
| Döndür | 90° döndür | Bölme işleminden önce görüntüyü döndürür. |
| Hazırla | Geçişleri hazırla | Ana görüntüyü ve geçişleri günceller. |

Dosya filtresi biçimleri tek tek listeler. “Her dosya biçimi desteklenir” yazılmaz. Ölçü metadata'dan önerildiyse `Dosyadan alınan ölçü`; metadata yoksa `508 DPI üzerinden önerilen ölçü` açıklaması gösterilir. Kullanıcı ölçüyü değiştirebilir.

## Interlace

| Alan | Varsayılan | Yardım |
|---|---|---|
| Satır serpiştirme (Interlace) | 3 | 1 = kapalı. Görüntüyü birbirini tamamlayan satır gruplarına ayırır. |
| Geçiş sırası | Ardışık | Seçenekler: Ardışık / Karışık |
| Karışık yardım | — | Tekrarlanabilir bir sıra kullanır. Her satır tur başına bir kez işlenir. |
| Çift yönlü tarama | Açık | Gerçek satır hareketlerini LightBurn hesaplar. |
| Lazer spot çapı (mm) | Bilinmiyor | Girilirse satır aralığıyla karşılaştırılır. |
| Toplam tur sayısı | 1 | Her tur bütün geçişleri bir kez tamamlar. |
| Her turda geçiş sırasını değiştir | Kapalı | Sonraki tur farklı ve tekrarlanabilir bir grup sırası kullanır. |
| Geçişler arası bekleme (ms) | 0 | İş içeren geçişler arasında uygulanır. |

Son üç kontrol planlama/kayıt için açık; gerçek yürütüm ancak V4 ve doğrulanmış profil desteğiyle sağlanır. Kaydedilmiş desteklenmeyen değer okunur ve gösterilir; 0/1'e sıfırlanmaz. Kullanıcı bu ayarla export yapamayacağını aynı panelde görür.

## Önizleme

Sekmeler: `Kaynak`, `Kazıma görüntüsü`, `Tek geçiş`, `Birleşik görünüm`.

Geçiş listesi sütunları: `Tur`, `Geçiş`, `Grup`, `Kazınacak satır`, `Durum`. Teknik grup kimliği 0 tabanlıdır; kullanıcıya görünen geçiş/sayfa numarası 1 tabanlıdır. Satır yakınlaştırmasında etiket `Satır indeksi (0 tabanlı)` olmalıdır.

Örnek özet: `3 geçiş · 1 tur · 30 × 18 mm · 508 DPI`. Örnek boş durum: `Geçiş 2 boş — işlenmeyecek`. Renkler sadece grupları anlatır; asıl export görüntüleri siyah-beyazdır.

Bilgi notu aynen: **Satır aralığı spot çapından küçük, serpiştirmenin soğutma etkisi sınırlı olabilir.**

Süre metinleri: `Ek bekleme: {ms} ms`; `Toplam süre: LightBurn önizlemesinde hesaplanacak`. Profile göre henüz doğrulanmayan yön/atlama animasyonu gerçek makine yolu gibi oynatılmaz.

## Kayıt ve dışa aktarma

- `İşi kaydet…`
- `İşi aç…`
- `Geçişleri PNG olarak kaydet…`
- `LightBurn projesi olarak dışa aktar…`
- `LightBurn profili`
- `Lazer ayarları`
- Başarı: `LightBurn projesi kaydedildi. {count} etkin geçiş, {width} × {height} mm.`
- Dosyayı açma yardımı: `Katman ve işlem ayarlarını yüklemek için LightBurn'de Dosya → Aç kullanın.`

## Hata ve durum karşılıkları

| Kod | Metin |
|---|---|
| `UNSUPPORTED_SOURCE_FORMAT` | Bu dosya biçimi desteklenmiyor. PNG, JPEG, BMP, TIFF, WebP, GIF, SVG veya PDF seçin. |
| `SOURCE_TOO_LARGE` | Dosya bu işlem için belirlenen boyut sınırını aşıyor. |
| `RASTER_LIMIT_EXCEEDED` | Bu ölçü ve DPI çok büyük bir görüntü oluşturuyor. Ölçüyü veya DPI'ı azaltın. |
| `SOURCE_DECODE_FAILED` | Görsel okunamadı. Dosyanın geçerli olduğundan emin olun. |
| `SVG_EXTERNAL_RESOURCE` | SVG harici dosyalara bağlı. Görselleri SVG içine gömerek yeniden kaydedin. |
| `SVG_UNSUPPORTED_FEATURE` | SVG'deki bazı öğeler bu sürümde işlenemiyor: {features}. |
| `FONT_MISSING` | Çizimde kullanılan yazı tipi bulunamadı: {font}. Yazı tipini kurun veya metni yola dönüştürün. |
| `PDF_UNAVAILABLE` | Bu kurulumda PDF içe aktarma bileşeni bulunmuyor. |
| `PDF_PASSWORD_REQUIRED` | Bu PDF parola korumalı. Parolasız bir kopya seçin. |
| `PAGE_OUT_OF_RANGE` | Seçilen sayfa veya kare dosyada bulunmuyor. |
| `INVALID_GRID` | Ölçü ve DPI pozitif, geçerli sayılar olmalıdır. |
| `INVALID_INTERLACE_COUNT` | Serpiştirme sayısı 1 ile 8 arasında tam sayı olmalıdır. |
| `EMPTY_MASK` | Kazınacak siyah alan bulunmuyor. Eşik ve ters renk ayarlarını kontrol edin. |
| `RECIPE_VERSION_UNSUPPORTED` | Bu iş dosyasının sürümü desteklenmiyor. Dosya değiştirilmedi. |
| `RECIPE_CORRUPT` | İş dosyasındaki görüntü veya ayarlar doğrulanamadı. |
| `PLAN_STALE` | Ayarlar değişti. Dışa aktarmadan önce geçişleri yeniden hazırlayın. |
| `LASER_RECIPE_REQUIRED` | Dışa aktarmak için lazer ayarlarını veya bir LightBurn şablonunu seçin. |
| `LIGHTBURN_PROFILE_UNVERIFIED` | Bu LightBurn sürümü ve cihaz profili için dışa aktarma henüz doğrulanmadı. |
| `LIGHTBURN_LAYER_LIMIT` | Seçilen tur ve geçiş sayısı, bu profil için doğrulanmış katman sınırını aşıyor. |
| `LIGHTBURN_OPTION_UNSUPPORTED` | Seçilen profil şu ayarı uygulayamıyor: {option}. İş ayarınız korunuyor. |
| `CANCELLED` | İşlem iptal edildi. |

Çalışan ekranın kesin metinleri `ui/visual_interlace_panel.py`, `visual_preview.py`, `visual_errors.py` içindedir. Menü: Görsel satır serpiştirme. Çalışan butonlar: Resim / SVG / PDF aç…, Maskeyi hazırla, Önizlemeyi yakınlaştır…, İşi JSON olarak kaydet…, JSON işi aç…, Geçiş PNG paketini kaydet…, MikroCAM projesine ekle, Projedeki görsel işi aç. Native LightBurn butonu profil bekleme açıklamasıyla kapalıdır.
