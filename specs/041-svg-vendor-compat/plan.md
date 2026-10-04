# Uygulama Planı: SVG üretici uyumluluğu

**Dal**: `041-svg-vendor-compat` | **Tarih**: 2026-10-04 | **Spec**: [spec.md](spec.md)
**Taban**: `origin/test/vendor-svg-fixtures` (`bb9a886c`, PR #41). PR #41'den sonra birleştirilir.

## Özet
Üç dar sözleşme değişikliği: (1) paylaşılan çevrim dışı DOCTYPE izin listesi, (2) miras alınmayan
`vector-effect` ile kesin `non-scaling-stroke` fiziksel genişliği, (3) 018 daire kanıtında çakışan
uçlu tek alt yol ve eş merkezli poligon pad desteği. Yeni bağımlılık, kalıcı format, UI veya legacy
değişikliği yoktur.

## Teknik bağlam
CPython 3.13, mevcut NumPy/Shapely 2. Testler donanımsız ve ekransızdır. Gerçek fixture'lar PR #41'de
lisans/provenance ile tutulur; yeni gerçek fixture eklenirse aynı kayıt düzeni uygulanır.

## Sözleşme değişiklikleri

### `mikrocam/importers/svg_doctype.py` (yeni, alan katmanı, yalnız stdlib)
- `SVG_PUBLIC_DOCTYPES: tuple[tuple[str, str], ...]` — SVG 1.0 ve 1.1 public/system çiftleri.
- `strip_svg_doctype(text: str) -> str` — önsözdeki tek izinli DOCTYPE'ı aynı uzunlukta boşlukla
  (satır sonları korunarak) siler. Hatalar `ValueError`: iç alt küme/entity, `SYSTEM`'siz public eksik,
  bilinmeyen tanımlayıcı, kök sonrası/ikinci DOCTYPE, herhangi bir kalan `<!ENTITY`/`<!DOCTYPE`.
- Kullanıcılar: `importers.svg_document._parse_xml` ve `importers.cad_svg_source._text` (iki somut
  kullanım; tek doğruluk kaynağı). 020 artık SVG 1.0 DOCTYPE'ını da kabul eder ve sanitize metni ayrıştırır.

### `mikrocam/core/svg_transform.py`
- `non_scaling_stroke_width(width_px: float, matrix: Affine2D) -> float` — kök viewport CSS pikseli
  cinsinden genişliği, `matrix` (kullanıcı→mm) benzerlikse eşdeğer kullanıcı genişliğine
  (`width_px × 25,4/96 / s`) çevirir; değilse `ValueError`. Benzerlik: sütun boyları ve diklik
  göreli 1e-9 içinde.

### `mikrocam/importers/svg_style.py` / `svg_document.py`
- `vector-effect` desteklenmeyenler listesinden çıkar; çözümlenmiş stilde miras alınmayan bir değer
  olarak tutulur (`none` | `non-scaling-stroke`, CSS anahtar sözcüğü büyük/küçük harf duyarsız);
  `inherit` ebeveynin kendi değerini alır; diğer değerler hata.
- `_Traversal._shape`: `non-scaling-stroke` + boyanan, sıfırdan büyük stroke → kök `transform` yoksa
  `SvgPaint.width` eşdeğer kullanıcı genişliğiyle değiştirilir; aksi halde hata. Boyanmayan stroke'ta
  değişiklik yok. Grup, `use` ve kökte etkin değer hata.
- Belge başına en fazla iki bildirim: `non-scaling-stroke` (boyanan sayısı ve kural) ve
  `non-scaling-stroke-unpainted` (etkisiz sayısı).

### `mikrocam/core/svg_drill_circles.py` / `svg_drills.py`
- `COINCIDENT_ENDPOINT_MM = 1e-6`; `_fitted`: tek alt yol kapalı veya uçlar bu tolerans içinde ise
  son nokta başlangıca eşitlenip `fit_closed_circle` çağrılır.
- `_circles` dairesel olmayan beyaz olmayan dolu tek-poligon elemanları `polygon pad` olarak toplar.
  `_pair` önce mevcut dairesel kuralı, yoksa poligon kuralını (ağırlık merkezi ≤0,02 mm, kesin
  içerme ve sınır uzaklığı ≥ r+0,01 mm, en küçük alan) uygular. `unsupported-opening` mesajı iki
  kuralı da anlatır. `DrillReview` ve `DrillCandidate` biçimi değişmez.

## Constitution Check
1. Yeni mantık `mikrocam/` altında ve katman yönüne uygun mu? **Evet.** DOCTYPE ve stil
   `importers`'ta (yalnız stdlib/core), matematik ve drill `core`'da (stdlib/NumPy/Shapely). (I)
2. Legacy'ye yalnız düzeltme/bağlantı mı, +50 altı mı? **Evet**, legacy değişikliği 0 satır. (II)
3. Her soyutlamanın iki kullanımı var mı; bağımlılık gerekçeli mi? **Evet.** `strip_svg_doctype`
   iki importer'da kullanılır; `non_scaling_stroke_width` tek fonksiyondur, soyutlama değildir.
   Yeni bağımlılık yok. (III, VII)
4. Birim/transform/parametre/format tek kaynaktan mı? **Evet.** px→mm 25,4/96 mevcut 016 sabiti;
   DOCTYPE listesi tek modülde; yeni kalıcı format yok. (IV)
5. Testler donanımsız/ekransız ve uygulamadan önce mi? **Evet** (tasks.md T003–T010 önce RED). (V)
6. Makine/lazer davranışı var mı? **Hayır (N/A).** Drill incelemesi yalnız aday listeler; Excellon
   oluşturma 018'deki açık seçim adımında kalır. (VI)
7. Dış kaynaklı kod var mı? **Hayır.** Standart metinleri yalnız okunup bağımsız uygulandı; yeni
   gerçek fixture eklenirse lisans/provenance `THIRD_PARTY_CHANGES.md`'ye işlenir. (VII)
8. En fazla 3 user story / 40 görev? **Evet**, 3 story, 28 görev.

## Proje yapısı
- `mikrocam/importers/svg_doctype.py` (yeni), `svg_document.py`, `svg_style.py`, `cad_svg_source.py`
- `mikrocam/core/svg_transform.py`, `svg_drill_circles.py`, `svg_drills.py`
- `tests/test_svg_doctype.py`, `tests/test_svg_non_scaling_stroke.py`,
  `tests/test_svg_drill_open_circles.py` (yeni); `tests/test_vendor_export_fixtures.py`,
  `tests/test_svg_document.py`, `tests/test_cad_source_svg.py` (bilinçli sözleşme güncellemesi)
- `docs/SVG_IMPORT.md`, `docs/SVG_DRILLS.md`, `docs/CAD_SOURCE.md`, 016/018/019/020 validation notları

## Complexity Tracking
İstisna yok. Bilinçli olarak dışarıda bırakılanlar (sessiz tahmin yerine açık hata): benzerlik
olmayan dönüşümde boyanan non-scaling stroke, kök `transform` ile boyanan non-scaling stroke,
iç alt kümeli DOCTYPE (eski Illustrator entity'leri), SVG Tiny/Basic DOCTYPE. Görsel (033)
`bridge/visual_svg.py` DOCTYPE kuralı bu dilimde değişmez; resvg yolunun ayrı güvenlik değerlendirmesi
gerekir.
