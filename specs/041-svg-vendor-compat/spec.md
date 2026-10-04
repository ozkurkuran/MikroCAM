# Özellik Belirtimi: SVG üretici uyumluluğu

**Özellik dalı**: `041-svg-vendor-compat`
**Oluşturma**: 2026-10-04
**Durum**: Uygulandı (bkz. [validation.md](validation.md))
**Girdi**: PR #41 (`test/vendor-svg-fixtures`) gerçek Proteus ve Illustrator dışa aktarımlarıyla
016/018/019/020 boşluklarını kayıt altına aldı. Bu dilim, donanım gerektirmeyen üç boşluğu kapatır:
standart SVG DOCTYPE, `vector-effect="non-scaling-stroke"` ve Proteus'un `Z` içermeyen tam daire
delikleri.

**Bağımlılık**: Bu dal PR #41'in commit'lerini içerir; PR #41'den sonra birleştirilmelidir.

## Kullanıcı Senaryoları ve Testler

### Kullanıcı Hikâyesi 1 — Standart DOCTYPE'lı SVG'yi içe aktarmak (Öncelik: P1)
Bir tasarımcı Illustrator'ın standart SVG 1.1 DOCTYPE satırını yazdığı bir dosyayı **Import SVG**
ile açar. Dosya, DOCTYPE satırı yokmuş gibi aynı fiziksel geometriyle içe aktarılır. Dış DTD
indirilmez, entity açılmaz; iç alt küme veya entity bildirimi içeren dosya anlaşılır bir hatayla
reddedilir.

**Neden bu öncelik**: PR #41 taramasında 731 gerçek Illustrator SVG'sinin 507'si (%69) yalnızca
DOCTYPE nedeniyle reddedildi; 459'u iç alt kümesiz düz DOCTYPE idi.

**Bağımsız test**: Aynı çizimin DOCTYPE'lı ve DOCTYPE'sız sürümleri aynı malzemeyi verir; saldırgan
DTD örnekleri ağ erişimi olmadan açık hatayla reddedilir.

**Kabul senaryoları**:
1. Yalnızca izinli SVG 1.0 veya SVG 1.1 public/system tanımlayıcı çiftini taşıyan, iç alt kümesi
   olmayan, kök elemandan önce tek DOCTYPE içeren dosya içe aktarılır; sonuç DOCTYPE'sız sürümle aynıdır.
2. İç alt küme (`[...]`, boş olsa bile), entity/parametre entity bildirimi, yalnız `SYSTEM`,
   bilinmeyen public veya system tanımlayıcı, kök dışında `svg`, ikinci veya kök sonrası DOCTYPE,
   tanımsız entity başvurusu reddedilir; mesaj nedeni söyler.
3. 020 kaynak algılayıcısı aynı izin listesini kullanır; algılayıcı ile içe aktarıcı aynı dosya için
   DOCTYPE konusunda farklı karar vermez.

### Kullanıcı Hikâyesi 2 — Proteus `non-scaling-stroke` niteliğini doğru yorumlamak (Öncelik: P1)
Proteus PCB SVG'si her dolgu yoluna `vector-effect="non-scaling-stroke"` yazar. Kullanıcı dosyayı
Geometry veya Gerber olarak açar; stroke boyanmayan yollarda nitelik malzemeyi değiştirmez.
Stroke boyanan yollarda genişlik tek ve kesin fiziksel anlamla mm'ye çevrilir; anlamın belirsiz
olduğu durumlar açık hatayla reddedilir.

**Neden bu öncelik**: Bulunan 35 izinli lisanslı Proteus SVG'sinin 30'u yalnızca bu nedenle
içe aktarılamıyordu.

**Bağımsız test**: Analitik çizimlerde stroke kalınlığı viewBox ölçeği ve eleman dönüşümlerinden
bağımsız olarak `genişlik × 25,4/96 mm` çıkar; eşit olmayan ölçek/eğiklikte hata alınır.

**Kabul senaryoları**:
1. Stroke boyanmayan veya sıfır genişlikli elemanda `non-scaling-stroke`, nitelik hiç yokmuş gibi
   aynı malzemeyi üretir (eşit olmayan ölçek/eğiklik altında da).
2. Stroke boyanan elemanda genişlik kök viewport'un CSS piksel koordinat sisteminde ölçülür:
   birimsiz/`px` değer `w × 25,4/96 mm`, mutlak birimli değer kendi fiziksel uzunluğudur;
   viewBox ölçeği, grup/eleman dönüşümü ve `use` ötelemesi kalınlığı değiştirmez.
