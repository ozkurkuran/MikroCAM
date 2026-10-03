# Görsel iş veri modeli

V1/V2 tipleri çalışan Python dataclass'larıdır; LightBurnProfile/ExportReport V3 tasarım hedefidir. Public API type hint taşır. JSON anahtarları ve kod isimleri İngilizcedir. İç uzunluk birimi mm, zaman birimi bu payload içinde tam sayı ms'dir. Modeller Qt veya Pillow nesnesi tutmaz.

## SourceAsset ve SourceInfo

| Alan | Tip | Kural |
|---|---|---|
| `kind` | enum | `bitmap`, `svg`, `pdf`, `geometry_snapshot` |
| `name` | str | Görüntülenecek dosya adı; exportta mutlak yerel yol yazılmaz |
| `media_type` | str | Gerçek dosya içeriğiyle doğrulanır |
| `data` | bytes | Açılan dosyanın değişmez snapshot'ı |
| `sha256` | str | Kaynak byte'larının hash'i |
| `page_index` | int | 0 tabanlı; tek görüntüde 0; PDF/TIFF/GIF/WebP seçiminde açık |
| `page_count` | int | İnceleme sonucunda bulunan toplam |
| `native_size_px` | tuple[int,int] veya None | EXIF yönü uygulanmış raster boyutu |
| `suggested_size_mm` | tuple[float,float] veya None | SVG/PDF fiziksel ölçü; bitmap DPI yalnız öneri |
| `size_origin` | enum | `document`, `metadata`, `user`, `default_508dpi` |
| `import_notes` | tuple[str,...] | Eksik font, yorumlanan ölçü vb. |

Recipe içinde `data` yerine `data_base64` saklanır. Kaynağın ilk açıldığı yol sadece oturum bilgisi olabilir; dosyanın yeniden açılmasının önkoşulu değildir. `geometry_snapshot`, legacy nesneye pointer içermez; şeklin o andaki kendi kendine yeterli SVG snapshot'ını taşır.

## PreparationSettings

| Alan | Tip / varsayılan | Açıklama |
|---|---|---|
| `requested_dpi` | float / 508.0 | Son tarama grid'inin çözünürlüğü; pozitif ve sonlu |
| `requested_width_mm` | float | Pozitif; girilen gerçek içerik/viewport genişliği |
| `requested_height_mm` | float | Pozitif; girilen gerçek içerik/viewport yüksekliği |
| UI en/boy oranı | Kaydın alanı değil | Panel kaynak oranını korur; model kesin W/H taşır |
| `threshold` | int / 128 | 1..255; gri değer `< threshold` ise kazınacak |
| `invert` | bool / False | Geçerli içerik alanında siyah/beyazı çevir |
| `mirror_x`, `mirror_y` | bool / False | Bölmeden önce ana görüntüye uygulanır |
| `quarter_turns` | int / 0 | İlk sürümde 0,1,2,3; saat yönünde 90° katları |
| `crop_rect` | tuple[float,float,float,float] veya None | Bitmap için EXIF sonrası piksel dikdörtgeni; SVG/PDF non-null değeri reddeder; ilk UI bütün sayfa |
| `normalization_version` | int / 1 | Eşik, alpha ve gri dönüşüm kurallarının sürümü |

Serbest açılı dönüşüm, otomatik kenar kırpma ve her parçayı farklı boyutlandırma ilk sürümde yoktur. 90° dönüş nihai boyut hesabından önce uygulanır; kaynak yönü ile son grid yönü birbirine karıştırılmaz.

## RasterGrid ve koordinat sözleşmesi

```text
pitch_mm = 25.4 / requested_dpi
W = ceil(requested_width_mm / pitch_mm)
H = ceil(requested_height_mm / pitch_mm)
canvas_width_mm = W * pitch_mm
canvas_height_mm = H * pitch_mm
```

Hesaplarda DPI ve istenen ölçülerin ondalık gösterimini `Decimal(str(value))` ile kullan; `ceil` sırasında ikili kayan nokta hatası yüzünden tam 600 yerine 601 üretme. JSON'da sonlu sayılar saklanır; yazımda anlamlı hassasiyet kaybedilmez. Hesaplanan W,H,pitch,canvas boyutu da kayıt içinde bulunur ve yüklemede tutarlılık kontrolünden geçer.

**Yuvarlama kararı:** İçeriği en yakın piksel sayısına sığdırmak için esnetme. Grid'i yukarı yuvarla; içerik viewport'unu sol üste hizala; sağda/altta her eksende bir pikselden küçük ek tuval kalabilir. Kullanıcıya içerik ölçüsü ve çıktı tuvali ölçüsü ayrı gösterilir. Piksel merkezleri istenen viewport dışında ise `valid_area=False`; bu pikseller ters renk açıkken de beyaz kalır. Bu örnekleme kuralı kenarda alt piksel ayrıntısını koruma garantisi vermez; grid çözünürlüğünün doğal sınırıdır.

