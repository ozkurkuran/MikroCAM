# Tasks: grblHAL seri desteği (043)

Testler uygulamadan önce gelir (anayasa V). `[P]` paralel yapılabilir.

## Faz 0 — Ayrı hotfix (spec dışı)

- [x] T001 `tests/test_job_stream.py`: GRBL `report.c:407/:419` `0` ve `+` OPT harfleri (RED 3 FAIL).
- [x] T002 `job_stream.verified_capacity` harf kümesi; ayrı commit.

## Faz 1 — Hazırlık

- [x] T003 spec/research/plan/tasks; FR-001…FR-013 eşlemesi; analyze.

## Faz 2 — Önce testler (RED)

- [x] T004 [P] [US1/US2] `tests/test_grblhal_identification.py`: hareket kapısı (eksen, AXS, RT±, LATHE,
      seviye ≥1), bütçe 128, D1 uyumluluk modu Unknown (FR-001/002/003).
- [x] T005 [P] [US2] `tests/test_grblhal_dialect.py`: `parse_status` grblHAL kipi ve GRBL kipi
      değişmezliği; `normalize_query_line` `$G`/`$#`/`$$` tablosu (FR-004/005).
- [x] T006 [P] [US2] `tests/test_grblhal_codes.py`: alarm/hata anlam tabloları, alarm 10 ayrımı (FR-008).
- [x] T007 [P] [US1] `tests/test_grblhal_controller.py`: uçtan uca jog, G54, sıfır, iş (iki mod),
      pause/resume, stop, probe grid, kuyruk, konsol, dry run, reset, push raporlar, ret yolları
      (FR-001/003/005/006/007/011, SC-001/002).
- [x] T008 [P] [US3] `tests/test_grblhal_fault_suites.py`: seçili C1/adversarial testleri grblHAL
      varsayılanıyla (FR-010).
- [x] T009 [P] [US3] `tests/test_hardware_readonly_grblhal.py`: H2 yardımcıları grblHAL satırları (FR-012).
- [x] T010 [P] [US1] `tests/test_machine_firmware_ui.py`: grblHAL hareket açık metni; ipucu anlamı.
- [x] T011 RED koşusunu kaydet (validation.md).

## Faz 3 — Uygulama

- [x] T012 [US1] `firmware.py` grblHAL profili, `_grblhal()` kanıt kapısı, `_streaming_budget`.
- [x] T013 [US2] `grbl.parse_status(grblhal=...)`.
- [x] T014 [US2] `grblhal.py` lehçe fonksiyonu.
- [x] T015 [US1] `controller.py` lehçe kancası ve ayrıştırıcı bayrağı.
- [x] T016 [US1] `job_stream.verified_capacity` ek OPT alanları; `job_control` VER+OPT eşleşmesi.
- [x] T017 [US2] `firmware_codes.py` + `machine_panel.py` durum ipucu.
- [x] T018 [US3] `fake_firmware.py` grblHAL biçimleri; `fake.py` profil kullanımı ve varsayılan profil.
- [x] T019 [US3] `tests/hardware/test_readonly_grbl.py` aileye göre doğrulama.
- [x] T020 [US1] D1'in “grblHAL kapalı” test/smoke varsayımlarını güncelle; validation.md'de listele.
- [x] T021 [US1] `tests/smoke_app.py` grblHAL yolculuğu: hareket açık + jog.

## Faz 4 — Belgeler

- [x] T022 [P] `docs/MACHINE_CONTROL.md` grblHAL bölümü ve tablo; `docs/GRBL_STREAMING.md` bütçe.
- [x] T023 [P] `docs/hardware/GRBL_VALIDATION.md` H043 senaryoları NOT_RUN; H042-2 beklentisi.
- [x] T024 [P] `docs/MACHINE_FAULT_MATRIX.md` grblHAL satırı/yeniden koşu.

## Faz 5 — Doğrulama ve teslim

- [x] T025 Odaklı + `tests/architecture` + `pip check`; modül ≤600 / fonksiyon ≤80.
- [x] T026 Altın GRBL 1.1 izleri (`test_firmware_wire_preservation.py`).
- [x] T027 Tam paket (offscreen, arka plan) ve masaüstü `tests/smoke_app.py` (120 s watchdog).
- [x] T028 validation.md ve merkezi `docs/IS_TAKIP.md` kaydı.
- [x] T029 Commit, push, PR (#44'e bağımlı); son-head Windows CI; birleştirme yok.
- [x] T030 CI hatası varsa önce-test düzeltme ve yeniden koşu.

## Bağımlılıklar

T001→T002→T003→(T004…T010)→T011→T012→T013→T014→T015→T016→T017→T018→T019→T020→T021→(T022…T024)→
T025→T026→T027→T028→T029→T030.

## FR eşlemesi

FR-001 T004/T007/T012 · FR-002 T004/T012 · FR-003 T004/T007/T016 · FR-004 T005/T013/T015 ·
FR-005 T005/T007/T014/T015 · FR-006 T007 · FR-007 T007 · FR-008 T006/T010/T017 · FR-009 T007/T018 ·
FR-010 T008 · FR-011 T007/T008 · FR-012 T009/T019/T023 · FR-013 T026.

Analyze (2026-10-04): 13 FR'nin her biri en az bir test ve bir uygulama/belge görevine eşlendi;
kritik/yüksek bulgu yok. Terimler (lehçe, kanıt kapısı, UA-1…UA-10) spec/plan/tasks'ta tutarlı.
