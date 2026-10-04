# Feature specification — Windows paketleme: portable ZIP, kurulum programı ve Release hazırlığı

Branch: `040-packaging-windows`; base `70800e5b`; 2026-10-04.
Roadmap: 1.0 Ürünleştirme, sıra 32 `packaging-windows` — "Installer ve portable ZIP; GitHub Releases".
Bu dilime ayrıca [033 visual-svg-pdf](../033-visual-svg-pdf/tasks.md) açık görevleri T001
(resvg_py wheel/render/lisans/paketleme denemesi) ve T010 (SVG/PDF lazy import, Qt PDF
lisans/paketleme, donanımsız offscreen duman testi) katılmıştır.

Kullanıcı bu oturumda yoktur; soru sorulamadığı için belirsizlikler aşağıda
**uygulama varsayımı** olarak yazılır, kullanıcı kararı gibi gösterilmez.

## User scenarios and acceptance

### US1 — Python kurmadan MikroCAM'i çalıştırma (P1)

Windows 11 x64 kullanıcısı GitHub Releases'tan indirdiği portable ZIP'i bir klasöre açar ve
`MikroCAM.exe`'yi çalıştırır. Python, derleyici, yönetici hakkı veya ağ gerekmez.
Bağımsız kabul: dondurulmuş (frozen) uygulama, temiz bir klasörde offscreen ve gerçek masaüstünde
açılır; paketle gelen örnek Gerber/Excellon dosyasını açar, izolasyon + CNC iş üretir, G-code
yazar, projeyi kaydeder, yeniden açar ve normal kapanır. Portable kipte ayarlar ZIP klasörünün
`config/` dizininde kalır. Opsiyonel ağır bağımlılıklar (rasterio/GDAL, svgtrace/Playwright,
KiCad) pakette yoktur ve uygulama bunlar olmadan açılır; görsel serpiştirme kaynakları
(bitmap, `resvg_py` ile statik SVG, Qt PDF ile PDF sayfası) paketin içinde tek pipeline'dan
kaydedilip açılır.

### US2 — Kullanıcı başına kurulum ve kaldırma (P1)

Kullanıcı `MikroCAM-<sürüm>-win64-setup.exe` ile yönetici hakkı istemeden
`%LOCALAPPDATA%\Programs\MikroCAM` altına kurar. Başlat menüsünde MikroCAM kısayolu ve
"Uygulamalar ve özellikler" listesinde kaldırıcı oluşur; ikon, ad, sürüm ve yayımcı tek
kimlik modülünden (`mikrocam/core/identity.py`) gelir. Kaldırıcı kurduğu dosyaları,
kısayolu ve kayıt girdisini siler; kullanıcı verisine (`%APPDATA%\FlatCAM`) dokunmaz.
Bağımsız kabul: sessiz kurulum → kısayol/kayıt/uygulama açılışı → sessiz kaldırma geçici
bir hedef dizinde otomatik doğrulanır.

### US3 — Lisanslar ve tekrarlanabilir yayın hazırlığı (P1)

Alıcı, paketteki her ikili dosyanın hangi bileşenden geldiğini ve lisans/bildirim metnini
paketin `licenses/` dizininde bulur (PyQt6 GPLv3, Qt LGPLv3 ve Qt üçüncü taraf bildirimleri,
CPython ve Microsoft Distributable Code koşulları, PyInstaller bootloader istisnası, OR-Tools
yerel kütüphaneleri, resvg_py Rust crate bildirimleri, devralınan artwork kaynak kaydı).
Kaynak kodun nereden alınacağı (karşılık gelen kaynak) yazılıdır. Bakımcı aynı sabit
gereksinimlerle aynı ZIP/kurulum programını yerelde veya GitHub Actions'ta üretir; tag push'ta
yalnızca **taslak** Release hazırlanır, yayımlamak kullanıcı kararıdır.
Bağımsız kabul: paket manifestosunda eşlenmemiş ikili dosya kalmaz; eksik lisans testi
başarısız olur; iş akışı `workflow_dispatch` ile ZIP + kurulum programını artifact olarak üretir.

### Edge cases

- Varsayılan IPC borusu (`\\.\pipe\NPtest`) başka bir MikroCAM örneğine aitse ikili duman
  testi o örneğe komut göndermemek için başlamadan durur.
- Duman testi Qt ayarlarını kayıt defterinde (`HKCU\Software\Open Source\FlatCAM_EVO`) değiştirir;
  önceden yedeklenir ve sonra geri yüklenir. Uygulama verisi geçici dizine yönlendirilir.
- Başlangıç betiği (`--shellfile`) ya da başlangıç argümanı ile istenen çıkış, Qt olay döngüsü
  başlamadan geldiğinde süreç gizli pencereyle asılı kalmamalıdır (legacy hata; önce test).
- İmzasız ikililer SmartScreen uyarısı alır; antivirüs davranış engeli oluşursa gizlenmez,
  kaydedilir.
- Paket dizini boşluk/Türkçe karakter içeren yolda çalışmalıdır.
- `requirements-image.txt` paketleri build ortamına yanlışlıkla girerse paket oluşturma reddedilir.

## Functional requirements

- FR-001: Uygulama CPython 3.13.x x64 ve `requirements.txt` + `requirements-visual.txt` sabit
  sürümleriyle, ayrı ve sabitlenmiş `requirements-build.txt` araçlarıyla dondurulur.
- FR-002: Çıktılar `MikroCAM-<VERSION>-win64-portable.zip` ve `MikroCAM-<VERSION>-win64-setup.exe`;
  sürüm, ad, yayımcı, URL ve telif yalnızca `mikrocam/core/identity.py`'den okunur.