Raster boyutu grid ile aynıysa ve dönüşüm/eşik durumu uygun ise yeniden örnekleme yapma. 1-bit bitmap ölçeklenmek zorundaysa nearest-neighbor; gri/RGB raster için LANCZOS örnekleme, ardından tek eşikleme. SVG/PDF doğrudan hedef fiziksel viewport'a render edilir; padding viewport'u büyütüp çizimi esnetmek için kullanılmaz. Qt PDF `render` boyutundaki tam sayı yuvarlaması hedef viewport'a ortak örnekleme dönüşümüyle bağlanır; bu fark için 30×18 ve tam piksele bölünmeyen sayfa testleri gerekir.

Yerel üretim koordinatı `x` sağa, `y` yukarıdır; canvas sol alt köşesi (0,0):

```text
pixel_center_x(c) = (c + 0.5) * pitch_mm
pixel_center_y(r) = (H - r - 0.5) * pitch_mm
machine_point = shared_placement(local_point)
```

Array satır 0 üsttedir. Mirror ve quarter-turn içerik hazırlamada bir kez uygulanır; son satır indeksi bu ana maske üzerinde tanımlanır. Yerleşim konumu bütün geçişlerde aynıdır. İlk raster exporter yalnız ortak placement'ın öteleme durumunu kabul eder; bake edilmemiş ölçek/dönüş varsa açıkça reddeder. Böylece LightBurn'e eklenen bir transform DPI eşleşmesini sessizce değiştiremez.

## RasterFrame ve BurnMask

`RasterFrame`: `rgba: uint8[H,W,4]`, `grid: RasterGrid`, `valid_area: bool[H,W]`. Kaynak biçimine özel nesne taşımaz. Diziler C-contiguous ve sahipliği belirlenmiş kopyalardır; model oluşturulduktan sonra read-only yapılır.

Normalize etme sırası:

1. Kaynak orientation, kare/sayfa seçimi ve geometrik hazırlama.
2. Alpha'yı beyaz üzerine birleştir: kanal başına `(C*A + 255*(255-A) + 127)//255`. Ara hesap en az uint32.
3. Gri değer: `(299*R + 587*G + 114*B + 500)//1000`.
4. `burn = gray < threshold`.
5. `invert` ise burn'u mantıksal tersle; sonra `burn &= valid_area`.

Renk profili varsa bitmap adaptörü kaynağı sRGB'ye dönüştürür; profil yoksa sRGB varsayımını kaydeder. Aynı kaynaktan tekrar render farklı font/renk kütüphanesiyle değişebilir; kaydedilmiş ana maske otomatik yeniden oluşturulmaz.

`BurnMask`: `burn: bool[H,W]`, `grid`, `sha256`, `black_pixel_count`. True kazıma anlamındadır. Hash girdisi tam olarak `b"MCAM-MASK-1\0" + struct.pack(">II", W, H) + np.packbits(burn, axis=None, bitorder="big").tobytes()` olur; satır-major sıra ve son byte'ta sıfır doldurma bitleri kullanılır. PNG encode sırasında True=0, False=255; byte'lara doğrudan OR yapmak yanlıştır. Hash, maskeyi fiziksel grid ile eşleştiren plan kontrolünün yerini tutmaz; aynı pikseller farklı pitch'te farklı iş revizyonudur.

## InterlaceSettings ve plan

| Alan | Varsayılan | Kural |
|---|---|---|
| `count` | 3 | int 1..8; eski kayıtta yoksa 1 |
| `order_mode` | `sequential` | `sequential` veya `mixed` |
| `order_algorithm` | `bit_reverse_v1` | Mixed algoritmasının kalıcı sürümü |
| `round_count` | 1 | int 1..999 |
| `vary_order_each_round` | False | Grup kimliklerine tur indeksi ekleyip mod N alma |
| `delay_ms` | 0 | int 0..600000 |
| `bidirectional` | True | LightBurn tarama tercihi |
| `direction_policy` | `lightburn_managed` | Katı alternatif `source_row_parity` profil gerektirir |
| `spot_diameter_mm` | None | Varsa pozitif; sadece bilgi notu hesabı |
| `effective_orders` | türetilir | Her tur için uzunluğu N olan permütasyon; kayıtta da saklanır |

`InterlacePass`: `round_index`, `sequence_index`, `group_index`, `row_start=group_index`, `row_step=N`, `row_stop=H`, `active_row_count`, `black_pixel_count`, `enabled`, `delay_before_ms`.

`row_start/step/stop` bütün teorik satırları temsil eder; boş satır listesi ayrıca yeniden numaralandırılmaz. `enabled` siyah piksel sayısı >0 ise True. İlk etkin geçişte `delay_before_ms=0`, sonraki etkin geçişlerde ayarlı delay. Boş geçişlerde 0. N maskeyi veya her satır için kopya piksel verisini plana koyma.

`InterlacePlan`: ana maske hash'i, settings, immutable geçiş tuple'ı, revizyon ve özet sayılar. Plan ile maske hash'i eşleşmiyorsa export hata verir.

