# Implementation plan — Doğrulanmış native tur, sıra değişimi ve bekleme

Feature:035-interlace-cycle-controls;3 user story,7 task. Ortak gerçek mimari ve Constitution Check:
[plan](../../docs/design/visual-interlace/plan.md). Tipler/limits/schema:
[data-model](../../docs/design/visual-interlace/data-model.md),
[API](../../docs/design/visual-interlace/contracts/api.md),
[test matrix](../../docs/design/visual-interlace/validation.md).

G01 gerçek Evo API keşfi tamamlandı. G02 native LightBurn version/device/fixture
keşfi WAITING;032/033 bağımsız ilerler,034/035native bu kapıyı atlamaz.
Task test→uygulama sırası ve bağımlılıklar tasks.md içindedir. Yeni import guard
istisnası yok; function80/module600, legacy+6, existing Placement/Recipe reuse.

Dependency kararları: mevcut Pillow/QtPdf/fontTools + optional resvg_py 0.5.0.
Wheel/license audit ayrımı ortak plan ve validation içinde kayıtlıdır.
Feature flag/renderer registry/ABC veya genel plugin altyapısı eklenmez.
