# Validation: grblHAL seri desteği (043)

Tarih: 2026-10-04 (Europe/Istanbul). Worktree `E:\VSCode\Flatcam\MikroCAM-grblhal`, dal
`043-grblhal-serial`, taban `origin/042-firmware-identification` (`164da247`, PR #44; birleştirme #44'ten
sonra). Python: ana `.venv` (CPython 3.13, tam `requirements-dev`). Gerçek seri port açılmadı; bütün
makine kanıtı FakeGRBL'dir.

## Ayrı hotfix (spec dışı)

| Adım | Sonuç | Kanıt |
| --- | --- | --- |
| GRBL `0`/`+` OPT harfleri (gnea/grbl `report.c:407`, `:419`) | RED 3 FAIL → GREEN; `test_job_stream`/C3/firmware 124 PASS | commit `04424f03` |

## Önce-test (RED)

| Adım | Sonuç | Kanıt |
| --- | --- | --- |
| Yeni dialect/kod testleri, uygulama yok | 2 toplama hatası (`mikrocam.machine.grblhal`, `firmware_codes` yok) | worktree `.venv/043-red.log` |
| Kimlik + controller testleri, uygulama yok | 35 FAIL / 15 PASS (geçenler D1'de zaten kapalı olan ret yolları ve konsol) | aynı log |

UI ipucu testleri (`test_machine_firmware_ui.py` son iki test), H2 grblHAL yardımcı testleri
(`test_hardware_readonly_grblhal.py`), her sahipte grblHAL reset testi ve grblHAL suite yeniden koşusu
uygulamayla aynı görevde, uygulamadan **sonra** yazıldı; RED kaydı yoktur.

## GREEN ve ilgili paketler

| Kontrol | Sonuç |
| --- | --- |
| `test_grblhal_identification.py`, `test_grblhal_dialect.py`, `test_grblhal_codes.py`, `test_grblhal_controller.py` | 134 PASS |
| `test_grblhal_fault_suites.py` (18 mevcut dosyanın değişmemiş testleri, FakeGRBL `grblhal` varsayılanı; 1 gerekçeli istisna) | 554 PASS |
| H2 yardımcıları (`test_hardware_readonly_guard.py`, `test_hardware_readonly_grblhal.py`) | 44 PASS, 1 skip (operatör testi) |
| GRBL 1.1 altın TX izleri (`test_firmware_wire_preservation.py`, D1) | değişmeden PASS |
| İlgili makine/iş/probe/konsol/kuyruk/C3/firmware/levelling/hardware paketi | 2807 PASS, 1 skip, 78 alt test (`.venv/043-related.log`) |
| `tests/architecture` | 83 PASS |
| `pip check` | No broken requirements |
| Modül/fonksiyon boyutu | En büyük değişen modül `controller.py` 530 satır; en uzun değişen fonksiyon `MachinePanel.__init__`/`FakeGRBL.__init__` 63 satır |
| Legacy büyümesi | 0 satır |

## Tam paket ve masaüstü

| Kontrol | Sonuç |
| --- | --- |
| Tam paket (`QT_QPA_PLATFORM=offscreen`, ana `.venv`, uygulama commit'iyle aynı kod ağacı; sonradan yalnız belge değişti) | **PASS**: 6602 passed, 3 skipped, 310 alt test, 382,68 s, exit 0 (`.venv/043-full.log`, `.venv/043-full.xml`) |
| Yerel masaüstü `tests/smoke_app.py` (native Qt/OpenGL, 120 s watchdog) | **PASS**: exit 0, 64 s; `MACHINE_FIRMWARE_GRBLHAL_MOTION_OK grblHAL 1.1f (build 20250101); RX 1024 B; char-counting budget 128 B; motion enabled`, `MACHINE_READ_ONLY_OK`, `MACHINE_JOG_G54_CANCEL_OK`, `CHAR_COUNTING_QUEUE_COMPLETE_OK`, `SHUTDOWN_OK` (`.venv/043-smoke.log`); yetim worker yok |
| Son-head Windows CI | PR üzerinde; sonuç PR ve merkezi `docs/IS_TAKIP.md` kaydındadır (eski head PASS yeni head'e aktarılmaz) |

## D1 varsayımı nedeniyle güncellenen mevcut assert'ler

D1 grblHAL hareketini bilerek 043'e kadar kapalı tutuyordu (D1 UA-2). Bu varsayımı sabitleyen satırlar
güncellendi; GRBL 1.1 baytları ve diğer davranışlar değişmedi.

| Dosya | Değişiklik |
| --- | --- |
| `tests/test_firmware_controller.py` | “desteklenmeyen profiller” parametresinden `grblhal` çıkarıldı (grblHAL retleri `test_grblhal_controller.py`'de); farklı firmware reset testi `…reidentifies_before_motion` adını aldı ve tanıma sonrası hareket açık bekler |
| `tests/test_firmware_identification.py` | tam grblHAL `$I` → hareket açık, bütçe 128; uzatılmamış cevap hareket kapalı |
| `tests/test_machine_firmware_ui.py` | uzatılmamış grblHAL gerekçesi “axis count”; panel grblHAL'de jog düğmesi açık |
| `tests/test_hardware_readonly_guard.py` | sahte `read_query` yeni `grblhal` anahtar sözcüğünü kabul eder |
| `tests/smoke_app.py` | `MACHINE_FIRMWARE_GRBLHAL_LOCKED_OK` yerine `MACHINE_FIRMWARE_GRBLHAL_MOTION_OK`: hareket açık + doğrulanmış jog |

## Kapsam dışı / devredilenler

- RX 1024'ün tamamını kullanan pencere (UA-2), `$I+` ile uyumluluk modu tanıma, 4+ eksen, lathe, MPG,
  SD akışı, otomatik rapor (`$481`) ve parser-state push için ayrı destek: kart ve saha kanıtı gerekir.
- `$10`/`$481` ayarlarını okuyup önceden uyarmak (bugün fail-closed işlem sırasında yakalanır).

## Fiziksel doğrulama

H043-1…H043-9 ve H042-2 (`docs/hardware/GRBL_VALIDATION.md`) **NOT_RUN / WAITING**. Gerçek grblHAL kartı
yok; H3 yapılmadı. Hiçbir fiziksel hücre geçti sayılmaz.
