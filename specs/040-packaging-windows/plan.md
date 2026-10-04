# Implementation plan — Windows paketleme

2026-10-04; [spec](spec.md), [research](research.md). CPython 3.13.13 x64, PyInstaller 6.22.3,
NSIS 3.12. Yeni **runtime** bağımlılığı yok; yeni **build** bağımlılıkları `requirements-build.txt`.

## Constitution Check

1. **Yeni mantık `mikrocam/` altında mı, katman yönü?** EVET/N-A. Uygulamaya yeni özellik mantığı
   eklenmez. Paketleme betikleri uygulamanın parçası değildir; `release/windows/` altında, uygulama
   tarafından import edilmeyen ayrı build aracıdır (KiCad eklentisinin `integrations/` altında
   durması gibi). Ürün kimliği yalnızca `mikrocam.core.identity`'den okunur.
2. **Legacy yalnızca düzeltme/bağlantı ve +50 altında mı?** EVET. Yalnızca önce yeniden üreten
   testle gelen üç hata düzeltmesi: `appHandlers/appLifecycle.py` olay döngüsünden önce istenen
   çıkış (+2), `appHandlers/appIO.py` Tcl/CLI `open_project` modalı (+1 net) ve
   `appGUI/VisPyPatches.py` ASCII-dışı yollarda FreeType font açma (+15). Toplam +18 satır.
3. **Soyutlama / bağımlılık?** EVET. Yeni sınıf hiyerarşisi, registry veya ayar yok; düz fonksiyonlar.
   Build bağımlılıkları sabit: pyinstaller 6.22.3 (GPL-2.0-or-later + bootloader istisnası),
   pyinstaller-hooks-contrib 2026.8 (GPL-2.0-or-later/Apache-2.0), altgraph 0.17.5 (MIT),
   pefile 2024.8.26 (MIT), pywin32-ctypes 0.2.3 (BSD-3-Clause). Alternatifler research R1/R2.
   Lisans metinleri `THIRD_PARTY_LICENSES/` ve envanterin `build` grubunda.
4. **Tek kaynak?** EVET. Ad/sürüm/yayımcı/URL/telif `identity.py`; sürüm VERSIONINFO, dosya adları,
   NSIS tanımları ve paket manifestosu ondan türetilir. Yeni kalıcı uygulama formatı yok; paket
   manifestosu (`bundle-manifest.json`) `schema_version` taşır ve yalnızca dağıtım kaydıdır.
5. **Donanımsız/ekransız test, test önce?** EVET. `tests/test_release_windows.py` saf fonksiyonları
   Qt/ağ/derleme olmadan test eder; çıkış hatası testi offscreen Qt ile; ikili duman testi ayrı ve
   donanımsızdır (gerçek port/kamera yok).
6. **Makine/lazer davranışı?** N/A. Hareket veya emisyon yok.
7. **Dış kaynaklı kod/lisans?** EVET. Kod kopyalanmaz; yalnızca lisans/bildirim metinleri bayt olarak
   saklanır (Qt attribution sayfaları, CPython LICENSE.txt, PyInstaller/NSIS COPYING). FlatCAM-Plus yok.
8. **≤3 user story, ≤40 görev?** EVET: 3 story, 34 görev.

## Design

```text
requirements.txt + requirements-visual.txt + requirements-build.txt  (binary-only, pip check)
        │
release/windows/build.py ──(temiz PATH)──▶ PyInstaller release/windows/mikrocam.spec
        │                                   ├─ MikroCAM.exe (windowed, VERSIONINFO, ikon)
        │                                   └─ MikroCAMSmoke.exe (console; aynı Analysis/PYZ)
        ├─ layout.py: kaynak kökü denetimi, dağıtım RECORD eşlemesi, bundle-manifest.json
        ├─ payload: smoke exe hariç + licenses/ + NOTICE/LICENSE + NOTICE-BINARY.txt + config
        ├─ MikroCAM-<v>-win64-portable.zip  (deterministik sıra/zaman, portable=True)
        └─ makensis MikroCAM.nsi → MikroCAM-<v>-win64-setup.exe (portable=False, HKCU)
release/windows/smoke_binary.py: ZIP aç → MikroCAM.exe Tcl (offscreen + native) →
        MikroCAMSmoke.exe (görsel bitmap/SVG/PDF + proje, opsiyonel bağımlılık yokluğu) →
        setup.exe /S → kurulu exe Tcl → Uninstall.exe /S → kalıntı yok
.github/workflows/package-windows.yml: tag v* / workflow_dispatch → artifact; yalnız tag'de taslak Release
```

- `layout.py` stdlib-only, ≤600 satır; fonksiyonlar ≤80 satır. Spec, build ve testler onu kullanır.
- Duman yürütücüsü aynı `Analysis` ve aynı PYZ ile üretilir; yalnızca betiği farklıdır. Böylece
  sevk edilen `MikroCAM.exe` ile aynı modül/ikili kümesini test eder; release payload'ına girmez.
- Duman yürütücüsü test modüllerini import etmez (pytest pakete girmez).
- Lisans bütünlüğü: `bundle-manifest.json` her dosyayı sahibine eşler; sahip envanterde yoksa veya
  pakette lisans dosyası yoksa build başarısız. `THIRD_PARTY_LICENSES/` tamamı `licenses/` olarak girer.
- Kayıt defteri: duman sürücüsü `HKCU\Software\Open Source\FlatCAM_EVO` anahtarını yedekler/geri yükler,
  `APPDATA`'yı geçici dizine yönlendirir, varsayılan IPC borusu doluysa başlamaz.

## Complexity Tracking

| İhlal / istisna | Neden gerekli | Reddedilen basit alternatif |
| --- | --- | --- |
| Uygulama dışında yeni Python kodu (`release/windows/`) | Build/duman araçları uygulama paketine girmemeli; `mikrocam/` import sınırları runtime içindir | `mikrocam/release` — runtime pakete build aracı sokar ve PyInstaller'ın kendi paketini dondurmasına yol açar |
| İkinci (duman) yürütücüsü | Dondurulmuş Python içinde görsel SVG/PDF pipeline'ı başka yolla deterministik sürülemez (Tcl komutu yok) | Ürüne test kancası/ortam değişkeni ile kod çalıştırma — güvenlik riski; GUI otomasyonu — kırılgan |
| OR-Tools ikiliden hariç | EPL-2.0 Coin-OR ile GPLv3 PyQt6 aynı süreçte; yerel DLL bildirimleri eksik | Dahil edip boşluğu kaydetmek — yayımlanabilir paket iddiasıyla çelişir |
| Legacy `appLifecycle.py` +2 satır | Gerçek hata: başlangıç betiğindeki çıkış süreci asılı bırakır | Duman testinde süreci zorla öldürmek — "normal kapanış" kabulünü sağlamaz |
| Legacy `appIO.py` koşulu (+1 net) | Tcl `open_project` görünmez "Import Settings" modalında sonsuza dek bekliyordu; kodun kendi yorumu GUI dışında seçenekleri doğrudan yüklemeyi söyler | Duman betiğinde proje açmayı atlamak — proje yeniden açma kabulü kaybolur |
| Legacy `VisPyPatches.py` +15 | `C:\Users\Şükrü\...` gibi ASCII-dışı kurulum yolunda ilk eksen yazısı FreeType "cannot open resource" ile uygulamayı çökertti (kaynak kurulumu da etkiler) | Kurulumu ASCII yola zorlamak — Türkçe kullanıcı adlarında kullanıcı başına kurulum çalışmaz; freetype-py'yi vendor/yamalamak — bağımlılık değişikliği |