3. Stroke boyanan elemanın kullanıcı→mm dönüşümü benzerlik değilse (eşit olmayan ölçek, eğiklik,
   `preserveAspectRatio="none"` ile farklı eksen ölçekleri) veya kökte `transform` varsa hata verilir.
4. `none` ve `non-scaling-stroke` dışındaki değerler, `viewport`/`screen` anahtar sözcükleri ve
   grup/`use`/kök üzerindeki etkin `vector-effect` hata verir.

### Kullanıcı Hikâyesi 3 — Gerçek Proteus deliklerini incelemek (Öncelik: P2)
Kullanıcı aynı Proteus dosyasını **SVG drill** incelemesinde açar ve gerçek delikleri merkez ve
çaplarıyla görür. Proteus delikleri `Z` ile kapatılmamış, başlangıç noktasına dönen dört kübik
Bezier daireleridir ve sekizgen (dairesel olmayan) pad'lerin içindedir.

**Neden bu öncelik**: 018 bugüne kadar gerçek Proteus çıktısında hiç çalıştırılamadı.

**Bağımsız test**: Gerçek dosyada inceleme, ham koordinatlardan bağımsız hesaplanan 25 merkez ve
1,00 mm çapı (dosyanın CADCAM notundaki `D=1mm` ile uyumlu) verir.

**Kabul senaryoları**:
1. Tek alt yollu, başlangıç ve bitişi 1e-6 mm içinde çakışan ve toplam süpürmesi tam 360° olan bir
   yol, 018'in mevcut daire uyum ölçütlerini geçerse açık olsa da daire kanıtı sayılır.
2. 360°'den az veya fazla süpürme, uç boşluğu toleranstan büyük yol, çok alt yollu daire parçaları ve
   dairesel olmayan beyaz şekiller daire kanıtı sayılmaz.
3. Delik merkezi ve çapı yalnızca beyaz dairenin kendisinden gelir; pad şekli asla delik çıkarımı için
   kullanılmaz. Pad yalnızca destek kanıtıdır: dairesel pad kuralı aynen korunur; dairesel destek
   yoksa ağırlık merkezi delik merkezine 0,02 mm içinde olan ve deliği 0,01 mm payla tamamen içeren
   beyaz olmayan dolu tek poligon pad kabul edilir.

### Sınır durumları
DOCTYPE'tan önce XML bildirimi, yorum ve işleme talimatı; tek/çift tırnak; boşluk çeşitleri;
küçük harfli `<!doctype`; DOCTYPE içinde `>` bulunan iç alt küme; milyar-kahkaha; yorum içinde
`<!ENTITY`; ters yön ve çevrilmiş (flip) daireler; aynı noktada iki tur atan yol; büyük bakır döküm
poligonunun içindeki delik; kenara kaydırılmış delik; `vector-effect` CSS yazımı ve büyük harf;
`inherit`; clip tanımı içinde `vector-effect`; kök `transform` ile stroke'suz `non-scaling-stroke`.

## Gereksinimler

### İşlevsel Gereksinimler
- **FR-001**: Geometri içe aktarıcısı ve 020 algılayıcısı tek bir izin listesini paylaşır: SVG 1.0
  (`-//W3C//DTD SVG 1.0//EN`, `http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd`) ve
  SVG 1.1 (`-//W3C//DTD SVG 1.1//EN`, `http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd`).
- **FR-002**: İzinli DOCTYPE kök elemandan önce, en fazla bir kez, iç alt kümesiz bulunmalıdır; XML
  ayrıştırıcıya verilmeden önce aynı uzunlukta boşlukla silinir. Dış kaynak hiçbir koşulda okunmaz.
- **FR-003**: Kalan metinde herhangi bir `<!DOCTYPE`/`<!ENTITY` veya tanımsız entity başvurusu
  bulunan kaynak, kısmi sonuç üretmeden açık hatayla reddedilir.
- **FR-004**: `vector-effect` miras alınmaz; yalnız grafik elemanlarda `none` veya
  `non-scaling-stroke` kabul edilir.
- **FR-005**: Boyanmayan stroke için `non-scaling-stroke` malzemeyi değiştirmez.
- **FR-006**: Boyanan stroke için genişlik kök viewport CSS pikselinde (1 px = 25,4/96 mm, yakınlaştırma
  1) ölçülür; yalnız benzerlik dönüşümünde eşdeğer kullanıcı genişliğine kesin çevrilir; aksi halde ve
  kök `transform` varsa hata verilir.
- **FR-007**: Kullanılan `non-scaling-stroke` sayısı ve anlamı içe aktarma bildirimlerinde sınırlı
  sayıda (eleman başına değil, belge başına) açıklanır.
