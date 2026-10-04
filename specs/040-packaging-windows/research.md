# Research — Windows paketleme

Tarih: 2026-10-04. Ortam: Windows 11 Pro 10.0.26200, CPython 3.13.13 x64 (`.python-version`),
ayrı `.venv/build` ve `.venv/test` sanal ortamları (`--only-binary=:all:`; derleyici yok).

## R1 — Dondurucu (freezer) seçimi

| Seçenek | Lisans (build aracı) | Değerlendirme |
| --- | --- | --- |
| **PyInstaller 6.22.3** + hooks-contrib 2026.8 | GPL-2.0-or-later + bootloader istisnası (çıktı GPL'e bağlanmaz); hooks GPL-2.0-or-later / Apache-2.0 | PyQt6 6.11 (QtPdf/QtSvg dahil), VisPy, Shapely, Matplotlib, Tcl/Tk için hazır hook; onedir kipinde Qt DLL'leri ayrı dosya kalır (LGPL değiştirilebilirlik); derleyici gerekmez. **Seçildi.** |
| cx_Freeze 8.7.1 (repodaki `make_freeze.py`) | PSF-türevi izin verici | Mevcut betik Evo `FlatCAM.exe` + updater üretir; MikroCAM 003 kararıyla updater kapalıdır. Kullanmak legacy betiği değiştirmeyi gerektirir. PyQt6 PDF/VisPy hook kapsamı daha dar. Reddedildi; `make_freeze.py` ve testleri değişmeden kalır. |
| Nuitka | Apache-2.0 | C derleyicisi (MSVC) gerektirir; derleme süresi ve AV/kaynak sorunları yüksek. Reddedildi. |
| Briefcase (MSI/WiX) | BSD-3 | Kendi proje düzenini ve WiX'i getirir; mevcut legacy yapı için ağır. Reddedildi. |

Spike (onedir, `.venv/spike.spec`) bulguları:

1. `vispy/glsl` veri dosyaları otomatik toplanmadı → `collect_data_files('vispy')` gerekli.
2. OR-Tools yerel DLL'leri `ortools/.libs` altında; PyInstaller bulamadı (bkz. R4).
3. PyOpenGL hook'u `OpenGL/DLLS` (freeglut/gle, 32/64 bit, vc9/vc10/vc14) topluyor; bunlar
   `MSVCR90/MSVCR100` ister ve `C:\Windows\System32\MSVCR100.dll` pakete sızdı. Uygulama GLUT/GLE
   kullanmaz → yerel hook ile hariç tutulur.
4. **PATH sızıntısı:** derleme makinesinin PATH'indeki `C:\Program Files\UVtools` (41 adet
   `api-ms-win-*`/`ucrtbase.dll`) ve `C:\Program Files\Git\ucrt64\bin` (`libssl-3-x64.dll`,
   `libcrypto-3-x64.dll`) pakete girdi. Karar: derleme temiz PATH ile çalışır ve paket
   manifestosu izinli kaynak kökleri dışındaki her dosyayı reddeder.
5. `appGUI/VisPyData` (32/64-bit freetype253 + OpenSans) yalnızca çağrılmayan
   `copy_and_overwrite` yedek yolunda geçiyor; pakete alınmaz.
