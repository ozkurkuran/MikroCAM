# Windows ikili paketleri

MikroCAM'in Windows 11 x64 ikili dağıtımı iki dosyadır:

| Dosya | Kullanım |
| --- | --- |
| `MikroCAM-<sürüm>-win64-portable.zip` | Herhangi bir klasöre açılır, `MikroCAM.exe` çalıştırılır. Ayarlar ve araç veritabanı ZIP klasöründeki `config\` altında kalır (portable kip). |
| `MikroCAM-<sürüm>-win64-setup.exe` | Yönetici hakkı istemeden yalnızca bu kullanıcı için `%LOCALAPPDATA%\Programs\MikroCAM` altına kurar; Başlat menüsü kısayolu ve "Uygulamalar ve özellikler" kaldırma kaydı oluşturur. Ayarlar `%APPDATA%\FlatCAM` altındadır ve kaldırmada silinmez. |

Python veya derleyici gerekmez. Sürüm, ad ve yayımcı `mikrocam/core/identity.py`'den gelir.
`<sürüm>-SHA256SUMS.txt` dosyası iki paketin SHA-256 değerlerini içerir.

## Pakette olmayanlar

- Opsiyonel görüntü içe aktarma/izleme araçları (rasterio/GDAL, svgtrace, Playwright/Chromium).
  Bu araç açıldığında mevcut "paket eksik" mesajı görünür; kaynak kurulumda kullanılabilir.
- Google OR-Tools. COIN-OR (EPL-2.0) kodunu statik içerdiği ve GPLv3 PyQt6 ile tek ikili
  paket olarak dağıtılamadığı için hariçtir. Delik/frezeleme yol sıralaması pakette RTree ile
  yapılır; "Basic/MetaHeuristic" seçenekleri devre dışı görünür.
- KiCad Bridge eklentisi kaynak checkout ve Python ister; `.mcam-transfer` paketleri ikili
  uygulamada açılabilir, eklenti kurulumu kaynak kurulumdan yapılır.

Görsel satır serpiştirmenin bitmap, statik SVG (`resvg_py`) ve PDF (Qt PDF) kaynakları pakettedir
ve ilk kullanımda yüklenir.

## İmzasız ikililer, SmartScreen ve antivirüs

Paketler kod imzalı değildir. İlk çalıştırmada Windows SmartScreen "Windows kişisel
bilgisayarınızı korudu" diyebilir: **Ek bilgi → Yine de çalıştır**. İndirdiğiniz dosyanın
SHA-256 değerini yayın sayfasındaki değerle karşılaştırın:

```powershell
Get-FileHash .\MikroCAM-0.1.0-win64-setup.exe -Algorithm SHA256
```

PyInstaller ile dondurulmuş uygulamalar bazı antivirüslerde sezgisel yanlış pozitif
üretebilir. Paket onedir kipindedir (tek dosya açıcı yok), UPX kullanılmaz ve sürüm bilgisi
taşır; bu riski azaltır ama sıfırlamaz. Yanlış pozitif durumunda dosyayı antivirüs üreticisine
bildirin; karantinadaki dosyayı doğrulamadan geri yüklemeyin.

## Lisanslar

Paket kökünde `LICENSE.txt` (MikroCAM MIT), `NOTICE.md`, `NOTICE-BINARY.txt` ve `licenses\`
(tüm üçüncü taraf lisans/bildirim metinleri) bulunur. `bundle-manifest.json` her dosyanın hangi
bileşenden geldiğini ve SHA-256 değerini listeler. PyQt6 GPLv3 olduğundan ikili paket bütün
olarak GPLv3 koşullarıyla iletilir; karşılık gelen kaynak bağlantıları `NOTICE-BINARY.txt`
içindedir. Ayrıntı: [NOTICE](../NOTICE.md).

## Paketi üretmek (bakımcı)

CPython sürümü `.python-version` ile aynı olmalıdır (3.13.13 x64). NSIS 3.12 gerekir
(`choco install nsis --version=3.12.0` veya resmi kurulum).

```powershell
py -3.13 -m venv .venv\build
.\.venv\build\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.txt -r requirements-visual.txt -r requirements-build.txt
.\.venv\build\Scripts\python.exe -m pip check
.\.venv\build\Scripts\python.exe release\windows\build.py --out dist\windows
.\.venv\build\Scripts\python.exe release\windows\smoke_binary.py --dist dist\windows --native --installer
```

`build.py` sabit sürümler dışında paket bulunan ortamı reddeder, PyInstaller'ı temiz PATH ile
çalıştırır ve izinli kaynak dışından gelen, kurulu wheel RECORD karmasıyla uyuşmayan veya lisans
metni olmayan herhangi bir dosyada durur. `smoke_binary.py` varsayılan IPC borusu başka bir
MikroCAM örneğine aitse veya MikroCAM zaten kuruluysa başlamaz; Qt ayar anahtarını yedekleyip geri
yükler. Gerçek seri port, kamera veya makineye bağlanmaz.

Yeni Python/Qt/araç sürümünde bildirimler `release\windows\collect_notices.py` ile yenilenir ve
`tests\test_binary_notices.py` ile doğrulanır.

## GitHub Releases

`.github/workflows/package-windows.yml`:

- `workflow_dispatch`: ZIP, kurulum programı, SHA256SUMS ve `bundle-manifest.json` artifact
  olarak yüklenir; offscreen ikili duman ve sessiz kurulum/kaldırma koşar.
- Paketleme girdilerini (`release/windows/**`, `requirements*.txt`, `.python-version`, envanter,
  iş akışı) değiştiren PR'lar: aynı derleme ve duman testi, Release yok.
- `v*` tag push: aynı adımlar + **taslak** Release. Taslak otomatik yayımlanmaz.

Yayımlama kullanıcı kararıdır: tag (`vX.Y.Z`, `identity.VERSION` ile aynı) oluşturmak, taslağı
gerçek masaüstü/kurulum kontrolünden sonra yayımlamak ve imzasız ikili uyarısını yayın notuna
eklemek bakımcının adımıdır.
