# MikroCAM marka dosyaları

| Dosya | Açıklama |
| --- | --- |
| `splash.png` | Açılış ekranı, 720×320. |
| `splash@2x.png` | Aynı görselin 1440×640 sürümü. `assets/resources/splash.png` ve `assets/resources/dark_resources/splash.png` bu dosyanın kopyasıdır. |
| `make_splash.py` | Görseli üreten betik. Bakır izler Shapely geometrisidir, camgöbeği çizgi bu izlerin buffer'ından elde edilen izolasyon yoludur, amber çizgiler bakırsız alanın lazer taramasıdır. |

`appMain.py` açılış görselini oranını koruyarak 622×344 kutusuna küçültür; bu görsel 622×276
olarak gösterilir. Uygulamaya büyük sürümün konması küçültmenin keskin kalmasını sağlar.

Sol alt köşe boş bırakılmıştır, çünkü `QSplashScreen.showMessage()` yükleme mesajlarını
oraya iki satır hâlinde açık gri renkte yazar.

## Yeniden üretme

Fontlar SIL Open Font License 1.1 ile lisanslıdır. Repoya eklenmezler; aşağıdaki adreslerden
indirilip bir klasöre konur. PNG'ye işlenmiş metin font dağıtımı sayılmaz.

- Chakra Petch (Bold, SemiBold, Medium): <https://github.com/google/fonts/tree/main/ofl/chakrapetch>
- JetBrains Mono (değişken font, `JetBrainsMono[wght].ttf` dosyası `JetBrainsMono.ttf` adıyla kaydedilir):
  <https://github.com/google/fonts/tree/main/ofl/jetbrainsmono>

```powershell
.\.venv\Scripts\python.exe docs\branding\make_splash.py <font_klasoru> docs\branding
Copy-Item docs\branding\splash@2x.png assets\resources\splash.png
Copy-Item docs\branding\splash@2x.png assets\resources\dark_resources\splash.png
```

Betik yalnızca Shapely ve Pillow kullanır; ikisi de `requirements.txt`'te sabitlenmiştir.
