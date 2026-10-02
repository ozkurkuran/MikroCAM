# Uygulama teslim kaydı ve değişen dosyalar

2026-10-02. Hedef `E:/VSCode/Flatcam/MikroCAM-visual-interlace`, dal032-visual-interlace,
base `c5a666cf`. **Yerel V1/V2 kodu hazır; native LightBurn hedefi tamamlanmadı.**
Main/push/PR/CI/merge yapılmadı; altın referans aynı kaldı.

## Tasarım özeti

Bitmap/SVG/PDF veya optional Gerber ROI tek fiziksel grid'e gelir; tek immutable
ana maske üretilir. Grupk `r%N==k` satırlarını aynı tam boyutlu beyaz tuvale taşır.
N=1aynı maske; N=1..8, mixed deterministik bit reversal. Başlangıç satırı0üsttedir;
boş satırlar yeniden indekslenmez. N grup bir tur; R tur sırası ve istenen bekleme
plan/kayıtta tutulur. Gerçek Image taraması native LightBurn'e aittir; G02kanıtı yok.

## Değişen dosyalar

| Alan | Dosyalar |
| --- | --- |
| Tek legacy bağlantı | `appMain.py` (+6 menü satırı) |
| Core | `mikrocam/core/{visual,visual_normalize,visual_interlace,visual_preview,geometry_visual,interlace_job}.py` |
| Source dispatch | `mikrocam/importers/visual_source.py` |
| Laser data/I/O | `mikrocam/laser/{visual_plan,visual_recipe,visual_files}.py`, `visual_recipe.schema.json` |
| Codec/host bridge | `mikrocam/bridge/{visual_bitmap,visual_svg,visual_fonts,visual_png,visual_workflow,visual_recipe,visual_project,visual_host,visual_geometry,visual_export}.py` |
| Qt UI | `mikrocam/ui/{visual_interlace_panel,visual_worker,visual_pdf,visual_preview,visual_errors}.py` |
| Optional dependencies | `requirements-visual.txt`, `requirements-image.txt`, `.github/workflows/ci.yml` installextra |
| Notice records | `THIRD_PARTY_LICENSES/{inventory.json,README.md}`, `resvg-py/0.5.0/{wheel,sdist,rust-crates}/`; exact source lock +152 original notices |
| Feature tests | `tests/test_visual_{core,interlace,bitmap,recipe,svg_pdf,geometry,export,ui,reference,sources_equivalence,notices}.py`;192 new cases |
| Native smoke | `tests/smoke_visual_app.py`;120 s watchguard, owned app only |
| Golden cases/demo | `tests/reference/visual/reference-cases.json`, `docs/examples/visual-interlace/` |
| Specs | `specs/{032-visual-interlace,033-visual-svg-pdf,034-lightburn-image-project,035-interlace-cycle-controls}/{spec,plan,tasks,validation}.md` |
| User docs | `docs/{ROADMAP.md,visual-interlace.md,lightburn-compatibility.md}` |
| Architecture | `docs/design/visual-interlace/`README/spec/plan/model/API/nativecontract/tasks/validation/ui-tr/research/handoff/analysis/targetintegration/implementation |

UntrackedAGENTS.md yalnız merkezi takip talimatını worktree'ye taşır; ürün dosyası değildir.
Merkezi takip main'deki `docs/IS_TAKIP.md`; ayrı ledger kopyası veya kullanıcı dosyası
taşınması yoktur. SVG/circuit demo kendi sentetik çizimidir; orijinal kullanıcı görseli
üzerine yazılmadı. Mevcut vektör laser/interlace, Placement/Recipe ve CAM nesne türleri korunur.

## Testler ve kanıt

[40senaryo eşlemesi](validation.md), [Türkçe ekran metinleri](ui-tr.md),
[gerçek tip/sınırlar](target-integration.md), [güncel görevler](tasks.md).
`eec5` kaynağı full5744test+310 subtest PASS,3 skip,11existingwarning458.19 s. Typed API
son kaynak `8fefc0d0`:27UI/recipe PASS; full PASS; native exit0 PASS.
Kaynak dosya SHA manifest'i `.venv/visual-api-final-source.json`; eski PASS değişmiş
kaynağa otomatik taşınmaz. Final sonucu validation dosyaları belirler.

## İncelenebilir örnek

[600×360/508DPI/N3 ZIP](../../examples/visual-interlace/demo-interlace-N3.zip),
[renkli birleşim](../../examples/visual-interlace/combined-preview.png),
[demo notu](../../examples/visual-interlace/README.md). Master13588siyah piksel;
her grup96aktif satır. ZIP native LightBurn dosyası değildir; manifest bunu açık belirtir.

## Kalan işler

G02 gerçek LightBurn version/device/app/saved fixture bilgisi bekleniyor; C01–C08
exporter ve gerçek FileOpen→Save→Open→Preview yapılmadı. Dwell, white-row skip,
source-row parity ve R*N layercapacity fiziksel Image yürütümü olarak doğrulanmadı.
75 exact Rust crate kaynak notice kapsamı tamam; wheel build provenance ve nihai binary bundle denetimi açık. PNG/JSON/proje başarıları tam
LightBurn ürün teslimi yerine geçmez. [Uyumluluk tablosu](../../lightburn-compatibility.md).

Son full:5744test+310alt test PASS/509.30s;3skip/11baseline warning. Code/config fingerprint `8fefc0d0bccc6c5b1c29aa219a595f0c5047d262569eb7200c24738cbbdb3c8c`. Yerel source hash'leri son koşu sonrası aynı. Native son API PASS.

## 2026-10-03 — resumed checkpoint

Complete suite PASS exit0: **5746 tests,310subtests,3skips,11existing warnings,306.23s**.
Log: `.venv/visual-resume-final-regression.log`; JUnit: `.venv/visual-resume-final-pytest.xml`.
Source/notice checkpoint: `77899fec9b5b14b87485c5be6c34bc6e6f79af92eee28e7dc815c6e06468334e`,201 SHA-verified files.
`.venv/visual-resume-final-result.json` proves the checkpoint stayed unchanged.
The actual worktree `.venv/Scripts/python.exe` passed pip check; seven SVG-dependent
cases first failed under the older repro-a interpreter, then passed in the correct
environment before this full run. Both results are retained as separate evidence.

The prior native menu/source/project/OpenGL/shutdown evidence remains applicable
to unchanged runtime/config files; it was not rerun or relabelled as a new native test.
Notice inventory and the two added notice tests are covered by this fresh full suite.
Historical5744-test records above remain historical rather than the current full result.

A local source checkpoint preserves V1/V2 and their tests/specs/notice records.
The commit is recorded in the central IS_TAKIP after git verifies it.
Push/PR/hosted CI/main delivery remain NOT_RUN. Two real historical vector-only
projects provide limited format metadata; they are not Image fixtures. Current
LightBurn executable/device/embedded Image evidence and native V3/V4 remain open.
No complete binary-release audit or complete .lbrn2 product delivery is claimed.
