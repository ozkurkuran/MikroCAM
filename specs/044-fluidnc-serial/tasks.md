# Tasks: FluidNC seri (USB) desteği (044)

Girdi: [spec](spec.md), [plan](plan.md), [research](research.md). Testler uygulamadan önce yazılır
(anayasa V). `[P]` paralel yapılabilir. Hepsi FakeGRBL ile; gerçek seri port açılmaz.

## Faz 1 — Hazırlık

- [x] T001 Worktree `MikroCAM-fluidnc`, dal `044-fluidnc-serial` (base `origin/042-firmware-identification`),
  AGENTS.md untracked; IS_TAKIP satırı ve süreç kaydı.
- [x] T002 Birincil kaynak: bdring/FluidNC `v3.9.9` (3fd629d3) ve `v4.1.1` (fdc17a2c) sığ klon;
  research.md R1–R9 dosya:satır atıflarıyla.
- [x] T003 spec.md (3 story, FR-001…FR-012, UA-1…UA-10, tehlike analizi), plan.md (Constitution Check).

## Faz 2 — Önce testler (RED)

- [x] T004 [P] `tests/test_fluidnc_protocol.py`: sürüm kapısı, Macro baytlarının üç doğrulayıcıda reddi,
  salt okunur sorgu izin listesi, boot işareti/serbest metin, makro+`$RI` kaydı ve sorun metni,
  `StartupEvidence` (GRBL tek `$N`, FluidNC dört sorgu), TLO skaler/vektör, `$$` vekil doğrulaması.
- [x] T005 [P] `tests/test_fluidnc_controller.py`: iki profil ile tanıma ve hareket açılması; jog/sıfır/G54;
  dolu makro ve açık/doğrulanamayan `$RI` reddi; iş ve `$30/$32`; character counting reddi;
  hold/resume/stop baytları; kuyruk; probe grid ve TLO vektörü; konsol `$CD`/`$N`; bilinmeyen ana
  sürüm; port açılışı boot dizisi; boşta reboot (varsayılan/özel karşılama); iş sırasında özel
  karşılama; jog sırasında boot işareti; GRBL'de serbest metin; 4 eksen/boş `A:`; `M56`; durdurma yolları.
- [x] T006 [P] `tests/test_fluidnc_fault_matrix.py`: C1 matrisi + job/manual-stop/probe/console
  adversarial + machine controller paketlerinin FluidNC varsayılan profiliyle yeniden toplanması.
- [x] T007 [P] `tests/test_fluidnc_wire_journeys.py`: D1 GRBL yolculuklarının FluidNC'de aynı sonuca
  ulaşması; tek izinli bayt farkı `$N` → dört FluidNC sorgusu.
- [x] T008 [P] `tests/test_hardware_readonly_guard.py`: FluidNC envanter sorguları ve cevapları.
- [x] T009 D1 testlerinde FluidNC hareket-kapalı beklentisinin D3 sonucu olarak güncellenmesi.
- [x] T010 RED kaydı: 4 toplama hatası + 83 FAIL / 72 PASS (`.venv/044-red*.log`).

## Faz 3 — US1: tanıma, boot/reset ve manuel hareket (P1)

- [x] T011 `mikrocam/machine/fluidnc.py` saf modül.
- [x] T012 `mikrocam/machine/startup_evidence.py` ve `manual_control.py` başlangıç adımı.
- [x] T013 `firmware.py`: `_PROFILES[FLUIDNC]` `motion_supported=True`, `_fluidnc()` 3.x/4.x kapısı.
- [x] T014 `manual_protocol.py`: beş salt okunur FluidNC sorgusu izin listesine; v4 TLO vektörü.
- [x] T015 `firmware_control.py`: `restarting`, `chatter`, `settled`, `fluidnc`.
- [x] T016 `controller.py`: boot işareti ve FluidNC serbest metin dalları, `_restart`, hazır olunca
  `$I`+`$$`, yeniden başlarken poll zaman aşımının konsol nedenselliğini bozmaması.
- [x] T017 `fake_fluidnc.py`, `fake.py`, `fake_firmware.py`: `fluidnc`/`fluidnc3`, boot simülasyonu.

## Faz 4 — US2: iş, kuyruk, probe (P1)

- [x] T018 `job_control.py`: `StartupEvidence` ve FluidNC `$$` doğrulaması.
- [x] T019 `probe_control.py`: `StartupEvidence`.
- [x] T020 Character counting'in FluidNC'de bütçe yokluğuyla reddi (D1 kapısı; test).

## Faz 5 — US3: tanı, saha ve matris (P2)

- [x] T021 Konsol `$CD` (yalnız FluidNC), FluidNC'de `$N` reddi; UI listesi.
- [x] T022 Hotfix (önce-test): konsol `$$` cevabında `$130-$132` satırları birim sayılmaz.
- [x] T023 `tests/hardware/test_readonly_grbl.py`: `$I` FluidNC ise makro/`$RI`/`$CD` salt okunur sorguları.
- [x] T024 `docs/MACHINE_CONTROL.md` FluidNC bölümü; `docs/GRBL_STREAMING.md`, `docs/MACHINE_CONSOLE.md`.
- [x] T025 `docs/hardware/GRBL_VALIDATION.md` H044 senaryoları ve matrisi NOT_RUN.
- [x] T026 `docs/MACHINE_FAULT_MATRIX.md` FluidNC satırı ve test dosyası eşlemesi.

## Faz 6 — Doğrulama ve teslim

- [x] T027 Odaklı testler + `tests/architecture` + `pip check`.
- [x] T028 Tam paket (offscreen) ve masaüstü `tests/smoke_app.py` (120 s watchdog).
- [x] T029 validation.md (RED/GREEN, kanıt, WAITING); IS_TAKIP güncellemesi.
- [ ] T030 Commit/push, PR (main hedefli, #44'e bağımlı), son-head Windows CI; merge yok.
