# Validation: Firmware tanıma (042)

Tarih: 2026-10-04 (Europe/Istanbul). Worktree `E:\VSCode\Flatcam\MikroCAM-firmware-id`, dal
`042-firmware-identification`, taban `origin/main` `70800e5b`. Python: ana `.venv` (CPython 3.13,
tam `requirements-dev`). Gerçek seri port açılmadı; bütün makine kanıtı FakeGRBL'dir.

## Önce-test (RED)

| Adım | Sonuç | Kanıt |
| --- | --- | --- |
| Altın GRBL 1.1 TX izleri | Değiştirilmemiş main `70800e5b` üzerinde 13 senaryo üretildi | `tests/fixtures/grbl11_wire_golden.json`, commit `f622412e` |
| Yeni testler, uygulama yok | 3 toplama hatası (`mikrocam.machine.firmware` yok) | worktree `.venv/042-red.log` |
| Altın iz karşılaştırması, uygulama yok | 13 FAIL / 1 PASS (`$I` henüz gönderilmiyor) | aynı log |

## GREEN ve ilgili paketler

| Kontrol | Sonuç |
| --- | --- |
| `test_firmware_identification.py` | 50 PASS |
| `test_firmware_controller.py` | 22 PASS |
| `test_firmware_wire_preservation.py` (13 senaryo + kapsam) | 14 PASS |
| `test_machine_firmware_ui.py` (offscreen Qt) | 3 PASS |
| İlgili makine/iş/probe/konsol/kuyruk/C3/levelling paketi | 1797 PASS, 41 alt test (`.venv/042-related-2.log`) |
| `tests/architecture` | 83 PASS |
| `pip check` | No broken requirements |
| Modül/fonksiyon boyutu | En büyük yeni modül 310 satır; en uzun değişen fonksiyon `MachinePanel.__init__` 63 satır |
| Legacy büyümesi | 0 satır (legacy dosyaya dokunulmadı) |

## Tam paket ve masaüstü

| Kontrol | Sonuç |
| --- | --- |
| Tam paket (`QT_QPA_PLATFORM=offscreen`, ana `.venv`, kod commit'i `a92ed66e` ile aynı ağaç) | **PASS**: 5902 passed, 3 skipped, 310 alt test, 336,63 s, exit 0 (`.venv/042-full.log`, `.venv/042-full.xml`) |
| Yerel masaüstü `tests/smoke_app.py` (native Qt/OpenGL, 120 s watchdog) | **PASS**: exit 0, 58 s; `MACHINE_FIRMWARE_GRBLHAL_LOCKED_OK`, `MACHINE_READ_ONLY_OK`, `MACHINE_JOG_G54_CANCEL_OK`, `CHAR_COUNTING_QUEUE_COMPLETE_OK`, `SHUTDOWN_OK` (`.venv/042-smoke.log`); yetim worker yok. `.venv/machine-smoke.png` Firmware satırı: `GRBL 1.1h; RX 128 B; char-counting budget 128 B; motion enabled` |
| Son-head Windows CI | PR üzerinde; sonuç PR ve merkezi `docs/IS_TAKIP.md` kaydındadır (eski head PASS yeni head'e aktarılmaz) |

## UA-1 nedeniyle güncellenen mevcut assert'ler

Davranış gevşetilmedi; yalnız bağlantıya eklenen salt okunur `$I` sayıldı. Diğer bütün GRBL 1.1
baytları altın izlerle ayrıca sabitlendi.

| Dosya | Değişiklik |
| --- | --- |
| `tests/test_machine_controller.py` | `session()` elle beslenen oturumda önce GRBL `$I` cevabını verir; bağlantı TX `[$I, $$, ?]` |
| `tests/test_machine_fault_matrix.py` | `connect` sahibi için `$I` cevabı ayar ACK testinden önce verilir |
| `tests/test_char_counting.py` | `$I` sayıları: +1 oturum kimliği (1→2, 3→4; “hiç yok”→1) |
| `tests/test_console_control.py` | Konsol `$I` gönderilmedi kanıtı: sayı 1 (oturum); yeniden bağlantı log'u `[$I, $$, ?]` |
| `tests/test_console_adversarial.py` | Aynı; tamamlanan `$I` kayıtları 2 (oturum + konsol) — önceki `any` daha zayıftı |
| `tests/test_machine_manual_controller.py`, `tests/test_machine_ui.py` | Salt okunur izin kümesine `$I` |
| `tests/smoke_app.py`, `tests/smoke_queue.py` | Küme/sayı aynı şekilde; grblHAL kilit yolculuğu ve GRBL firmware satırı eklendi |

## Kapsam dışı / devredilenler

- grblHAL/FluidNC hareket profilleri, durum/alarm farkları, `0x87`, RX bütçeleri: spec 043/044.
- FluidNC özel `$Start/Message` reset tespiti (UA-8): D3.
- `tests/hardware/test_readonly_grbl.py` (H2) `$I` satırlarını GRBL'e özgü sıkı parser ile denetler;
  grblHAL/FluidNC kartında bu operatör testi başarısız olabilir. D2/D3 bu aracı aileye göre genişletmeli.
- Bulgu (C3, değiştirilmedi): `job_stream.verified_capacity` OPT harf deseni GRBL kaynağındaki `+` ve
  `0` harflerini kabul etmez; bu seçeneklerle derlenmiş kartta karakter sayımı güvenli tarafta
  reddedilir. Ayrı hotfix önerisi.

## Fiziksel doğrulama

H042-1…H042-7 (`docs/hardware/GRBL_VALIDATION.md`) **NOT_RUN / WAITING**. Gerçek GRBL/grblHAL/
FluidNC kartı yok; hiçbir hücre geçti sayılmaz.
