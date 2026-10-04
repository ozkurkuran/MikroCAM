# Tasks — 037 lazer reçete veritabanı

## Setup
- [x] T001 Merkezi takip, anayasa, roadmap, DEVELOPMENT okundu; `037-laser-recipe-db` worktree.
- [x] T002 spec.md; açık noktalar uygulama varsayımı UA1–UA6 olarak kaydedildi.
- [x] T003 research.md, data-model.md, plan.md (Constitution Check, Complexity Tracking).
- [x] T004 Analiz: 3 story / 12 FR / görev eşlemesi ve kapsam dışı (görsel panel, fiziksel kabul).

## US1 — seç ve kullan
- [x] T005 [test] `tests/test_laser_recipe_db.py`: model değişmezleri, ad/kimlik/referans, arama.
- [x] T006 [test] `tests/test_laser_recipe_db_store.py`: eksik dosya, atomik yazım, yeniden açma.
- [x] T007 [test] `tests/test_laser_recipe_db_ui.py`: malzeme/lens/makine ekleme, kaydet, ara, yükle.
- [x] T008 RED çalıştırması kaydı.
- [x] T009 `mikrocam/core/laser_recipe_db.py` model ve işlemler.
- [x] T010 `mikrocam/laser/recipe_db_store.py` depo ve ortak atomik yazım.
- [x] T011 `mikrocam/ui/laser_recipe_db.py` ince arayüz; Laser CAM paneline bağlama; bridge veri yolu.

## US2 — JSON reçetelerinin taşınması
- [x] T012 [test] `tests/test_laser_recipe_db_json.py`: strict v1 codec, migration, gelecek sürüm red.
- [x] T013 [test] schema1/schema2 içe→dışa aktarma bayt eşitliği; v1 altın dosyası.
- [x] T014 [test] UI çoklu JSON içe aktarma hep-ya-hiç ve dışa aktarma.
- [x] T015 `mikrocam/core/laser_recipe_db_json.py` codec + migration giriş noktası.
- [x] T016 `tests/test_files/laser_recipe_db_v1.json` altın dosya ve JSON Schema belgesi.
- [x] T017 `save_recipe_file` ortak atomik yazıcıya taşındı; mevcut testler korunur.

## US3 — tutarlılık
- [x] T018 [test] makine güncellemesinde yeniden doğrulama, kullanılan kayıt silme reddi,
  çakışma/replace, dış değişiklik ve bozuk dosyanın korunması.
- [x] T019 Çekirdek işlemlerde açık hata mesajları ve hep-ya-hiç davranışı.
- [x] T020 UI onay/hata yolu, salt okunur mod.

## Delivery
- [x] T021 İlgili laser/visual testleri, `tests/architecture`, `pip check`.
- [x] T022 Tam suite (offscreen) ve sonuç kaydı.
- [x] T023 `tests/smoke_app.py` veritabanı adımıyla gerçek masaüstü.
- [x] T024 Kullanıcı belgesi `docs/LASER_RECIPES.md`, validation.md, commit.
- [ ] T025 Push, PR, final-head Windows CI.
- [ ] T026 Merkezi takip son kaydı; birleştirme koordinatörde; fiziksel kabul WAITING.
