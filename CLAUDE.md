# MikroCAM

PCB CAM + CNC kontrol + fiber lazer CAM. Açık kaynak (MIT), GitHub'da herkese açık.

- **Bu repo:** `ozkurkuran/MikroCAM`, `mekatrol/flatcam`'in fork'udur; kullanıcının seçimiyle
  Bitbucket `marius_stanciu/flatcam_beta` reposunun `Beta_1.0` dalına güncellenmiştir.
  Seçilen commit: `e046a2a33926003765f83d6402b96fe6c5c3bcf7`.
- **Altın referans:** `ozkurkuran/flatcam-8.994-py313`, `baseline-8.994-py313` tag'i.
  Değiştirilmemiş ilk fork `upstream-evo-baseline`, seçilen Beta_1.0 tabanı
  `upstream-evo-beta1-baseline` tag'iyle korunur. Ayrıntı: `docs/PREPARATION.md`.

## Bağlayıcı kurallar

`.specify/memory/constitution.md` her değişiklikte geçerlidir; spec-kit dışındaki küçük işler de
buna dahildir. Özet:

- Yeni özellik mantığı `mikrocam/` paketine yazılır (`foundation-guardrails` ile oluşturulacak).
  `appMain.py`, `camlib.py` ve diğer legacy dosyalara yalnızca hata düzeltmesi ve kısa bağlantı
  kodu eklenir.
- Katman yönü: legacy → `mikrocam.ui` → `mikrocam.bridge` → `mikrocam.<alan>` → `mikrocam.core`.
  `core` ve alan paketleri PyQt6 veya legacy import etmez; legacy'yi yalnızca `bridge` import eder.
- En az iki somut kullanımı olmayan bir soyutlama eklenmez. Yeni bağımlılık gerekçe ve lisans ister.
- Hedef CPython 3.13.x'tir; daha yeni sözdizimi kullanılmaz.
- FlatCAM-Plus'ın non-commercial modüllerinin kaynak kodu açılmaz ve kopyalanmaz (temiz oda);
  FlatCAM-Plus git remote'u olarak eklenmez.

## Komutlar

Evo giriş noktası `flatcam.py`, ana uygulama modülü `appMain.py`'dir.
Windows 11 / Python 3.13 kurulumu, tek komutla başlatma ve doğrulanmış test komutları
`001-evo-py313-baseline` uygulamasında belgelenecek; henüz doğrulanmış değildir.
8.994 portunun test komutları yalnızca altın referans reposunda geçerlidir.

Mevcut Evo testleri `tests/` altındadır; updater testleri de korunur. Beta_1.0 ile gelen
updater, MikroCAM için yeni bir otomatik güncelleme özelliği geliştirme kararı değildir.

## İş akışı

- Yeni özellik: `docs/ROADMAP.md`'den sıradaki dilimi seç ve şu akışı izle: `/speckit-specify` →
  `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`.
- Hata düzeltmesi veya davranışı değiştirmeyen refactor için spec gerekmez; önce hatayı yeniden
  üreten bir test yazılır.
