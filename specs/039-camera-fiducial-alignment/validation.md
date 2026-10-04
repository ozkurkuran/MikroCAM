# Validation — Fiducial hizalama

Base origin/main `70800e5b`; dal `039-camera-fiducial-alignment`; Windows 11, CPython 3.13.
Yeni bağımlılık yok; legacy satır değişikliği 0. Kanıt logları ana checkout'un yok sayılan
`.venv/` dizinindedir (`fiducial-*.log`, `fiducial-*.xml`, `fiducial-smoke.png`).

## Test-first

- RED: 7 yeni test dosyası; 23 FAIL + 6 toplama hatası (modüller yok) — `fiducial-red.log`.
- GREEN (yeni testler): 134 PASS — `fiducial-green.log`.
- İlgili placement/motion/preflight/dry-run/auto-level/laser JSON/görsel reçete/lazer planı/
  job hazırlık-hassasiyet-UI/levelling handoff: 595 PASS — `fiducial-related.log`.
- `motion_bounds` tek genel yola geçti; mevcut rijit ve aynalı yay testleri değişmeden geçti.
- Mimari testler (import sınırları, legacy büyüme, runtime metadata): 83 PASS. `pip check`: temiz.
- Yeni modüller ≤ 316 satır, en uzun fonksiyon 59 satır (`PreflightPanel._build_ui`, mevcut).

## Tam suite

Paylaşılan `repro-a` ortamı: 5934 PASS, 13 FAIL, 3 skip, 310 alt test PASS, 495.99 s
(`fiducial-full.log`/`.xml`). 12 başarısızlık opsiyonel `resvg_py` (requirements-visual)
bu ortamda kurulu olmadığı için görsel SVG testlerindedir; aynı 12 test değiştirilmemiş main
`70800e5b` checkout'unda aynı ortamla da başarısız (ortam kaynaklı). Kalan 1 test
(`test_large_program_completes_with_bounded_storage_and_prompt_cancellation`, <10 s sınırı)
paralel ajan yükü altında 11.4 s sürdü; tek başına 6.0 s (main'de 6.5 s) PASS.
Görsel ekstraları kurulu ana `.venv` ile bu 5 görsel dosya + preflight: 118 PASS.
Görsel ekstraları kurulu, sabitlenmiş ana `.venv` ile kaynak commit `960f8b77` üzerinde
tam suite: **5947 PASS, 0 FAIL, 3 skip, 310 alt test PASS, 11 mevcut uyarı, 539.66 s, exit 0**
(`fiducial-full-mainenv.log`/`.xml`).

## Masaüstü

`tests/smoke_app.py` exit 0 PASS (`fiducial-native.log`). Yeni `tests/smoke_fiducial.py`
yolculuğu gerçek uygulama dock'larında: 4 noktalı affine fit → preflight'a aktarım → analiz →
Aligned job (G54 FakeGRBL WCO'dan) → Machine'e aktarım → FakeGRBL ile tamamlanma; işaret
`FIDUCIAL_ALIGNED_JOB_COMPLETE_OK`. Ekran görüntüsü `fiducial-smoke.png` incelendi. Diğer
bütün smoke işaretleri ve normal kapanış PASS.

## Bekleyen (WAITING)

- Kamera görüntüsü yakalama ve fiducial algılama: gerçek kamera yok; arayüz eklenmedi.
- Gerçek GRBL makinesinde yakalama, hizalanmış iş ve dry-run doğrulaması yapılmadı.
- Fiziksel doğruluk (mekanik boşluk, homing tekrarlanabilirliği) ölçülmedi.