6. `assets/Working GDAL-RASTERIO wheels` (cp310 wheel'ler) ve `assets/linux` pakete alınmaz.
7. Uygulama `appMain.app_home` ile `_internal` dizinine `chdir` eder; kaynaklar (`assets`,
   `locale`, `preprocessors`) `_internal` altında, `config/configuration.txt` kök dizinde
   (frozen dalı `appLifecycle`/`flatcam.py` bu yolu zaten arıyor).

## R2 — Kurulum programı

| Seçenek | Lisans | Değerlendirme |
| --- | --- | --- |
| **NSIS 3.12** | zlib/libpng (zlib sıkıştırıcı ile stub tamamen zlib/libpng) | OSI onaylı; `RequestExecutionLevel user` ile yönetici hakkı olmadan HKCU kurulum; makinede kurulu, Chocolatey'de `nsis 3.12.0` sabitlenebilir. **Seçildi.** |
| Inno Setup 6 | Inno Setup License (izin verici, OSI listesinde değil) | Teknik olarak uygun, makinede kurulu; ancak kurulum programına gömülen stub OSI onaylı değil (anayasa VII). Reddedildi. |
| WiX/MSI | MS-RL | Kullanıcı başına MSI ve kaldırma yönetimi daha karmaşık. Reddedildi. |

NSIS sıkıştırıcı: LZMA modülü CPL-1.0'dır; GPLv3 içerikle karışık lisans yorumundan kaçınmak için
`zlib` seçildi (boyut maliyeti kabul). Kaldırıcı `RMDir /r $INSTDIR` kullanmaz; derleme sırasında
üretilen açık dosya/dizin listesiyle yalnızca kendi dosyalarını siler (kullanıcı başka bir klasör
seçerse veri kaybı riski yok).

## R3 — Legacy çıkış hatası

`--shellfile` betiği `App.__init__` içinde, `app.exec()` başlamadan yürür. `quit_app` →
`AppLifecycle.quit_application()` sonunda `QApplication.quit()` çağırır; olay döngüsü henüz
yokken Qt bu çağrıyı yok sayar, ardından `app.exec()` sonsuza dek döner (UI gizli, havuz kapalı).
faulthandler yığını `flatcam.py` `app.exec()` satırını gösterdi; kaynakta da aynı. Düzeltme: aynı
çıkışı `QTimer.singleShot(0, QApplication.quit)` ile döngü başlangıcına da bırakmak. Başlangıç
argümanı `quit` da aynı yolu kullanır.

İkili duman testinde iki legacy hata daha bulundu (ikisi de kaynakta da geçerli):

- `appIO.restore_project_handler` koşulu (`not run_from_arg or not cli or from_tcl is False`)
  Tcl `open_project` için de "Import Settings" modalını açıyordu; offscreen/başlangıç betiğinde
  görünmez modal süreci kilitledi. Kodun yorumu GUI dışında seçeneklerin doğrudan yüklenmesini
  söyler; düzeltme `not (cli or from_tcl)`. "Legacy Project" modalı (Tcl'de reddeder) değişmedi.
- freetype-py dosya adını UTF-8 bayt olarak FreeType'ın dar `fopen`'ına verir; Türkçe karakterli
  yolda (`Taşınabilir ğüş paket`; gerçek kullanıcıda `C:\Users\Şükrü\AppData\Local\Programs`)
  VisPy eksen yazısı `FT_Exception: cannot open resource` ile çöktü. freetype-py, dosya adı
  kodlaması `UnicodeError` verirse dosyayı Python ile okuyup bellekten açar; `VisPyPatches`
  Windows'ta ASCII-dışı adlarda bu yolu seçtirir.
- `--shellfile` ANSI kod sayfasıyla (`open(..., 'r')`) okunur; duman betiği bu kodlamayla yazılır.
- NSIS `/D=` yalnızca tırnaksız ve son argümanken geçerlidir; tırnaklı verildiğinde varsayılan
  `%LOCALAPPDATA%\Programs\MikroCAM` dizinine kurdu (yerel denemede bu kurulum `/S` ile temiz
  kaldırıldı). Duman sürücüsü komut satırını aynen geçirir.

Tcl komutları (`open_gerber`, `isolate`) nesneleri asenkron worker'da üretir; ardışık komut
nesneyi henüz bulamayabilir (kaynakta yarış gözlendi). Tcl motoru değiştirilmez; duman betiği
`get_names` + `plot_all` (sinyalli, olay döngüsünü döndürür) ile nesneyi bekler.

## R4 — Lisans uyumluluğu ve bildirim boşlukları

- **PyQt6 GPLv3:** ikili paket bütün olarak GPLv3 koşullarıyla iletilir; MikroCAM kaynağı MIT kalır.
  Karşılık gelen kaynak: MikroCAM commit'i (GitHub), PyQt6 6.11.0 sdist (PyPI), Qt 6.11.2 kaynak
  arşivi (download.qt.io). onedir düzeninde Qt DLL'leri ayrı dosyadır (LGPLv3 değiştirme hakkı).
  svglib (LGPL-3.0-or-later) saf Python olarak `.py` kaynak biçiminde, PYZ dışında toplanır.
- **Qt üçüncü taraf kodu:** PyQt6-Qt6 wheel'i yalnızca LGPL metnini taşır. Qt 6.11.2'nin resmi
  "Third-Party Code Used in Qt" sayfası ve paketteki modüllerin (Core, GUI, Image Formats, Network,
  PDF/PDFium, SVG, Test) ve Mesa llvmpipe'ın (`opengl32sw.dll`) ayrıntı sayfaları bayt olarak saklanır.
- **OR-Tools 9.15:** `ortools.dll` içinde Coin-OR CLP/CBC statik bağlıdır (`clp-src\Clp\src\ClpSimplexDual.cpp`
  dizgileri). Coin-OR EPL-2.0 (ikincil lisans bildirimi yok) GPLv3 ile uyumsuz kabul edilir; ayrıca
  abseil/protobuf/re2/HiGHS/SCIP/zlib/bzip2 DLL bildirimleri wheel'de yok. Uygulama OR-Tools yoksa
  RTree yoluna düşer (`camlib.HAS_ORTOOLS`, tercihlerde seçenekler devre dışı). **Uygulama varsayımı:**
  Windows ikilisinden hariç; kaynak kurulum değişmez. Dahil etme kararı hukuki inceleme sonrası
  kullanıcıya aittir (WAITING değil, açık kayıt).
- **Rasterio/GDAL DLL boşluğu:** `requirements-image.txt` pakete girmez → ikili için kapanır; kaynak
  opsiyonel kurulum için kayıt açık kalır.
- **resvg_py:** pakete giren `.pyd` wheel RECORD karmasıyla, wheel SHA256 `1f6b8956…` ile doğrulanır;
  75 crate'in 152 bildirimi pakete girer. PyPI build provenance 404 → ikili/kaynak eşlemesi kanıtsız
  olarak kayıtlı kalır.
- **Devralınan artwork:** `assets/resources` dosyaları git geçmişinden dosya başına ekleyen commit,
  yazar, tarih ve SHA256 ile kayda geçirilir; About/NOTICE kredileri pakete girer. Her ikonun
  özgün sağlayıcı lisansı geçmişte yok → "upstream provenance recorded", lisans doğrulaması açık.
- **CPython 3.13.13 Windows ikilisi:** `LICENSE.txt` (PSF + bzip2/libffi/OpenSSL/Tcl/Tk… ve
  "Microsoft Distributable Code" ek koşulları) saklanır ve pakete girer.
- **Microsoft çalışma zamanı:** `vcruntime140*.dll` (CPython), `MSVCP140*.dll` (PyQt6-Qt6, NumPy)
  Microsoft Distributable Code'dur; ikili bildirimde kısıtlar yazılır. Temiz PATH ile UCRT
  `api-ms-win-*` ileticileri pakete girmez (Windows 10/11'de işletim sistemiyle gelir).
- **PyInstaller bootloader:** `MikroCAM.exe` içine gömülü; COPYING.txt bootloader istisnasıyla
  pakete girer. Build araçları `requirements-build.txt` içinde `==` ile sabitlenir ve envanterde
  `build` grubunda kaydedilir.
- **NSIS 3.12:** kurulum programı stub'ı; COPYING metni bileşen olarak saklanır.

## R5 — İmzalama, SmartScreen ve antivirüs

Ücretsiz ve kalıcı bir kod imzalama yolu (SignPath OSS vb.) başvuru/onay ister; bu dilimde yok
(A5). İmzasız `setup.exe` ve `MikroCAM.exe` SmartScreen "Windows kişisel bilgisayarınızı korudu"
uyarısı alır; kullanıcı "Ek bilgi → Yine de çalıştır" seçmelidir. PyInstaller bootloader'ı bazı
antivirüslerde sezgisel yanlış pozitif üretebilir; onedir kipi (onefile değil), sürüm kaynağı
(VERSIONINFO) ve UPX kullanılmaması riski azaltır, sıfırlamaz. Release notunda SHA256 ve
VirusTotal/AV beyaz liste yönlendirmesi verilir. Yerel Kaspersky gözlemi `validation.md`'dedir.

## R6 — GitHub Actions

`windows-latest` üzerinde `.python-version` ile setup-python; `requirements.txt` +
`requirements-visual.txt` + `requirements-build.txt` binary-only kurulum; NSIS 3.12 yoksa
`choco install nsis --version=3.12.0`. Tetikleyiciler: `push: tags: ['v*']`, `workflow_dispatch` ve
`release/windows/**`, `requirements*.txt`, `.python-version`, envanter veya iş akışını değiştiren PR'lar
(`workflow_dispatch` yalnızca varsayılan dalda bulunan iş akışı için çağrılabildiğinden PR doğrulaması bu yolla yapılır).
Build işi `contents: read`; taslak Release işi yalnızca tag'de, `contents: write` ile `gh release
create --draft`. Barındırılan runner gerçek OpenGL sağlamaz; orada yalnızca offscreen ikili duman
ve sessiz kurulum/kaldırma koşar, gerçek masaüstü duman testi yereldir.
