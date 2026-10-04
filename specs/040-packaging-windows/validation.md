# Validation — Windows paketleme (040) + 033 T001/T010

check-status: PASS (yerel + PR CI kaynak/ikili kabul) / WAITING (Release yayını, imzalama, merge koordinatörde).

Base `70800e5b`; dal `040-packaging-windows`; worktree `E:/VSCode/Flatcam/MikroCAM-packaging`.
Makine: Windows 11 Pro 10.0.26200, CPython 3.13.13 x64, Kaspersky (avp) etkin, Windows Defender
pasif. Kanıt logları worktree `.venv/` altındadır (git dışı). Merkezi kayıt:
`E:/VSCode/Flatcam/MikroCAM/docs/IS_TAKIP.md` → "Windows paketleme (32)".

| Kontrol | check-status | Kanıt |
| --- | --- | --- |
| İzole binary-only kurulum (build + test ortamları) | PASS | `.venv/t001-install.log`, `.venv/test-install.log`; `--only-binary=:all:`, derleyici yok; `pip check` iki ortamda temiz (`.venv/040-pipcheck.log`) |
| 033 T001 resvg_py wheel/render | PASS | wheel SHA256 `1f6b8956…6c3c` (önceki kayıtla aynı); `tests/test_visual_svg_pdf.py` 20 PASS (`.venv/t001-render.log`) |
| Önce-test: olay döngüsü öncesi çıkış | PASS | RED `.venv/040-quit-red.log` (1 FAIL, guard 5 s) → `appLifecycle` +2 → ilgili 16 PASS |
| Önce-test: release layout | PASS | RED `.venv/040-layout-red.log` (modül yok) → 42 PASS |
| Önce-test: ikili bildirimler | PASS | RED `.venv/040-notices-red.log` (9 FAIL) → `collect_notices.py` → 76 PASS |
| Önce-test: Tcl `open_project` modalı | PASS | RED `.venv/040-tclproject-red.log` → `appIO` koşulu → 2 PASS + 19 ilgili PASS/189 alt test |
| Önce-test: ASCII-dışı yol FreeType | PASS | RED `.venv/040-font-red.log` (`FT_Exception cannot open resource`) → `VisPyPatches` → PASS |
| PyInstaller build + paket manifestosu | PASS | `.venv/040-build5.log`; 3095 dosya / 26 sahip, 2607 PYZ modülü sahipli; PATH sızıntısı 0; wheel RECORD karmaları birebir; ortools/rasterio/PyOpenGL DLL yok |
| Portable ZIP | PASS | `MikroCAM-0.1.0-win64-portable.zip` 107 288 145 B, SHA256 `30765eb1f0ea48919f9ce5301162e16c03dd13765ec3393a40e9920593e520fc` |
| NSIS kurulum programı | PASS | `MikroCAM-0.1.0-win64-setup.exe` 104 469 211 B, SHA256 `f2376d6d1c3ebe7e6c6971db522a268469e526f98afc6eac5a845b7cec814ede`; makensis v3.12 `/WX` |
| İkili duman — portable offscreen | PASS | `.venv/040-smoke5.log`, `.venv/040-smoke-native-installer.json`: Tcl Gerber+Excellon→izolasyon→CNC→G-code→proje; ikinci açılışta proje→G-code eşit (587 satır); artık süreç yok |
| İkili duman — MikroCAMSmoke offscreen | PASS | FROZEN_ENVIRONMENT/STARTUP/CAM/VISUAL_BITMAP_SVG_PDF_JSON/PROJECT_CAM_AND_VISUAL_ROUNDTRIP/NORMAL_SHUTDOWN_OK |
| İkili duman — gerçek masaüstü | PASS | aynı iki yolculuk + NATIVE_RENDER_OK (VisPy/OpenGL, eksen yazıları) |
| Kurulum/kaldırma (`Kurulum Dizini ğüş`) | PASS | sessiz kurulum 11.2 s; Başlat menüsü kısayolu, HKCU kaldırma kaydı, `portable=False`; kurulu exe Tcl yolculuğu `%APPDATA%\FlatCAM` kullandı; sessiz kaldırma sonrası dizin/kısayol/kayıt yok, kullanıcı verisi korundu |
| Antivirüs (Kaspersky etkin) | PASS (gözlem) | Hiçbir exe/kurulum/kaldırıcı engellenmedi veya karantinaya alınmadı; MikroCAM.exe SHA256 çalıştırmalar boyunca aynı (`dc1dea8b…795f`). Tek gözlem: bir kullanıcının bugün gördüğü başka uygulamadaki davranış engeli burada tekrarlanmadı; garanti değildir |
| Mimari testler | PASS | 83 PASS (`tests/architecture`, legacy büyüme dahil) |
| Tam pytest (offscreen) | PASS | 5867 passed, 3 skipped, 11 mevcut uyarı, 310 alt test, 548.58 s, exit 0 (`.venv/040-full.log`, `.venv/040-full.xml`) |
| Kaynak `tests/smoke_app.py` native | PASS | exit 0, 68 s, tüm yolculuk işaretleri + RENDER_OK + SHUTDOWN_OK (`.venv/040-smoke-app.log`); ekran görüntüsü incelendi |
| PR Windows CI (tests) | PASS | [PR #43](https://github.com/ozkurkuran/MikroCAM/pull/43) head `1a0791b9`: [run 37214085188](https://github.com/ozkurkuran/MikroCAM/actions/runs/37214085188) 5867 passed, 3 skipped, 310 alt test, 425 s |
| PR paketleme iş akışı (windows-latest) | PASS | [run 37214085168](https://github.com/ozkurkuran/MikroCAM/actions/runs/37214085168): NSIS 3.12, build + manifest, portable/frozen offscreen duman, kurulum→kurulu exe→kaldırma; artifact `mikrocam-windows-x64` (ZIP `bd355d86…`, setup `bb276af6…`). İlk deneme [run 37213266063](https://github.com/ozkurkuran/MikroCAM/actions/runs/37213266063) FAIL: runner TEMP 8.3 kısa adı (`RUNNER~1`) kayıt metni eşleşmesini bozdu; sürücü winreg+samefile ile düzeltildi |
| `workflow_dispatch` | NOT_RUN | GitHub yalnızca varsayılan dalda bulunan iş akışını elle çalıştırır; dal doğrulaması yol filtreli `pull_request` tetikleyicisiyle yapıldı. Birleşmeden sonra kullanılabilir |
| Bit-bit tekrarlanabilirlik | N/A | Aynı sabit girdiler aynı dosya kümesini ve manifesti üretir; PyInstaller exe/ZIP baytları derleme ortamına göre değişir (yerel `30765eb1…` ≠ CI `bd355d86…`); iddia edilmez |
| GitHub Release yayını | WAITING | Tag push ve taslağı yayımlama kullanıcı kararı; bu dilimde tag/Release yok |
| Kod imzalama | WAITING / N/A | Ücretsiz kalıcı yol yok (A5); SmartScreen uyarısı belgelendi |
| Fiziksel makine/lazer | N/A | Donanım bağlantısı yok |

## Yol boyunca kayıtlı başarısızlıklar (silinmedi)

- Spike `--shellfile` ile `quit_app`: süreç `app.exec()`'te asılı kaldı (faulthandler); legacy hata,
  FR-011 ile düzeltildi.
- İlk build manifest denemeleri: lisanssız sahip (`pyinstaller-generated`), namespace paket
  kaynağı `-`, `_internal` önekli hedef yolları — build betiği düzeltildi; ürün kodu değişmedi.
- İlk portable duman (Türkçe yol): Tcl betiği UTF-8 yazılmıştı, uygulama ANSI okur → Gerber
  yolu bozuldu, 300 s zaman aşımı. ASCII denemesi ilk betiği geçirdi, ikinci betik Tcl
  `open_project` modalında asılı kaldı → FR-012 düzeltmesi.
- İlk native duman: Türkçe yolda VisPy eksen yazısı FreeType hatası → FR-012 düzeltmesi.
- İlk kurulum dumanı: NSIS `/D=` tırnaklandığı için varsayılan dizine kurdu; bu kurulum
  PowerShell ile `/S` kaldırıldı (dizin, kısayol, kayıt yok doğrulandı). Git Bash'in `/S`
  argümanını yol sanması bir kaldırma penceresi açtı; süreç kapatıldı.

## 033 T001/T010 kapanışı

[033 validation](../033-visual-svg-pdf/validation.md) ve tasks güncellendi: B01 binary-only
kurulum/render/paket/lisans, B10 lazy import + Qt PDF lisans/paket + dondurulmuş offscreen
(ve native) bitmap+SVG+PDF kaydet/aç PASS. Renderer değişimi yok, PDF vektör kapsamı eklenmedi.

## Kalan açıklar

- Devralınan ikonların özgün sağlayıcı lisansı dosya başına doğrulanamadı (git provenance kaydı var).
- resvg_py wheel build provenance upstream'de yok.
- OR-Tools ikiliden hariç (EPL-2.0 + GPLv3); dahil etme kararı hukuki inceleme sonrası kullanıcıda.
- KiCad Bridge eklentisi ikiliden kurulmaz (kaynak checkout ister).
