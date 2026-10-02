# Görsel içe aktarma ve LightBurn interlace mimarisi

Tarih: 2026-10-02. Durum: Evo hedefinde V1/V2 uygulandı; yerel final doğrulama PASS. Native LightBurn V3 ve V4 yürütümü G02 profil kanıtını bekliyor.

MikroCAM, yaygın resim dosyalarını, SVG çizimlerini ve seçilen PDF sayfasını gerçek ölçekte bir kazıma maskesine dönüştürecek. Bu maskenin satırlarını N tamamlayıcı görüntüye dağıtacak ve görüntüleri aynı konum ve boyutta ayrı Image katmanlarına yerleştiren bir LightBurn projesi üretecek. KiCad veya Gerber zorunlu değildir.

**Asıl teslim ölçütü, hedef LightBurn sürümünde doğrulanmış tek bir `.lbrn2` dosyasıdır.** PNG dosyaları ve MikroCAM iş kaydı ayrıca yararlıdır; `.lbrn2` tesliminin yerine geçmez.

## Uygulamaya başlayacak modelin okuma sırası

1. [Spec](spec.md): kapsam, terimler, gereksinimler ve değişmezler.
2. [Plan ve mimari](plan.md): paketler, bağımlılıklar ve veri akışı.
3. [Veri modeli](data-model.md): alan adları, birimler, koordinatlar ve kayıt sözleşmesi.
4. [API sözleşmeleri](contracts/api.md): fonksiyonların girdi, çıktı ve hata davranışları.
5. [LightBurn sözleşmesi](lightburn-contract.md): gerçek uygulamada doğrulanacak export davranışı.
6. [Görevler](tasks.md): küçük feature dilimleri, sıralama ve tamamlanma koşulları.
7. [Test matrisi](validation.md) ve [örnekler](contracts/reference-cases.json).
8. [Türkçe ekran metinleri](ui-tr.md).
9. [Araştırma ve kanıt](research.md): doğrulanmış bilgiler ve açık uyumluluk soruları.
10. [Uygulayıcıya devir](handoff.md): başka bir modele verilebilecek başlangıç talimatı.
11. [Tutarlılık incelemesi](analysis.md): doğrulama sonuçları ve teslim edilen dosyaların tam listesi.

## Hedef depo

Uygulama `E:/VSCode/Flatcam/MikroCAM-visual-interlace`, dal `032-visual-interlace`,
base `c5a666cf` içindedir. `E:/VSCode/Flatcam/flatcam` altın referansı değiştirilmedi.
Mevcut Placement ve LaserRecipe kullanılır. Poligon LaserJob değiştirilmeden raster
`VisualInterlaceJob` eklenmiştir. [Gerçek girişler](target-integration.md),
[kullanım](../../visual-interlace.md), [teslim ve dosyalar](implementation.md).

032–035 numaraları bu hedefteki spec-kit dilimleridir; tek entegrasyon worktree'sinde
uygulanırlar. Merkezi durum dosyası `E:/VSCode/Flatcam/MikroCAM/docs/IS_TAKIP.md`;
worktree'de ayrı takip kopyası yoktur. İşaretlenmemiş native görevler tamamlanmış sayılmaz.

## Karar özeti

| Konu | Karar |
|---|---|
| Temel kaynaklar | PNG, JPEG, BMP, TIFF, WebP, GIF; SVG; PDF'den tek sayfa |
| Çok sayfalı dosya | PDF/TIFF sayfa veya kare seçimi; bir işte bir sayfa |
| Animasyon | GIF/WebP için seçilen tek kare; animasyon kazıma yok |
| Ortak veri | `bool[H,W]`, `True = kazınacak`, `False = boş` |
| Interlace | N=1..8, yeni işte 3; eski kayıtta alan yoksa 1 |
| Çıktı boyutu | Her parça aynı W×H ve aynı mm boyutunda |
| Çözünürlük | `pitch_mm = 25.4 / dpi`; N ile değiştirilmez |
| Resim işleme | Önce tek kez dönüştür/eşikle, sonra satırlara ayır |
| LightBurn | Pass-Through, ayrı Image katmanları, katmana göre sıra; profil başına doğrulama |
| PDF | Temel sayfa rasterleştirme ilk kapsamda; vektör çıkarma ve OCR ayrı iş |
| Gerber | İsteğe bağlı ek kaynak; görsel akışını bloke etmez |
| Gelişmiş kontroller | Tur, sıra değişimi, bekleme V4; desteklenmeyen ayar sessizce atılmaz |

## Uçtan uca örnek

600×360 piksellik 1-bit kaynak, 508 DPI ve N=3 için üç adet 600×360 görüntü çıkar. Her görüntü 30×18 mm olur. Parçalar sırasıyla `0,3,6,...`, `1,4,7,...`, `2,5,8,...` satırlarını taşır. Siyah piksellerin birleşimi kaynağa eşittir; hiçbir siyah piksel aynı tur içinde iki kez bulunmaz.

## Aşamalar

| Dilim | Kullanıcıya sağladığı sonuç |
|---|---|
| V1 `visual-mask-interlace` | Bitmap açma, ölçülendirme, bölme, önizleme ve taşınabilir iş kaydı |
| V2 `visual-svg-pdf` | Aynı iş akışında SVG ve PDF sayfası açma |
| V3 `lightburn-image-project` | Hedef uygulamada doğrulanmış `.lbrn2` dışa aktarma |
| V4 `interlace-cycle-controls` | Doğrulanmış kapasite içinde tam tur, tur sırası ve bekleme |

LightBurn formatını doğrulayan keşif görevi G02, V1'den önce başlar. V3 riskini bütün arayüz yazıldıktan sonraya bırakmayın. İlk kullanılabilir ana ürün V1+V2+V3'tür; V4 özgün isteğin opsiyonel kontrollerini tamamlar.

## Son kaynak ve uyumluluk hazırlığı

[75 crate kaynak notice kanıtı](notice-audit.md) ve
[10 LightBurn keşif örneği](../../examples/visual-interlace/lightburn-discovery/README.md) hazır.
Keşif seti PNG/JSON içerir; gerçek `.lbrn2` fixture veya native PASS değildir.