- **FR-008**: 018 daire kanıtı, açık tek alt yolun uçları 1e-6 mm içinde çakışıyorsa yolu bu uçta
  kapatıp mevcut uyum ölçütleriyle (≥12 nokta, basit halka, ≤π/4 adım, tek yön, toplam 2π, radyal ve
  orta nokta hatası ≤ min(0,01 mm, r×%2)) değerlendirir.
- **FR-009**: Delik destek kuralı FR-003 (018) dairesel pad'i korur ve FR-008 ile tanımlı ek poligon
  pad desteği ekler; seçilen pad kimliği raporlanır, pad'den merkez/çap türetilmez.
- **FR-010**: Gerçek Proteus dosyası Geometry ve Gerber olarak içe aktarılır, drill incelemesi gerçek
  delikleri bulur; gerçek Illustrator DOCTYPE'lı dışa aktarımı içe aktarılır.
- **FR-011**: 016/018/019/020 doğrulama notları ve `docs/SVG_IMPORT.md`, `docs/SVG_DRILLS.md` yeni
  kanıta bağlanır; gerçekten açık kalan boşluklar açık yazılır.

### Ana varlıklar
- **İzinli DOCTYPE**: sabit public/system tanımlayıcı çifti; içerik veya ağ kaynağı değildir.
- **Non-scaling stroke genişliği**: kök viewport CSS pikseli cinsinden kaynak genişlik ve elemanın
  benzerlik ölçeğinden türetilen eşdeğer kullanıcı genişliği.
- **Açık uçlu daire kanıtı**: çakışan uçlu tek alt yol; mevcut daire uyumunu geçmek zorundadır.
- **Poligon pad desteği**: eş merkezli, deliği paylı içeren beyaz olmayan dolu poligon.

## Başarı Ölçütleri
- **SC-001**: DOCTYPE'lı ve DOCTYPE'sız analitik çizimlerin malzeme alanı ve sınırları birebir aynıdır;
  12+ saldırgan DTD örneğinin tamamı ağ erişimi olmadan reddedilir.
- **SC-002**: Analitik `non-scaling-stroke` çizimlerinde stroke kalınlığı 1e-9 mm içinde beklenen
  fiziksel değerdir; boyanmayan durumlarda malzeme nitelik yokken üretilenle aynıdır.
- **SC-003**: Gerçek Proteus dosyasında 25 aday, her biri bağımsız ham koordinat hesabına 1e-6 mm
  içinde ve çap 1,00 mm; flip açık/kapalı.
- **SC-004**: Var olan 016–020 testleri yalnız bilinçli değiştirilen sözleşme noktalarında güncellenir;
  tam test paketi ve mimari kontroller yeşildir, legacy büyümesi 0'dır.

## Varsayımlar (uygulama varsayımı; kullanıcı kararı değildir)
- **UA-1**: Yalnız SVG 1.0 ve 1.1 tam profil tanımlayıcıları izinlidir. SVG 1.1 Tiny/Basic ve 1.2
  DOCTYPE'ları gerçek taramada gözlenmediği için izin listesine alınmadı; reddedilmeye devam eder.
- **UA-2**: `non-scaling-stroke` için ana koordinat uzayı, SVG Tiny 1.2 ve SVG 2'nin "host/screen"
  koordinat uzayının yakınlaştırma 1'deki karşılığı olan kök viewport CSS piksel uzayıdır. CAM'de
  ekran yakınlaştırması yoktur.
- **UA-3**: Eşit olmayan ölçek/eğiklik altında SVG 2 tanımı uygulanabilir olsa da mevcut stroke
  hattı kalınlığı kullanıcı uzayında genişletir; ikinci bir stroke hattı eklemek yerine bu durum
  açıkça reddedilir. Kök `transform` ile tarayıcı davranışı (viewport mu, ekran mı) belirsiz olduğundan
  boyanan non-scaling stroke reddedilir.
- **UA-4**: Uç çakışma toleransı 1e-6 mm'dir: yalnız kayan nokta artığını kapsar, geometrik boşluk
  kapatmaz.
- **UA-5**: "Dairesel olmayan pad'den çıkarım yok" kuralı, deliğin merkez/çapının pad'den
  türetilmemesi ve pad'in tek başına aday olmaması olarak yorumlanmıştır; beyaz tam daire kanıtı
  zorunludur. Poligon pad yalnız destek olarak, eş merkez ve tam içerme şartıyla kullanılır.
- **UA-6**: 731 dosyalık Illustrator taraması ağdan yeniden indirme gerektirdiği için tam olarak
  yinelenmedi; kabul oranı yalnız sınırlı bir yerel ölçümle raporlanır (bkz. validation.md).
