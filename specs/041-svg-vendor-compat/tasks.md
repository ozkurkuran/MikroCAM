# Görevler: SVG üretici uyumluluğu

Girdi: spec.md, plan.md, research.md. 3 hikâye, 28 görev; testler uygulamadan önce (RED).

## Hazırlık
- [x] T001 PR #41 dalından worktree, AGENTS.md (untracked), merkezi takip satırı.
- [x] T002 Gerçek Proteus dosyasının ham koordinat incelemesi ve standart araştırması (research.md).

## US1 — Standart DOCTYPE (P1)
- [x] T003 [US1] `tests/test_svg_doctype.py`: SVG 1.0/1.1 kabul, DOCTYPE'sız sürümle aynı malzeme,
  önsöz yorum/PI/BOM, tek/çift tırnak, ağ erişimi engelli ortamda başarı.
- [x] T004 [US1] Aynı dosyada saldırgan örnekler: iç alt küme (boş, entity, parametre entity,
  milyar-kahkaha), yalnız SYSTEM, bilinmeyen public/system, kök adı `html`, küçük harf, kök sonrası
  ve ikinci DOCTYPE, tanımsız entity başvurusu → açık mesajla hata.
- [x] T005 [US1] `tests/test_cad_source_svg.py`: 020 algılayıcısının SVG 1.0'ı kabul etmesi ve aynı
  saldırgan kümeyi reddetmesi.
- [x] T006 [US1] `mikrocam/importers/svg_doctype.py` uygulaması.
- [x] T007 [US1] `svg_document._parse_xml` ve `cad_svg_source._text` paylaşılan modüle bağlanır.

## US2 — non-scaling stroke (P1)
- [x] T008 [US2] `tests/test_svg_non_scaling_stroke.py`: `non_scaling_stroke_width` benzerlik/
  yansıma/döndürme, eşit olmayan ölçek ve eğiklik hatası.
- [x] T009 [US2] Analitik içe aktarma: viewBox 0,1 mm/birim, `rotate`+`scale`, `use`, mutlak birim,
  flip; boyanmayan durumda eşit olmayan ölçek ve eğiklik altında malzeme eşitliği; bildirimler.
- [x] T010 [US2] Hata örnekleri: eşit olmayan `preserveAspectRatio="none"`, `skewX`, kök `transform`,
  `viewport`/`screen`, `non-scaling-size`, grup/`use`/kök üzerinde değer, bozuk değer; `inherit`.
- [x] T011 [US2] `core/svg_transform.non_scaling_stroke_width`.
- [x] T012 [US2] `svg_style` miras alınmayan `vector-effect`, `svg_document` genişlik ve bildirimler.
- [x] T013 [US2] `tests/test_svg_document.py` eski "vector-effect her zaman hata" parametreleri
  bilinçli olarak yeni sözleşmeye göre güncellenir (bypass testi `non-scaling-size` ile korunur).

## US3 — Proteus delikleri (P2)
- [x] T014 [US3] `tests/test_svg_drill_open_circles.py`: Z'siz dört kübik daire, iki yarım `A` yayı,
  ters yön, flip → aday; 3/4 yay, uç boşluğu 0,001 mm, iki tur, iki alt yol → aday değil.
- [x] T015 [US3] Poligon pad: eş merkezli dikdörtgen/sekizgen destek, en küçük alan seçimi; kaydırılmış
  pad, büyük döküm, payı yetmeyen pad, clip'li pad, beyaz pad → destek yok; sekizgen asla aday değil.
- [x] T016 [US3] `tests/test_vendor_export_fixtures.py`: gerçek Proteus Geometry/Gerber içe aktarma
  başarılı; drill incelemesi 25 aday, merkezler testte ham `d` metninden bağımsız hesaplanır, Ø1,00 mm,
  flip açık/kapalı; eski "vector-effect hatası" testi kaldırılır.
- [x] T017 [US3] `core/svg_drill_circles.py` çakışan uç kuralı.
- [x] T018 [US3] `core/svg_drills.py` poligon pad desteği ve bildirim metni.

## Gerçek kanıt ve belgeler
- [x] T019 Gerçek Illustrator DOCTYPE'lı dışa aktarımın lisans/provenance ile eklenmesi ve testi
  (bulunamazsa arama kaydı).
- [x] T020 Sınırlı Illustrator kabul ölçümü (ağ ölçeği gerekiyorsa atlanır, kayıt edilir).
- [x] T021 `docs/SVG_IMPORT.md`, `docs/SVG_DRILLS.md`, `docs/CAD_SOURCE.md` güncellemesi.
- [x] T022 016/018/019/020 `validation.md` notlarının yeni kanıta bağlanması; 016/018 sözleşme notu.
- [x] T023 `THIRD_PARTY_CHANGES.md` ve `tests/reference/README.md` (yeni fixture varsa).

## Doğrulama ve teslim
- [x] T024 Odaklı testler, `tests/architecture`, `pip check`, 600/80 satır sınırı.
- [x] T025 Tam test paketi (offscreen) ve masaüstü `tests/smoke_app.py`.
- [x] T026 `validation.md` sonuçları.
- [x] T027 Commit/push, PR (PR #41'e bağımlılık notu), final-head Windows CI.
- [x] T028 Merkezi takip dosyasına sonuç satırları (merge yok).
