# Implementation plan — Cihaz türüne göre lazer reçeteleri

2026-10-03; [spec](spec.md). CPython3.13/PyQt6; yeni bağımlılık yok.

## Constitution Check

1. PASS: Capability/validation `mikrocam.core`, JSON codecs core, UI yalnız input/display.
2. PASS: Legacy kaynak değişikliği 0; host hook yeniden kullanılır.
3. PASS: Bir concrete device dataclass; CAM ve görsel reçete iki gerçek kullanım. Registry/backend yok.
4. PASS: Tek capability/parameter kaynağı; recipe2 nested formatlar versioned ve schema1 migration testli.
5. PASS: Qt'siz model/codec/export testleri önce; UI Qt smoke ve gerçek desktop kanıtı.
6. N/A: Makine/emisyon yok; metadata yanlışlığı tehlike analizi spec içinde.
7. PASS: Özgün uygulama; yalnız resmi davranış dokümanı, upstream kod kopyalanmaz.
8. PASS:3story,24task.

## Design

`LaserPass` eski positional API korunarak optional cihaz alanları alır; recipe
profilinde gerekli/izinli alanlar doğrulanır. `device=None` legacy dört alanı
zorunlu tutar ve schema1 üretir. Yeni cihaz reçetesi schema2 üretir. job/visual/
manifest yeni profilli kayıt için2, eski kayıt için1; her decoder exact-version
eşleşmesini ve nested profile tutarlılığını denetler.

`LaserDeviceProfile(kind,name,ranges,discrete pulse widths)` sayısal default
üretmez. `LaserRecipeEditor` her cihazda aynı satır draftlarını saklar, yalnız
uygun sütunları gösterir; eski reçete unspecified olarak görünür. Optional
üretici sınırı paneli ayrı thin widget; modeldeki capability ve validation
yeniden kullanılır. Shared editor mevcut CAM ve visual changed sinyallerine uyar.

## Verification

New test collection RED → core/codec/UI/export GREEN → existing laser/visual/
architecture tests → real desktop two-device save/reopen → full suite → source
commit/PR exact-head Windows CI → merge → exact main Windows CI.
Tek central ledger E:/VSCode/Flatcam/MikroCAM/docs/IS_TAKIP.md; private QA orada .venv altında.
Native LightBurn G02 ve binary release bu profil metadata tesliminden ayrı kalır.
