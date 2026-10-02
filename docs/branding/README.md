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
