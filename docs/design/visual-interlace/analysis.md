# Spec/plan/task tutarlılık incelemesi

2026-10-02. İlk plan13belgesi hedef Evo'ya uyarlandı. G01gerçek API tamamlandı;
V1/V2 yerel kod, G02/V3native ve V4native ayrı durumdadır. Uygulayıcı model
`implementation.md` + `target-integration.md` okuyup mevcut kodu yeniden yazmamalı.

24FR,40T ve40task:2ortak+13V1+10V2+8V3+7V4. Dört feature032–035,
her biri3story ve≤40 task. Scoped spec'ler shared davranış sözleşmesine link verir;
katman/API gerçek kod yollarıdır. Yanlış QtPdf bridge ve NumPy domain varsayımları
hedef import guard'ına göre düzeltildi. Yeni generic layer/registry/host object yok.

## İnceleme sonucu

- Bitmap/SVG/PDF bağımsız, Gerber isteğe bağlı; aynı raster split.
- SameW/H/pitch/placement, piksel birleşimi ve kaynak satır paritesi helper testli.
- Immutable arrays gerçek bytes-owned; writes tekrar açılamaz; hash tutarlı.
- Downsample group kaybetmez; zoom thumbnail'ı büyütür, export ana maskeyi kullanır.
- Kaydedilmiş kesin DPI / mm eşik değişikliği sırasında korunur;90degW/H takası testli.
- PNG1 bit/DPI/whitepadding, JSONhash/schema/migration, actualhost project roundtrip testli.
- Pixelalgorithm ile LightBurn native tarama/skip/direction ayrılır; G02atlamaz.
- Tam tur repeat ile katman tekrarı ayrılır; dwell request native uygulanmış sayılmaz.
- Kaynak ve statik bağımlılık license metadata kayıtlı; binaryrelease audit gap açık.
- B01/B10binary proof ve V3/V4native alt koşulları checkbox'ta açık bırakıldı.

Modül/fonksiyon boyutları ve publictypehint kontrolü son `8fef` kaynağı'ta PASS.
Full regression önce eec5source5744/310 PASS; son API full PASS.
Native gerçek uygulama menu+source+JSON+project+OpenGL+normalshutdown sonAPI'de PASS.
Diğer kaynağa ait eski sonuçlar validation geçmişiyle ayrılır; CI/main teslimi NOT_RUN.
Whitespace incelemesinde noticeinventory'nin mevcut CRLF biçimi korunur;
`git -c core.whitespace=cr-at-eol diff --check` authoredchanges için kullanılır.

## Teslim dosyaları

[Kesin değişen dosya listesi](implementation.md), [kullanım](../../visual-interlace.md),
[40kabul matrisi](validation.md), [görevler](tasks.md), [nativekontrat](lightburn-contract.md),
[uyumluluk](../../lightburn-compatibility.md), [modeldevir](handoff.md).
Altın referans ve ilgisiz main/kullanıcı takip kayıtları değiştirilmedi.

Son full5744test/310alt test PASS509.30s,3skip/11existing warning; son API native PASSexit0. Doküman bağlantı/fence kontrolü PASS; code/config fingerprint `8fefc0d0bccc6c5b1c29aa219a595f0c5047d262569eb7200c24738cbbdb3c8c`. G02/V3 ve V4native açık kaldı.
