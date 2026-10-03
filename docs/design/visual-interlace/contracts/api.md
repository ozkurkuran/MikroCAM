# Fonksiyon ve hata sözleşmeleri

V1/V2 imzaları çalışan API özetidir; LightBurn imzaları G02 sonrası uygulanacak hedeftir. Opsiyonel cancellation/provenance parametreleri için kaynak type hint'lerini esas alın. Dataclass tanımları [veri modelindedir](../data-model.md). Bağımlılık yönleri [plan.md](../plan.md) ile uyumlu kalmalıdır.

## Kaynak sınırı

```python
# mikrocam/bridge/visual_bitmap.py
def inspect_bitmap(data: bytes, page_index: int = 0) -> SourceInfo: ...
def render_bitmap(source: SourceAsset, preparation: PreparationSettings,
                  grid: RasterGrid) -> RasterFrame: ...

# mikrocam/bridge/visual_svg.py
def inspect_svg(data: bytes) -> SourceInfo: ...
def render_svg(source: SourceAsset, preparation: PreparationSettings,
               grid: RasterGrid) -> RasterFrame: ...

# mikrocam/ui/visual_pdf.py
def inspect_pdf(data: bytes, page_index: int = 0) -> SourceInfo: ...
def render_pdf_page(source: SourceAsset, preparation: PreparationSettings,
                    grid: RasterGrid) -> RasterFrame: ...
```

Kaynak render fonksiyonları eşikleme veya interlace yapmaz. Seçilmiş kaynak viewport'u tek ortak grid'e örnekler; gerekli crop/ayna/90° dönüşü uygular. Ortak dönüşüm matematiği `core/placement.py` üzerinden kullanılır; her importer kendi koordinat convention'ını icat etmez. PNG/JPEG decoder doğru ölçeği tahmin etmez; `PreparationSettings` çözülmüş mm ölçülerini taşır.

İnceleme hatalı/eksik kaynakta exception verir. Bitmap decompression-bomb uyarısını yok sayma. SVG'de DTD/entity, ağ referansı, harici dosya referansı ve dinamik içerik kabul edilmez. Gömülü data URI rasterları boyut kontrolüyle kabul edilir; başka SVG'ye dış `use` referansı reddedilir. Font eksikliği tespit edilirse açık kullanıcı işlemi gerekir: fontu sağla veya metni path'e dönüştür.

PDF ilk kapsamda şifresiz dokümandır. Şifreli PDF için `PDF_PASSWORD_REQUIRED`; parola kırma veya sessiz boş sayfa yoktur. `page_index` yüklenen belgenin aralığında olmalıdır. Görüntülenen sayfa ile rasterlenen sayfa aynı olmalıdır; page rotation iki kez uygulanmaz.

## Saf çekirdek ve alan fonksiyonları

```python
# mikrocam/core/visual.py
def build_grid(preparation: PreparationSettings) -> RasterGrid: ...

# mikrocam/core/visual_normalize.py
def make_burn_mask(frame: RasterFrame,
                   preparation: PreparationSettings) -> BurnMask: ...

# mikrocam/core/visual_interlace.py (+ build_plan: mikrocam/laser/visual_plan.py)
def partition_rows(height: int, count: int) -> tuple[range, ...]: ...
def base_order(count: int, mode: str) -> tuple[int, ...]: ...
def source_row_direction(row_index: int) -> str: ...
def build_plan(mask: BurnMask, settings: InterlaceSettings,
               revision: int) -> InterlacePlan: ...
def materialize_group(mask: BurnMask, group_index: int,
                      count: int) -> BurnMask: ...
```

`partition_rows(10,3)` tuple olarak `range(0,10,3)`, `range(1,10,3)`, `range(2,10,3)` verir. `height=0` için N boş range geçerlidir. Negatif H, bool N, kesirli N, N<1 veya N>8 hatadır. `source_row_direction(0)="left_to_right"`, `(1)="right_to_left"`; geçiş numarası veya etkin satır sırası argümanı yoktur.

`materialize_group` girdiyi değiştirmez. Yeni False maske oluşturup `out[k::N] = source[k::N]` yapar. N=1'de pixel-identical salt okunur view veya kopya dönebilir; memory ownership davranışı test edilir. Grid ve placement değişmez. Boş satırlara rağmen orijinal indeksler kullanılır.

Planlama O(H+R*N), grup materialization O(W*H) olabilir. Sadece indeksleri elde etmek için W*H piksel veya N maske oluşturulmaz. Boş satır sayımı ana maskede bir kez yapılır; R tur için tekrar piksel taraması yapılmaz.

## Codec, kayıt ve export