- FR-003: ZIP portable kipte (`config/configuration.txt` `portable=True`), kurulum programı
  normal kipte çalışır; uygulama veri/ayar formatları ve ad alanları değişmez.
- FR-004: Kurulum programı yönetici hakkı istemez, kullanıcı başına kurar, Başlat menüsü
  kısayolu, kaldırıcı ve HKCU kaldırma kaydı oluşturur; kaldırıcı yalnızca kendi dosyalarını siler.
- FR-005: Opsiyonel image/KiCad bağımlılıkları pakete girmez; uygulama onlarsız açılır, ilgili
  araçlar mevcut "paket eksik" mesajını verir. SVG/PDF görsel kaynakları lazy import edilir.
- FR-006: Paket içindeki her dosya bir kaynağa (MikroCAM kaynak/varlık, CPython, PyInstaller
  bootloader, kurulu dağıtım RECORD'u veya açıkça listelenmiş Microsoft çalışma zamanı) eşlenir;
  eşlenmeyen ya da lisans kaydı olmayan dosya derlemeyi başarısız kılar.
- FR-007: `NOTICE.md`, `LICENSE`, `THIRD_PARTY_LICENSES/` ve ikili dağıtım bildirimi pakete girer;
  003'te açık kalan ikili dağıtım boşlukları (Rasterio DLL, devralınan artwork, resvg_py
  bileşimi, Qt/OR-Tools yerel üçüncü taraf bildirimleri) kapatılır veya kalan kısmı açıkça
  kaydedilir.
- FR-008: İkili duman testi dondurulmuş `MikroCAM.exe`'yi offscreen ve gerçek masaüstünde,
  aynı paketteki duman yürütücüsünü görsel/opsiyonel bağımlılık senaryosu için çalıştırır;
  kurulum programını sessiz kurup kaldırır. Gerçek seri port, kamera veya makineye bağlanılmaz.
- FR-009: GitHub Actions iş akışı tag push, `workflow_dispatch` ve paketleme girdilerini değiştiren PR'larda ZIP + kurulum programını
  artifact olarak üretir, ikili duman testini koşar; yalnızca tag'de taslak Release oluşturur.
  Bu dilimde tag push edilmez ve Release yayımlanmaz.
- FR-010: Kod imzalama kapsam dışıdır; SmartScreen ve antivirüs yanlış pozitif riski belgelenir,
  yerel antivirüs davranışı gözlemlenip kaydedilir.
- FR-011: `quit_app` veya başlangıç `quit` isteği olay döngüsünden önce gelirse uygulama döngü
  başlar başlamaz kapanır (legacy hata düzeltmesi, önce yeniden üreten test).
- FR-012: Tcl/CLI `open_project` etkileşimli "Import Settings" modalını açmaz; ASCII dışı
  kurulum yolunda (ör. Türkçe kullanıcı adı) kanvas yazıları çizilir (legacy hata
  düzeltmeleri, önce yeniden üreten test).

## Success criteria

- SC-001: Portable ve kurulu `MikroCAM.exe` duman testleri exit 0, G-code ve proje yeniden
  açma eşitliği PASS; artık MikroCAM süreci kalmaz.
- SC-002: Paket manifestosunda %100 dosya eşlemesi; her bileşenin en az bir tam lisans metni pakette.
- SC-003: Sessiz kurulum/kaldırma sonrası hedef dizin, kısayol ve HKCU kaydı kalmaz.
- SC-004: Tam pytest paketi, mimari testleri ve kaynak `tests/smoke_app.py` yeşil kalır.

## Assumptions (uygulama varsayımları — kullanıcı kararı değildir)

- A1: Paket, `requirements-visual.txt` görsel codec'lerini (Pillow, resvg_py) içerir;
  `requirements-image.txt` (rasterio/GDAL, svgtrace, Playwright/Chromium) içermez. Gerekçe: GDAL
  DLL lisans denetimi ve Chromium indirmesi ikili dağıtım kapsamını büyütür; kaynak kurulumda
  bu araçlar aynen kalır.
- A2: Kurulum hedefi kullanıcı başına `%LOCALAPPDATA%\Programs\MikroCAM`; tüm kullanıcılar için
  kurulum sunulmaz.
- A3: Uygulama veri yolu ve Qt ayar ad alanı (FlatCAM/FlatCAM_EVO) değişmez (003 FR-007).
- A4: İkili dağıtım PyQt6 GPLv3 içerdiği için bütün olarak GPLv3 koşullarıyla iletilir;
  MikroCAM kaynak kodu MIT kalır. Karşılık gelen kaynak bağlantıları bildirimde verilir.
- A5: Kod imzalama ücretsiz ve güvenilir bir yol olmadığından yapılmaz.
- A6: Release yayımı (tag push, taslağı yayımlama) kullanıcı onayı bekler — WAITING.
- A7: Tcl betik yürütümünün asenkron nesne üretimi legacy davranıştır; duman testi betikte
  nesne adını bekleyerek senkronize olur, Tcl motoru değiştirilmez.

## Scope and hazard analysis

Bu dilim dağıtım/paketleme içindir; makine hareketi, lazer emisyonu veya donanım I/O'su eklemez.
Pakete giren seri port kodu mevcut davranıştır; duman testleri gerçek porta bağlanmaz.
Yanlış yapılandırılmış ikili paketin riski (eksik preprocessor, yanlış veri yolu, eksik lisans)
paket manifestosu, ikili duman testi ve eksik-lisans testleriyle ele alınır.
