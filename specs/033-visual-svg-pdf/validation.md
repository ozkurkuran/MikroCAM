# Validation

check-status: PASS / WAITING.

SVG/PDF/Gerber source desteği ve native CAM PASS. B01/B10binary notice/packaging kabulünün alt kanıtı WAITING; source desteğini binary release diye raporlama.
2026-10-04: B01/B10 ikili paket alt kabulü 040 ile PASS (aşağıda); LightBurn G02 ve Release yayını ayrı/WAITING.

Base: c5a666cfb090aa5671f335471c209c4809246726; branch032-visual-interlace; local checkpoint (commit recorded in central IS_TAKIP).
Tested source/notice checkpoint: `77899fec9b5b14b87485c5be6c34bc6e6f79af92eee28e7dc815c6e06468334e`.
Manifest: `.venv/visual-resume-source.json` (201 files SHA256). Runtime/config hashes are unchanged from the prior native API checkpoint; notice inventory and tests are included in this new full run.

| Kontrol | check-status | Kanıt |
| --- | --- | --- |
| Final fullregression + architecture/growth/notices | PASS |5746test,310subtest,3skip,11existingwarning,306.23s; `.venv/visual-resume-final-regression.log` and JUnit; exit0, source unchanged |
| UI/recipe API sonrası ilgili | PASS |27test/4.45s; public hints tamamlandı |
| Native realCAM3formats/project/render/shutdown | PASS |`.venv/visual-api-final-native.log`; source/project roundtrip ve normal shutdown markers; exit0 |
| Module600/function80/publictypehint check | PASS |AST scan; violations=[] |
| Reviewable demo | PASS |600×360,508DPI,N3; PNG mode1, logical union=master, nativeappliedFalse |
| Markdown local links/fences | PASS |Broken=[]; typed source mutation check=[] |
| LightBurn native Open/Save/Preview | WAITING / NOT_RUN |G02dependency; no real program/fixture/version/device supplied |
| Binary installer/release audit | PASS (B01/B10) / WAITING (yayın) | 040 ikili paket: resvg_py+Qt PDF dondurulmuş bitmap/SVG/PDF offscreen+native PASS, crate/Qt bildirimleri pakette; Release yayını kullanıcı kararı |
| Source publication / delivery record | PASS |[PR#36](https://github.com/ozkurkuran/MikroCAM/pull/36) is open; its Checks and timeline record hosted CI and remote merge state. Local source commit d77a7cb1 is verified |
| Physical machine/laser | NOT_RUN |No COM/USB/emission; outside file-generation scope |

Detailed40acceptance mapping: [matrix](../../docs/design/visual-interlace/validation.md).
Use current source/proof; old5669 and eec55744 checkpoints are separate history.

## 2026-10-03 resume verification

The first resume run used the older repro-a interpreter and failed seven SVG-dependent
tests because resvg_py was absent (5739 passed/7 failed). That FAIL/JUnit is retained.
The actual worktree .venv passed pip check and all seven cases, then the complete
suite passed5746 tests/310subtests/3skips in306.23s. No product-code change or
test skip was used to remove the failures. The201-file checkpoint stayed unchanged.

Two historical vector-only .lbrn2 projects were discovered; they do not close G02.
Current executable/device and a real embedded Image fixture remain required.
Native LightBurn and binary-release acceptance remain WAITING/NOT_RUN.

## Source publication and local main

[PR#36](https://github.com/ozkurkuran/MikroCAM/pull/36) publishes source commit
d77a7cb1. The current PR head, hosted checks and merge result are recorded by
GitHub; previous NOT_RUN/local-only statements retain their checkpoint dates.
Local main separately passed192 visual tests/20.67s and a fresh native desktop
journey/47.94s with normal shutdown, using the SHA-verified resvg_py0.5.0 wheel.
No native LightBurn or binary-release acceptance changed.

## 2026-10-04 B01/B10 binary acceptance (spec 040)

- **B01 (T001):** temiz `.venv/build` ve `.venv/test` ortamlarında `--only-binary=:all:` ile
  `resvg_py==0.5.0` (cp310-abi3-win_amd64, SHA256 `1f6b8956c4143dbfe107bcd35799d0dfd778a40a8cd537893c0bf489898a6c3c`)
  derleyicisiz kuruldu; `pip check` PASS. Statik çizim/clipPath/delik renderı
  `tests/test_visual_svg_pdf.py` 20 PASS. Paketleme denemesi: PyInstaller 6.22.3 paketinde
  `resvg_py` `.pyd` kurulu wheel RECORD karmasıyla birebir; dondurulmuş SVG kaynağı
  hazırlandı/kaydedildi/açıldı. Lisans: wrapper + 75 crate/152 bildirim pakette `licenses/`.
  Renderer değişimi yapılmadı. Wheel build provenance upstream'de yok (404) — kayıtlı açık.
- **B10 (T010):** dondurulmuş `MikroCAMSmoke.exe` (sevk edilen `MikroCAM.exe` ile aynı PYZ) içinde
  uygulama açılışından sonra `resvg_py` ve `PyQt6.QtPdf` yüklenmemiş (lazy), bitmap+SVG+PDF
  aynı pipeline'dan hazırlanıp JSON'a kaydedildi/açıldı, proje taşıyıcısı kaydedilip proje
  yeniden açıldı (maske SHA eşit), normal kapanış. Offscreen ve gerçek masaüstü (OpenGL render)
  PASS. Qt PDF (PDFium ve bağımlılıkları) Qt 6.11.2 attribution sayfalarıyla pakette.
  PDF vektör çıkarma kapsamı eklenmedi. Kanıt: [040 validation](../040-packaging-windows/validation.md).
