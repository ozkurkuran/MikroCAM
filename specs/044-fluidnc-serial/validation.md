# Validation: FluidNC seri (USB) desteği (044)

Durum: yazılım doğrulaması FakeGRBL FluidNC profilleriyle yapıldı. **Hiçbir gerçek FluidNC kartı
bağlanmadı; gerçek seri port açılmadı.** Fiziksel doğrulama (H044-1…9, H042-4/5) **NOT_RUN/WAITING**.
Python: `E:\VSCode\Flatcam\MikroCAM\.venv\Scripts\python.exe` (CPython 3.13). Loglar worktree
`.venv/` altında (git'e girmez).

## Önce-test (RED)

| Adım | Sonuç | Kanıt |
| --- | --- | --- |
| Yeni FluidNC testleri, uygulama yokken | 4 toplama hatası (`mikrocam.machine.fluidnc`, `startup_evidence`, `FLUIDNC_COMMANDS` yok) | `.venv/044-red.log` |
| FluidNC matris + D1 testleri (güncellenmiş beklenti) | 83 FAIL / 72 PASS | `.venv/044-red-2.log` |
| Konsol `$$` `$130` hotfix regresyonu (GRBL ve FluidNC) | 2 FAIL | `.venv/044-red-console130.log` |

## GREEN

| Kontrol | Sonuç | Kanıt |
| --- | --- | --- |
| Odaklı FluidNC + D1 + konsol testleri | 384 PASS | yerel |
| `tests/test_fluidnc_fault_matrix.py` (C1 + adversarial, FluidNC profili) | 235 PASS | yerel |
| Öncelik yarışı regresyonu (önce RED: 2 FAIL, `.venv/044-red-priority.log`) | GRBL + FluidNC PASS | commit 67a50bc3 |
| `tests/architecture` | 83 PASS | yerel |
| `pip check` | temiz | yerel |
| Tam paket (offscreen), kod head `67a50bc3` | 6270 PASS, 3 skip, 310 alt test, 421,15 s | `.venv/044-full-3.log`, `.venv/044-full-3.xml` |
| Windows CI, head `67a50bc3` | PASS: 6270 passed, 3 skip, 310 alt test, 444,75 s | [run 37228982730](https://github.com/ozkurkuran/MikroCAM/actions/runs/37228982730) |
| Masaüstü `tests/smoke_app.py` (native, 120 s watchdog) | exit 0; `MACHINE_FLUIDNC_JOG_OK FluidNC 4.1.1; RX unknown; char-counting unavailable; motion enabled`, `MACHINE_READ_ONLY_OK`, `CONSOLE_READ_ONLY_CLEAR_OK`, `SHUTDOWN_OK`; yetim worker yok | `.venv/044-smoke.log` |

Smoke, `67a50bc3`'ten önceki `9d131c6b` kod durumunda çalıştırıldı; sonraki değişiklik yalnız
`job_control.py` başlangıç adımında bir `_guard()` çağrısı ve testidir (UI'ya dokunmaz).
Son belge commit'inin (validation/tasks) Windows CI sonucu PR #46'da kayıtlıdır.

## Kapsam kanıtı

- **Profil:** `fluidnc` = v4.1.1 (karşılama `Grbl 4.1 [FluidNC v4.1.1 (esp32-wifi) '$' for help]`,
  vektör TLO), `fluidnc3` = v3.9.9 (skaler TLO). İkisinde tanıma, jog, sıfır, G54, iş, probe grid ve
  D1 yolculukları geçer.
- **C1 matrisi:** `test_fluidnc_fault_matrix.py` C1 matrisi ile job/manual-stop/probe/console
  adversarial ve machine controller paketlerinden 234 testi FluidNC varsayılan profiliyle yeniden
  toplar (+1 profil doğrulama testi). Yeniden toplanmayan paketler GRBL'e özgü baytları (`$N`, `$31`,
  `startup_blocks`) assert eder; FluidNC karşılıkları `test_fluidnc_controller.py`'dedir. Keşif
  çalıştırması (bütün C1 makine paketleri FluidNC'de): 305 PASS / 40 FAIL, FAIL'lerin hepsi GRBL'e özgü
  beklentiler (`.venv/044-fluidnc-c1-explore.log`).
- **GRBL 1.1:** D1 altın izleri (13 senaryo) değişmeden geçer; seri taşıma ve DTR/RTS değişmedi.
- **Macro baytları:** `0x87`–`0x8A` üç doğrulayıcıda reddedilir ve hiçbir FluidNC yolculuğunda yazılmaz.

## Uygulama varsayımları ve açık işler (WAITING)

- UA-1…UA-10 [spec](spec.md#uygulama-varsayımları) içinde. Özellikle: `$31` yok → alt devir sınırı 0;
  DTR/RTS değişmedi; 2 s sessizlik; özel karşılama + Info altı mesaj seviyesinde ilk tanıma
  başarısız olabilir; 4+ eksen/`M56`/boş `A:` desteklenmez.
- **WAITING (fiziksel):** H044-1…9 ve H042-4/5 gerçek FluidNC v3.9.x/v4.x kartında; port açılışı
  DTR/RTS reset davranışı (CP210x/CH340/S3 yerel USB) ölçümü; H3 (GRBL) önkoşulu.
- **WAITING (karar):** DTR/RTS politikası saha kanıtından sonra ayrı spec/hotfix olabilir.
- Kapsam dışı: TCP/WebSocket (D4), SD'den iş (D5), homing/unlock, FluidNC kod metin tabloları.

## #45 (043 grblHAL) ile birleştirme — 04.10.2026

Koordinatör isteğiyle `origin/043-grblhal-serial` (332ca0a5) normal merge commit ile alındı (rebase/force
push yok). Çakışmalar ve çözümleri:

- `mikrocam/machine/controller.py`: iki import birlikte; `_consume` önce grblHAL satır normalizasyonunu
  (043) sonra FluidNC yeniden başlama sessizlik takibini (044) uygular; `parse_status(..., grblhal=)`,
  boot işareti/serbest metin dalları ve hazır olunca `$I`+`$$` birlikte durur.
- `mikrocam/machine/fake.py`: `fake_firmware.DEFAULT_PROFILE`/`self.firmware` (043) korunur; FluidNC
  yardımcısı `self.firmware` ile seçilir; `hal_tlo_xy`, grblHAL durum biçimi ve FluidNC `FS`/kancaları birlikte.
- `tests/hardware/test_readonly_grbl.py`: `family_of` ile grblHAL lehçesi; aile FluidNC ise ek salt okunur
  makro/`$RI`/`$CD` sorguları. Koruma testindeki FluidNC sahte `read_query` imzası `grblhal=` kabul eder.
- `tests/test_firmware_controller.py`: hareket-kapalı profil listesinde yalnız `unknown` kalır.
- Belgeler: iki firmware satırı ve iki bölüm (`grblHAL kartları (043)`, `FluidNC (044)`), H043 + H044,
  hata matrisi dosya listeleri ve gönderim notu birleştirildi. FluidNC için 043 kod ipucu tablo kullanmaz
  (“code not documented for this firmware”; test eklendi).

| Kontrol (birleşik ağaç) | Sonuç | Kanıt |
| --- | --- | --- |
| Odaklı FluidNC + grblHAL + firmware + konsol + H2 koruma | 1255 PASS | yerel |
| Tam paket (offscreen; mimari 83, grblHAL fault suites 555, FluidNC matris 235 dahil) | 6971 PASS, 3 skip, 310 alt test, 434,97 s | `.venv/044-merge-full.log` |
| `pip check` | temiz | yerel |
| Masaüstü `tests/smoke_app.py` | exit 0; `MACHINE_FIRMWARE_GRBLHAL_MOTION_OK`, `MACHINE_FLUIDNC_JOG_OK`, `SHUTDOWN_OK`; yetim yok | `.venv/044-merge-smoke.log` |
