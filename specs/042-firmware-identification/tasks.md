# Tasks: Firmware tanıma (042)

Testler uygulamadan önce gelir (anayasa V). `[P]` paralel yapılabilir.

## Faz 1 — Hazırlık

- [ ] T001 spec/research/data-model/plan/tasks yaz; FR-001…FR-014 görevlere eşle; analyze (kritik bulgu 0).
- [ ] T002 Değiştirilmemiş main `70800e5b` üzerinde 13 GRBL 1.1 FakeGRBL senaryosunun altın TX izini üret
      (`tests/firmware_wire_scenarios.py`, `tests/fixtures/grbl11_wire_golden.json`).

## Faz 2 — Önce testler (RED)

- [ ] T003 [P] [US1/US3] `tests/test_firmware_identification.py`: birincil kaynak örnekleriyle sınıflandırma,
      çelişki/bozuk/limit, karşılama ve tutarlılık, aile profilleri, kayıt doğrulaması (FR-003/004/006/011).
- [ ] T004 [P] [US1/US2] `tests/test_firmware_controller.py`: bağlantı bayt sırası, dört Fake profili, PENDING
      kapısı, `error:`/timeout/sıra bozulması, reset tutarlı/tutarsız, `GrblHAL` reset, disconnect temizliği,
      stop yolu, wire log kanıtı (FR-001/002/005/007/008/009/012).
- [ ] T005 [P] [US2] `tests/test_firmware_wire_preservation.py`: altın izler + beklenen kimlik eklemesi (SC-001).
- [ ] T006 [P] [US3] C3 bütçe kapısı testleri: OPT'siz GRBL, VER değişimi, bütçe 128 (FR-010).
- [ ] T007 [P] [US1] `tests/test_machine_firmware_ui.py`: firmware satırı metni ve hareket düğmeleri (FR-013).
- [ ] T008 RED koşusunu kaydet (validation.md, log yolu).

## Faz 3 — Uygulama

- [ ] T009 [US1] `mikrocam/machine/firmware.py`: enum, kayıt, gözlem, saf sınıflandırma, aile profilleri.
- [ ] T010 [US1] `mikrocam/machine/firmware_control.py`: tek `$I` koordinatörü.
- [ ] T011 [US1] `models.py` snapshot alanı; `controller.py` connect/reset/consume/expire bağlantısı.
- [ ] T012 [US2] `manual_control.py` hareket kapısı; `console_control.py` PENDING kapısı.
- [ ] T013 [US3] `job_control.py` C3 bütçe ve VER eşleşmesi.
- [ ] T014 [US1] `fake_firmware.py` + `fake.py` profil seçimi (varsayılan baytlar aynı).
- [ ] T015 [US1] `mikrocam/ui/machine_firmware.py` + `machine_panel.py` firmware satırı.
- [ ] T016 [US2] Mevcut testlerde bağlantı baytı/`$I` sayısı varsayımlarını UA-1'e göre güncelle; her
      değişikliği validation.md'de listele.
- [ ] T017 [US1] `tests/smoke_app.py` makine yolculuğunda firmware satırı ve grblHAL hareket kapısı.

## Faz 4 — Belgeler

- [ ] T018 [P] `docs/MACHINE_CONTROL.md` firmware tanıma bölümü; `docs/GRBL_STREAMING.md` bütçe kaynağı.
- [ ] T019 [P] `docs/hardware/GRBL_VALIDATION.md` H042 senaryoları NOT_RUN (FR-014).
- [ ] T020 [P] `docs/MACHINE_FAULT_MATRIX.md` firmware tanıma satırı.

## Faz 5 — Doğrulama ve teslim

- [ ] T021 Odaklı + `tests/architecture` + `pip check`; modül ≤600 / fonksiyon ≤80 satır denetimi.
- [ ] T022 Tam paket (offscreen) ve yerel masaüstü `tests/smoke_app.py` (120 s watchdog).
- [ ] T023 validation.md ve merkezi `docs/IS_TAKIP.md` kaydı.
- [ ] T024 Commit, push, PR; son-head Windows CI; birleştirme yok.

## Bağımlılıklar

T001→T002→(T003…T007)→T008→T009→T010→T011→T012→T013→T014→T015→T016→T017→(T018…T020)→T021→T022→T023→T024.

## FR eşlemesi

FR-001 T004/T011 · FR-002 T004/T010 · FR-003 T003/T009 · FR-004 T003/T011 · FR-005 T004/T011 ·
FR-006 T003/T009/T011 · FR-007 T004/T012 · FR-008 T004/T012 · FR-009 T004/T012 · FR-010 T006/T013 ·
FR-011 T003/T009 · FR-012 T004/T014 · FR-013 T007/T015/T017 · FR-014 T019.
