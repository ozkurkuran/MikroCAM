# Research — ada ve dama tahtası tarama

Kaynaklar: mevcut MikroCAM 006/007/008/036 davranışı ve genel lazer/SLM tarama
literatüründeki “island scanning” kavramı (küçük kare adalar, komşu adalarda dik hatch,
adaların ardışık olmayan sırada taranması). Dış kod kopyalanmadı; FlatCAM-Plus kaynağı açılmadı.

## Kararlar

1. **Orijine sabit ızgara.** Hatch çizgileri zaten orijine sabit tarama indisleri kullanır
   (006). Izgara da orijine sabitlenince bölge değiştiğinde mevcut döşemeler kaymaz ve
   çıktı deterministik kalır. Reddedilen: bölge sınırına hizalı ızgara.
2. **Önce bölge, sonra hücre kırpma.** Her döşemede çizgi önce bölgeyle (marjlı pencere),
   sonra kapalı hücreyle kırpılır; yalnız tamamen üst/sağ kenardaki parça düşürülür.
   Reddedilen: bölge ∩ hücre poligonu ile kırpma; ortak kenardaki sınır çizgileri sıfır
   alanlı kesişimde kaybolur ve normal hatch ile eşdeğerlik bozulur.
3. **90° katlarında kesin dönüş.** `Placement` 0/90/180/270 için tam katsayı kullanır;
   kenar üzerindeki çizgiler bu açılarda kesin karşılaştırılır. Diğer açılarda çizgi
   kenara paralel olmadığından 1e-9 mm tolerans yalnız sayısal gürültü içindir.
4. **Kalıcılık manifest'te.** `PlanOptions` 006–008'de dosya formatı değildir; export
   manifest'i interlace_n'i saklar. Ada ayarı da orada tutulur; v3 yalnız ada açıkken
   yazılır, eski çıktı aynen kalır. Reddedilen: job JSON'a plan seçenekleri eklemek
   (uygulama job JSON'u kullanmıyor, 037 reçete formatıyla çakışma riski, bütün hatch
   seçeneklerini kapsama alma gereği).
5. **Dama tahtası = iki parite sınıfı.** Aynı paritedeki iki hücre kenar paylaşamaz;
   sıra basit, kararlı ve kanıtlanabilir olur. Reddedilen: rastgele sıra (tohum ve
   format gerektirir), en uzak-komşu sezgiseli (gereksiz karmaşıklık).
6. **Yeni bağımlılık yok.** Shapely kırpma/kesişim ve mevcut `Placement` yeterlidir.
