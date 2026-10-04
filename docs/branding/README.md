# MikroCAM marka dosyaları

Bakır PCB izi biçimindeki µ işareti; camgöbeği izolasyon hattı ve lazer noktasıyla birlikte
uygulamanın ortak logosudur. Tasarım mevcut yerel geometri betiğinden üretilir.

| Dosya | Kullanım |
| --- | --- |
| `splash.png` | 720×320 açılış görseli. |
| `splash@2x.png` | 1440×640 sürüm; her iki temanın `splash.png` dosyasına uygulanır. |
| `logo.png` | 1024×1024, köşeleri şeffaf logo. |
| `logo.svg` | Ölçeklenebilir logo kaynağı. |
| `app16.png` … `app256.png` | Başlık, görev çubuğu, kabuk ve Hakkında ikonları. |
| `mikrocam.ico` | 16, 24, 32, 48, 64, 128 ve 256 piksel Windows ikon katmanları. |
| `make_splash.py` | Açılış görseli, logo ve ikonları aynı geometriyle üreten betik. |

Açılış görselinin renkleri (05.10.2026) mikrofab.com tasarım değişkenlerinden esinlenir:
lacivert zemin `#0A1628` → `#102243`, çerçeve/ayırıcı `#1e3a64`, "CAM" ve üst çizgi
`#1C74BA` → `#5aa9f0`, izolasyon hattı ve DRO `#5aa9f0`, lazer taraması `#d7e8fb`,
alt yazı `#9aa7b8`. Bakır PCB izleri, logo ve uygulama ikonları değişmedi.

Açık ve koyu temadaki `assets/resources/` marka dosyaları aynı tasarımı kullanır.
Eski `flatcam_icon*.png/.ico` tüketicileri de yeni işareti gösterir. `assets/icon.png`,
`app.svg` ve `app_small.svg` günceldir. Açılışta sol alt alan yükleme mesajlarına ayrılmıştır.
Uygulama büyük açılış görselini oranını koruyarak 622×276 piksel gösterir.

## Yeniden üretme

Chakra Petch (Bold, SemiBold, Medium) ve JetBrains Mono fontları SIL OFL 1.1 lisanslıdır.
Fontlar repoya dağıtılmaz; yalnızca görüntülerdeki metin için kullanılır.
Kaynaklar: https://github.com/google/fonts/tree/main/ofl/chakrapetch ve
https://github.com/google/fonts/tree/main/ofl/jetbrainsmono . JetBrains değişken fontu
`JetBrainsMono.ttf` adıyla kaydedilir. Bu çalışma için font önbelleği `.venv/branding-fonts/`.

```powershell
.\.venv\Scripts\python.exe docs/branding/make_splash.py .venv/branding-fonts docs/branding
```

Shapely ve Pillow mevcut sabitlenmiş bağımlılıklardır; yeni bağımlılık eklenmemiştir.
Orijinal yazarlara ait telif ve kaynak kayıtları LICENSE/NOTICE belgelerinde korunur.

## Integrated delivery, 2026-10-02

Delivered to `main` through [PR #34](https://github.com/ozkurkuran/MikroCAM/pull/34),
merge `d173f5fde47008f04de824ea26b6903896a69f16`. PRs #28–#33 are also confirmed merged;
their original commit histories are preserved. Earlier pending/open statements above are historical.

Exact tested source head `405da9519c8ebd3bc73c38517e818eae4c56e53b`:
- Complete local CPython 3.13 suite: 5487 passed, 3 skipped, 11 existing warnings,
  310 subtests, 595.42 s; `.venv/grbl-delivery-full.log`.
- [Windows CI PASS](https://github.com/ozkurkuran/MikroCAM/actions/runs/36989955432):
  same 5487 tests and 310 subtests, 306.13 s.
- Native Qt/OpenGL desktop smoke exit 0; character-counting queue completes three jobs,
  Stop prevents the next source, new MikroCAM logo/About renders and shutdown passes.
  Queue and About screenshots visually inspected; `.venv/grbl-delivery-desktop.log`.

Three skips are the operator-only hardware inventory and two existing full-Qt-context tests.
No physical device was connected. H3 remains open; FluidNC/grblHAL/TCP/SD remain deferred.
The final main documentation head requires its own CI; its exact status is recorded in
central `docs/IS_TAKIP.md`, without transferring this source-head PASS to a newer commit.
