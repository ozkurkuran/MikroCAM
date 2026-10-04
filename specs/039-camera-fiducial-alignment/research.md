# Research — Fiducial hizalama

## R1 Transform tipi
Karar: mevcut `mikrocam.core.placement.Placement`'a opsiyonel `affine` alanı.
Gerekçe: anayasa IV CAM→makine dönüşümünü tek core tip olarak ister ve “ileride
fiducial/affine” bu tipi işaret eder. `matrix`, `apply_point(s)`, `apply_geometry` zaten
Shapely affine katsayılarıyla çalışır; preflight, auto-level, lazer planlayıcı değişmeden
genel affine'i kullanır. Reddedilen: ayrı `AffineTransform` tipi (kopya transform kodu) ve
rijit alanlarla affine'in bileşimi (iki anlam, belirsiz `inverse`).

## R2 Yay sınırları
`motion_bounds` rijit placement için makine uzayındaki ana yönleri kullanıyordu ve
aynalamayı `mirror_x` ile çeviriyordu. Affine altında yay elips olur. Kaynak açısı θ için
X'in ekstremumu `atan2(b, a)` (+π), Y'ninki `atan2(e, d)` (+π) açılarındadır. Bu açılar
kaynak yay süpürmesi üzerindeyse transformlu nokta sınırlara eklenir. Tek genel yol rijit ve
aynalı placement'ları da kapsar; mevcut motion/preflight testleri değişmeden geçer.

## R3 Uydurma (fit)
- Rijit/benzerlik: merkezlenmiş 2B Procrustes; θ = atan2(Σ(dx·my−dy·mx), Σ(dx·mx+dy·my)),
  benzerlik ölçeği s = |S|/Σ|d|². Yansıma içermez.
- Affine: merkezlenmiş tasarım matrisinde `numpy.linalg.lstsq`; ofset = m̄ − L·d̄.
- Doğrusallık: merkezlenmiş tasarım noktalarının tekil değer oranı σ2/σ1.
- Eksen ölçekleri: L'nin tekil değerleri; dönme: en yakın benzerlik açısı atan2(d−b, a+e).
- Artıklar `Placement.apply_point` ile hesaplanır (tek uygulama yolu).
NumPy zaten core bağımlılığıdır; yeni bağımlılık yok.

## R4 Akışa uygulama
`PreparedJob` yalnız öteleme kabul eder; G-code G54 ile değişmeden gönderilir. Dönme/affine
için iki seçenek: (a) G-code'u transformlu koordinatlarla yeniden yazmak, (b) kontrolcü
koordinat dönmesi (GRBL'de yok). (a) seçildi; auto-level zaten aynı yöntemi kullanıyor
(`work_point` = placement − G54). Yaylar affine altında yay kalmadığı için kirişe bölünür.

## R5 Kamera
Kamera yakalama için soyut arayüz yalnız gerçek kamera + fake iki kullanımla eklenebilir
(anayasa III). Gerçek kamera sürücüsü/cihazı ve doğrulaması bu hedefte yok; arayüz eklenmez.
Makine yakalaması mevcut `MachineSnapshot` üzerinden yapılır; kamera ileride aynı
`FiducialPair.machine_mm` alanını dolduracaktır.

## R6 Kalıcı format
`probe_codec`/`laser_json` desenleri: `kind`, `schema_version`, katı alan kümesi, sonlu sayı,
boyut sınırı. Şema 1 ilk sürüm; v1 fixture (tests/test_files/fiducial_set_v1.json) commit'lenir.