```python
# mikrocam/bridge/visual_png.py
def encode_mask_png(mask: BurnMask) -> bytes: ...
def decode_mask_png(data: bytes, grid: RasterGrid) -> BurnMask: ...

# mikrocam/bridge/visual_recipe.py
def save_visual_recipe(job: VisualInterlaceJob, destination: Path) -> None: ...
def load_visual_recipe(source: Path) -> VisualInterlaceJob: ...

# mikrocam/laser/lightburn_export.py
def validate_export(job: VisualInterlaceJob, plan: InterlacePlan,
                    profile: LightBurnProfile) -> tuple[Issue, ...]: ...
def export_lightburn(job: VisualInterlaceJob, plan: InterlacePlan,
                     profile: LightBurnProfile, destination: Path) -> ExportReport: ...
```

PNG kayıpsız ve gerçek iki değerli olmalı; dosya boyutu veya PNG byte eşitliği test edilmez. LightBurn'ün gömülü bitmap biçimi 1-bit PNG kabul etmiyorsa G02 kanıtıyla 0/255 değerli 8-bit PNG kullanılabilir; mantıksal piksel eşitliği aynı kalır. Recipe ana maskesi için kanonik codec 1-bit PNG'dir.

Exporter sadece `.lbrn2` yazar; LightBurn'ü açıp işi başlatmaz, UDP/USB/serial komutu göndermez. Destination yanında benzersiz geçici dosyaya yazar, XML/gömülü bitmap/katman referanslarını doğrular, başarıda atomik replace yapar. Hata veya iptal önceki destination'ı değiştirmez. Yalnız kendi oluşturduğu geçici dosyayı temizler.

## Bridge orkestrasyonu

```python
# mikrocam/bridge/visual_workflow.py
def prepare_visual_job(source: SourceAsset,
                       preparation: PreparationSettings,
                       interlace: InterlaceSettings,
                       placement: Placement,
                       laser_recipe: LaserRecipe | None,
                       revision: int) -> VisualInterlaceJob: ...
```

Bridge formatı seçer, importer/Qt PDF adapter'ını çağırır, maskeyi ve planı alan fonksiyonlarına üretir. Worker cancellation/revision kontrolü burada yapılır. UI içine threshold, bit tersleme, birim dönüşümü veya XML mantığı yazılmaz.

## Hata kodları

Native exporter hedefindeki `Issue` alanları: `code`, `severity` (`info`, `warning`, `error`), `params`. Core/alan Türkçe metin üretmez; UI kodu [metin tablosuna](../ui-tr.md) bağlar.

| Kod | Sonuç |
|---|---|
| `UNSUPPORTED_SOURCE_FORMAT` | Kaynak açılmaz; mevcut iş korunur |
| `SOURCE_TOO_LARGE` / `RASTER_LIMIT_EXCEEDED` | Decode/render başlamaz |
| `SOURCE_DECODE_FAILED` | Boş görüntüyle başarı döndürülmez |
| `SVG_EXTERNAL_RESOURCE` / `SVG_UNSUPPORTED_FEATURE` | Kaynağı düzeltmeden üretim maskesi yapılmaz |
| `FONT_MISSING` | Görünümü değiştirecek font ikamesi sessiz yapılmaz |
| `PDF_UNAVAILABLE` / `PDF_PASSWORD_REQUIRED` / `PAGE_OUT_OF_RANGE` | İlgili kaynak açılmaz |
| `INVALID_GRID` / `INVALID_INTERLACE_COUNT` | Plan yapılmaz |
| `EMPTY_MASK` | Önizleme/kayıt serbest, LightBurn export kapalı |
| `RECIPE_VERSION_UNSUPPORTED` / `RECIPE_CORRUPT` | Dosya yazılmadan hata; otomatik onarım yok |
| `PLAN_STALE` | Plan yeniden üretilecek; eski revizyon export edilmez |
| `LASER_RECIPE_REQUIRED` | Güç/hız/device ayarları uydurulmaz |
| `LIGHTBURN_PROFILE_UNVERIFIED` | Native export yapılamaz; PNG/recipe mümkün |
| `LIGHTBURN_LAYER_LIMIT` | Tur veya N azaltılması gerekir; katmanlar birleştirilmez |
| `LIGHTBURN_OPTION_UNSUPPORTED` | İstenen bekleme/yön/sıra kaybedilmez; export reddedilir |
| `PITCH_BELOW_SPOT` | Bilgi notu; işlemi engellemez |
| `CANCELLED` | Önceki iş/dosya değişmeden kalır |

Çalışan source/recipe sınırı `ValueError(CODE + details)` ile hatayı bildirir; UI Türkçe karşılığı ve tooltip tanısını gösterir. Native Issue/ExportReport henüz kodda yoktur. SVG/PDF crop `CROP_UNSUPPORTED`; PNG paket exporter `bridge/visual_export.export_png_package(job, plan, destination, cancelled=None)` olup `.lbrn2` değildir. PDF frame/provenance UI worker'da üretilip detached workflow'a verilir.
