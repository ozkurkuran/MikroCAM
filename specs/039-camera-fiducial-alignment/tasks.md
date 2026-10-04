# Tasks — Fiducial hizalama

## Setup
- [x] T001 Merkezi takip, anayasa, roadmap, geliştirme belgeleri; izole 039 worktree.
- [x] T002 Spec; açık noktalar uygulama varsayımı UV1–UV9 (kullanıcı kararı değil).
- [x] T003 Research, data model, plan ve Constitution Check.
- [x] T004 Analiz: 3 story / 15 FR / görevler ve tehlike analizi tutarlılığı.

## US1 — Hizalama hesabı (testler önce)
- [x] T005 [test] `Placement.affine` doğrulama, matrix, inverse, rigid_data testleri (RED).
- [x] T006 [test] Affine yay sınırları ve rijit yolun değişmediği testleri (RED).
- [x] T007 [test] Rijit/benzerlik/affine geri bulma, gürültü, ret ve degenerate testleri (RED).
- [x] T008 `Placement` affine genişletmesi ve `rigid_data`.
- [x] T009 `motion_bounds` affine elips ekstremumları.
- [x] T010 `fiducial.py` modelleri ve `fit_alignment`.
- [x] T011 Rijit formatlarda affine'in açık reddi (laser JSON, görsel reçete, export manifest).

## US2 — Set dosyası ve nokta toplama (testler önce)
- [x] T012 [test] Codec roundtrip, v1 fixture, sürüm/alan/birim ret testleri (RED).
- [x] T013 [test] FakeGRBL anlık görüntüsünden yakalama ve uygun olmayan durum testleri (RED).
- [x] T014 [test] Excellon/Gerber tasarım adayları bridge testleri (RED).
- [x] T015 `fiducial_codec.py` ve v1 fixture.
- [x] T016 `machine/fiducial_capture.py`.
- [x] T017 `bridge/fiducial_points.py`.

## US3 — İş hattına uygulama (testler önce)
- [x] T018 [test] Hizalanmış iş türetme: XY, yay kirişi, lineage, sınır, ret testleri (RED).
- [x] T019 [test] FakeGRBL akış, Stop, G54/G92 uyuşmazlığı, dry-run zinciri (RED).
- [x] T020 [test] Auto-level ve lazer planının aynı Placement'ı kullandığı testleri (RED).
- [x] T021 [test] Preflight kurulum hizalama modu ve paneller Qt testleri (RED).
- [x] T022 `aligned_job.py`.
- [x] T023 `preflight_setup.py` hizalama modu.
- [x] T024 `fiducial_panel.py`.
- [x] T025 `aligned_job_panel.py` + worker ve preflight düğmeleri.

## Delivery
- [x] T026 İlgili testler, mimari testler, pip check.
- [x] T027 Tam suite ve masaüstü smoke.
- [x] T028 Kullanıcı belgesi (docs/FIDUCIAL_ALIGNMENT.md) ve validation.md.
- [ ] T029 Commit, push, PR, final-head Windows CI (merge koordinatörde).
- [ ] T030 Merkezi takip son kaydı; kamera/fiziksel doğrulama WAITING.
