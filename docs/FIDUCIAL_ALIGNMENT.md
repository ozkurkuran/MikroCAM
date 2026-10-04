# Fiducial hizalama ve hizalanmış iş

Bu araç, kartın makinedeki gerçek konumunu ve dönüklüğünü fiducial (referans) noktalarından
hesaplar ve sonucu mevcut tek CAM→makine transformuna (`Placement`) uygular. Kamera ile
otomatik yakalama **henüz yoktur**; makine koordinatları yazılır veya bağlı makinenin
konumundan alınır. Otomatik testler FakeGRBL ile yapılmıştır; gerçek makinede veya kamerayla
doğrulama yapılmamıştır.

**Yazılım kontrolleri fiziksel E-stop, muhafaza ve interlock'un yerini almaz.**

## Akış

1. **Plugins → G-code preflight** dock'unda kaynağı yükleyin, **Fiducial alignment…** düğmesine basın.
2. Her fiducial için bir satır ekleyin:
   - **Design X/Y**: CAM/G-code koordinatı (mm). Seçili Excellon nesnesinin delik merkezlerinden
     veya Gerber nesnesinin flash pedlerinden **Points from selected object** ile seçilebilir.
   - **Machine X/Y (MPos)**: makine koordinatı (mm), çalışma (WPos) koordinatı değil. Takımı
     fiducial üzerine jog ile getirip makine **Idle** ve durum taze iken **Capture machine XY**
     ile alınabilir. Yakalama yalnız Machine panelinin son durumunu okur; komut göndermez.
3. Yöntemi seçin: **Rigid** (öteleme + dönme, ≥2 nokta), **Similarity** (+ eşit ölçek, ≥2),
   **Affine** (en küçük kareler, ≥3). Varsayılan: 2 noktada Rigid, 3+ noktada Affine.
4. Eşikler: maksimum artık (varsayılan 0.05 mm), maksimum ölçek sapması (%0.5), en küçük
   fiducial aralığı (10 mm). **Calculate alignment** her nokta için artığı, RMS/maksimumu,
   dönmeyi, ölçekleri ve fazlalığı gösterir.
5. Sonuç **REJECTED** ise kullanılamaz. Ayna, aşırı ölçek, büyük artık veya yakın noktalar
   reddedilir; doğrusal veya çakışan noktalar hiç sonuç üretmez.
6. **ACCEPTED** ise **Use in preflight setup** ile preflight kurulumuna aktarın; rijit
   placement alanları devre dışı kalır. **Analyze** ile yeniden inceleyin. **Clear fiducial
   alignment** eski kuruluma döner.
7. Dönme/affine içeren inceleme doğrudan gönderilemez (GRBL G-code'u değiştirmeden G54 ile
   gönderir). **Aligned job…** ile ayrı bir iş türetin:
   - **G54 X/Y**: başlatmada etkin olacak G54 değeri. **Use machine G54 XY** taze durumdaki
     WCO'yu doldurur. Başlatmada gerçek G54/G92/TLO yeniden doğrulanır; uyuşmazlıkta hiçbir
     blok gönderilmez.
   - **Arc chord tolerance**: yaylar bu tolerans içinde doğru parçalarına bölünür.
8. Önce **Dry run aligned job** ile havada XY kontrolü yapın, sonra **Load aligned job into
   Machine** ile mevcut Start/Pause/Stop akışını kullanın.

Auto-level, aynı incelemedeki hizalamayı doğrudan uygular. Lazer işi aynı `Placement`'ı
kullanabilir; ancak lazer job JSON, görsel reçete ve görsel export manifest formatları yalnız
rijit placement saklar ve affine hizalamayı açıkça reddeder.

## Fiducial seti dosyası

**Save set…** / **Open set…** `mikrocam.fiducial-set` şema 1 JSON dosyası kullanır (mm).
Ölçülen değerler yalnız aynı bağlama ve homing için geçerlidir; kart veya makine referansı
değiştiyse yeniden ölçün.

## Sınırlar ve riskler

- 2 noktalı benzerlik ve 3 noktalı affine tam belirlidir: artık her zaman sıfırdır ve ölçüm
  hatasını gösteremez. Doğrulama için bir nokta fazlası ekleyin.
- WPos'u MPos yerine girmek sabit bir öteleme hatası üretir; eşikler bunu yakalamaz.
- Hizalama bayatlayabilir: kart yerinden oynarsa yazılım bunu algılamaz.
- Kamera yakalama, görüntü işleme ve gerçek makinede hizalama doğrulaması bekleyen işlerdir.