## Mixed sıra tablosu

| N | Temel sıra |
|---|---|
| 1 | 0 |
| 2 | 0,1 |
| 3 | 0,2,1 |
| 4 | 0,2,1,3 |
| 5 | 0,4,2,1,3 |
| 6 | 0,4,2,1,5,3 |
| 7 | 0,4,2,6,1,5,3 |
| 8 | 0,4,2,6,1,5,3,7 |

Rastgele sayı üreticisi veya seed gerekmez. Tablonun ve algoritmanın aynı sonucu verdiği test edilir.

## VisualInterlaceJob ve JSON recipe

`VisualInterlaceJob`: `source`, `preparation`, `mask`, `interlace`, `placement`, `laser_recipe`, `revision`, `renderer_name`, `renderer_version`. `laser_recipe` mevcut LaserJob recipe tipidir; yoksa export için eksik parametre sonucu verilir. Fiziksel hız mm/s, güç yüzde, frekans kHz, pulse ns olarak normalize edilir; cihaz için geçerli aralıklar kullanıcı profilinden gelir, bu belge güç değeri önermez.

Kalıcı payload anahtarları:

```text
schema_version: 1
kind: "visual_interlace"
source: {name, data_base64, sha256, page_index, info: {...SourceInfo}}
preparation: {...PreparationSettings}
grid: {width_px, height_px, pitch_mm, canvas_width_mm, canvas_height_mm,
       requested_width_mm, requested_height_mm, requested_dpi}
mask: {encoding: "png-1bit", data_base64, sha256, black_pixel_count}
interlace: {...InterlaceSettings, effective_orders}
placement: <mevcut Placement dataclass alanları; üst payload schema1>
laser_recipe: <mevcut LaserJob recipe payload'ı veya null>
provenance: {normalizer_version, renderer_name, renderer_version}
```

Ana maske ve kaynak dosya gömülüdür; türetilmiş N PNG kayda tekrar eklenmez. PDF'nin seçilmiş sayfasını değiştirebilmek için kaynak PDF bytes saklanır; boyut limiti aşılırsa açık hata, sessiz dış dosya bağlantısı yoktur. Ana maskenin SHA değeri PNG dosya byte hash'i değil, yukarıda tanımlı mantıksal piksel hash'idir.

Yüklemede sürüm, base64 boyutu, dosya hash'i, PNG boyutu, yalnız 0/255 değerleri, grid tutarlılığı ve permütasyonlar doğrulanır. Bozuk maskeden veya kaynak kaybından sessiz yeniden üretim yapılmaz. Yeniden hazırlama kullanıcı ayar değişikliğinin açık sonucudur; orijinal snapshot kullanılır ve provenance güncellenir.

JSON recipe dosyası için ilk okuma limiti 256 MiB'dir. Decode edilmiş kaynak 64 MiB'yi, maskenin W*H değeri 40 milyon pikseli aşamaz. Base64 çözülmeden önce bildirilen/beklenen uzunluk, çözümden sonra gerçek boyut kontrol edilir. Sıkıştırılmış PNG boyutu küçük diye piksel limiti atlanmaz. Kaynak, grid, placement, ayarlar veya recipe değişince `revision` artar; export aynı mask hash'i olsa bile farklı revizyondaki planı kabul etmez.

Eski visual payload'da interlace/count alanı yoksa migration count=1, tur=1, bekleme=0, sıra=sequential yapar. Eski Gerber/CNCJob dosyası zorla visual_interlace tipine dönüştürülmez. Bilinmeyen gelecek şema yazılmadan reddedilir; dosya korunur. Her şema artışı ayrı migration ve eski dosya testi gerektirir.

## LightBurnProfile ve ExportReport

`LightBurnProfile` sabit, sürümlü adapter verisidir; kullanıcı plugin registry'si değildir. Alanlar: `profile_id`, `lightburn_version`, `device_family`, `fixture_digest`, `tested_layer_limit`, `supports_passthrough`, `supports_blank_row_skip`, `supports_source_row_parity`, `supports_interpass_delay`, `supports_cycle_expansion`, `field_mapping_version`.

Profil yetenekleri test kanıtı olmadan True yapılmaz. Tek bir test edilmiş profil ile başlanır; LightBurn sürümü şu anda bilinmediği için bu belgede çalışan profil varmış gibi değer verilmez.

`ExportReport`: sonuç dosyası, aktif/kapalı katman sayıları, mm boyutları, DPI, kullanılan profil, toplam etkin geçiş, toplam istenen bekleme, uyarılar ve doğrulama durumu. Makineye gönderim veya çalışma sonucu içermez.

Çalışan JSON anahtarlarının doğruluk kaynağı [schema1](../../../mikrocam/laser/visual_recipe.schema.json) ve `laser/visual_recipe.py`; runtime hash/grid/permütasyon doğrulaması şemadan daha güçlüdür. Bitmap float/signed32 örnek aralığı desteklenmiyorsa açık hata verir.
