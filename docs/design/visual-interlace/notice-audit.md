# SVG renderer kaynak ve lisans kanıtı

2026-10-02. **Kaynak notice kapsamı PASS; binary release denetimi WAITING.**
Bu kayıt runtime kodunu veya renderer sürümünü değiştirmez.

## Exact kaynak

- Wrapper: resvg_py 0.5.0; Windows cp310-abi3 wheel ve wrapper MIT metni önceki kayıtta korunur.
- [Resmi PyPI sürüm metadata](https://pypi.org/pypi/resvg-py/0.5.0/json) içindeki
  [exact sdist](https://files.pythonhosted.org/packages/2a/64/a24f8f29d8bf158e01f6ccad68a1366afd922dc0f0977cbd0c0aaa7a22f2/resvg_py-0.5.0.tar.gz)
  SHA256: `6d3bf8e866b4e129524d9432a809138b2d100931d8d635bc81294002abcdfd46`.
- Orijinal Cargo.lock SHA256:
  `578b2a28b47041de07b6722712aca776efdf8b1b1b2ac49e91f5e829df4ea70a`.
  Kilitli resvg/usvg sürümleri 0.48.1; tiny-skia 0.12.0.
- Cargo.lock, Cargo.toml, pyproject.toml ve LICENSE değişmeden
  [sdist kayıt klasöründe](../../../THIRD_PARTY_LICENSES/resvg-py/0.5.0/sdist/resvg_py-0.5.0/Cargo.lock) tutulur.
  Bunlar kaynak kanıtıdır; uygulama derleme konfigürasyonu olarak kullanılmaz.
- Kilitteki 75 registry crate, resmi static.crates.io arşivinden alındı ve her biri
  kendi Cargo.lock checksum değeriyle doğrulandı. 152 orijinal license/notice dosyası
  [envanterde](../../../THIRD_PARTY_LICENSES/inventory.json) path/hash/source ile izlenir.
  Copyright/AUTHORS dosyaları full license metninden ayrı role ile kayıtlıdır.

## Kapsam ve açık sınır

Bu, build ve platform bağımlılıklarını da içeren konservatif kaynak kümesidir.
74 crate için exact arşivden tam lisans metni korunur. Siphasher 1.0.3 arşivindeki
`COPYING` yalnız copyright ve MIT/Apache-2.0 seçimine referans içerir; full-license
olarak sınıflandırılmaz. Referans verdiği [resmi Apache-2.0 tam metni](https://www.apache.org/licenses/LICENSE-2.0.txt)
ayrıca `LICENSE-APACHE` olarak saklanır; bu ek metnin URL/hash provenance kaydı,
crate arşivinden çıkan 152 orijinal notice kaydından ayrıdır. Exact kaynak arşivleri
özel audit cache'inde kaldı; ürün deposuna native binary veya crate uygulama kodu taşınmadı.

PyPI wheel ve sdist build-provenance endpoint'leri 404 döndü; wheel için hem
`resvg_py` hem `resvg-py` normalizasyonu kontrol edildi. Bu gözlem yalnız bu tarihteki
endpoint sonucudur. Stripped wheel'in bütün bileşenlerinin bu kaynak kilidiyle
birebir eşleşmesi ve dağıtılacak installer'ın nihai içeriği kanıtlanmış sayılmaz.
B01/B10 binary teslim alt kabulü açık kalır; kaynak notice kayıtları bunu gizlemez.

## Doğrulama

Eksik kaynak kaydıyla yeni iki regresyon testi önce FAIL verdi. Kayıt eklendikten
sonra mevcut envanter testleriyle birlikte 26 test PASS (4.80 s).
[test_visual_notices.py](../../../tests/test_visual_notices.py) exact kilit SHA,
75/75 checksum kapsamı, notice byte hash'leri ve unproven build-provenance sınırını kontrol eder.

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_dependency_notices.py tests/test_visual_notices.py
```

Önceki `8fefc0d0` manifestindeki runtime/config kaynakları aynı; yalnız inventory.json
ve yeni test/kanıt dosyaları değişti. Fresh full-suite sonucu [validation](validation.md)
içinde ayrı kaydedilir; eski tam suite sonucu yeni envanterin PASS kanıtı sayılmaz.

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
Remote delivery and current hosted CI are tracked in [PR#36](https://github.com/ozkurkuran/MikroCAM/pull/36). Two real historical vector-only
projects provide limited format metadata; they are not Image fixtures. Current
LightBurn executable/device/embedded Image evidence and native V3/V4 remain open.
No complete binary-release audit or complete .lbrn2 product delivery is claimed.

## 2026-10-03 — PR review corrections

The siphasher full-text regression first failed; its original COPYING is now
classified as copyright, with the referenced official Apache text retained separately.
Notice, development installation, SVG font and carrier regressions passed together:
46 tests, 82.09 s. Current full-suite/remote delivery evidence is tracked by PR#36;
the earlier 5746-test checkpoint above predates these corrections.
