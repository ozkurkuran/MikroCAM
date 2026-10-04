# Araştırma: SVG üretici uyumluluğu

## 1. Standart SVG DOCTYPE

**Kanıt**: PR #41'in yerel olmayan taramasında Illustrator işaretli 731 Wikimedia Commons SVG'sinin
507'si (%69) 016'nın her DOCTYPE'ı reddetmesi nedeniyle açılamadı: 459'u iç alt kümesiz düz DOCTYPE,
48'i iç entity alt kümeli (eski Illustrator `ns_svg`/`ns_flows` entity'leri). 020 algılayıcısı SVG 1.1
public DOCTYPE'ını zaten çevrim dışı okuyordu ama yalnız bir kez `subn` ile siliyor, konumunu
denetlemiyor ve orijinal metni XML ayrıştırıcıya veriyordu.

**W3C tanımlayıcıları** (SVG 1.0 REC ve SVG 1.1 REC ekleri):
- SVG 1.0: `-//W3C//DTD SVG 1.0//EN`, `http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd`
- SVG 1.1: `-//W3C//DTD SVG 1.1//EN`, `http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd`

**Karar**: Paylaşılan `mikrocam/importers/svg_doctype.py`; önsöz (boşluk, XML bildirimi/PI,
yorum) taranır, ilk önsöz dışı yapı DOCTYPE ise tam desenle (`<!DOCTYPE svg PUBLIC "p" "s">`,
iç alt küme yok) eşleşmeli ve çift izin listesinde olmalıdır. Eşleşen bildirim aynı uzunlukta
boşlukla değiştirilir (satır sonları korunur, hata satır numarası değişmez). Kalan metinde
büyük/küçük harf duyarsız `<!DOCTYPE`/`<!ENTITY` aranır. Böylece expat hiçbir DTD görmez;
entity tanımı olmadığından `&x;` başvurusu "undefined entity" ile reddedilir; dış DTD indirme
yolu hiç oluşmaz (ElementTree zaten indirmez, fakat DTD'yi tamamen kaldırmak bu varsayıma
dayanmaz).

**Reddedilen alternatifler**: (a) `defusedxml` — yeni bağımlılık ve yine DTD işler; (b) expat'a DTD'yi
verip `SetParamEntityParsing` ile sınırlamak — daha geniş saldırı yüzeyi; (c) iç alt kümede yalnız
Illustrator ad alanı entity'lerine izin vermek — entity açılımı gerektirir, görev kapsamı dışı.

## 2. `vector-effect="non-scaling-stroke"`

**Standart**: SVG Tiny 1.2 §11.5 "vector-effect": değerler `non-scaling-stroke | none | inherit`,
başlangıç `none`, **miras alınmaz**, grafik elemanlara uygulanır. Tanım: "the shape's path is
transformed into the host coordinate space. Stroke outline is calculated in the host coordinate
space. The resulting outline is transformed back to the user coordinate system." Sonuç: stroke
genişliği eşit olmayan ölçek ve eğiklik dahil dönüşümlerden ve yakınlaştırmadan bağımsızdır.
SVG 2 §8.13 aynı özelliği `none | [non-scaling-stroke | non-scaling-size | non-rotation |
fixed-position]+ [viewport | screen]?` olarak genişletir; varsayılan ana uzay ekran (screen),
`viewport` anahtar sözcüğü ise doğrudan viewport'tur; `use`'a da uygulanır.

**Fiziksel çeviri**: MikroCAM'in mm çerçevesi kök viewport'un CSS piksel uzayıdır: 016 sözleşmesi
1 px = 25,4/96 mm kullanır ve kök `width/height` mm ise viewBox→viewport eşlemesi bu çerçeveye
yerleşir. Ekran yakınlaştırması 1 kabul edilince ana (host) uzay = bu çerçeve. Kaynak genişlik
`w` (`parse_svg_length` ile CSS px) fiziksel olarak `w × 25,4/96 mm`'dir; `0.2mm` gibi mutlak birim
tam 0,2 mm olur.

Eleman kullanıcı→mm matrisi `M` benzerlik ise (sütunlar dik ve eşit uzunlukta, ölçek
`s = sqrt(|det M|)`), kullanıcı uzayında `w_mm / s` genişlikle genişletip `M` ile eşlemek, mm
uzayında `w_mm` ile genişletmekle **birebir aynıdır** (yuvarlak uç/birleşim dahil; benzerlik
daireleri daireye eşler, miter oranı açıya bağlıdır ve korunur). Dikey flip bir yansımadır; benzerliği
bozmaz.

**Belirsiz / desteklenmeyen**:
- `M` benzerlik değil: standart tanımlı ama mevcut hat stroke'u kullanıcı uzayında genişletir;
  sonucun doğru olması için ikinci bir mm-uzayı stroke hattı gerekir → açık hata (UA-3).
- Kök `transform`: 016 bunu viewBox dışında viewport CSS pikselinde uygular. SVG 2'de kök
  `transform`'un ana uzaydan önce mi sonra mı sayılacağı (`viewport` ve `screen` farkı) ve tarayıcı
  davranışı tutarlı değildir → boyanan stroke için hata.
- `viewport`/`screen` anahtar sözcükleri, diğer SVG 2 etkileri, grup/`use`/kök üzerinde etkin değer
  → hata. (Miras alınmadığı için grup üzerindeki değer çocukları etkilemez; sessizce yok saymak yerine
  reddedilir.)
- Boyanmayan stroke: tanım yalnız stroke ana hattını değiştirir; dolgu ve merkez çizgisi aynı kalır.
  Bu nedenle her dönüşümde kesin no-op'tur ve kabul edilir. Gerçek Proteus dosyasındaki 209 kullanımın
  209'u bu türdendir (`stroke="none"` gruplarında dolgu yolları).

**Reddedilen alternatif**: niteliği her durumda yok saymak — boyanan stroke'ta kalınlığı viewBox
ölçeğiyle yanlış (Proteus'ta 100 kat) üretebilirdi.

## 3. Proteus delikleri

**Ham dosya incelemesi** (`tests/reference/cad-source/proteus-breath-analyzer/B_A_.svg`, Apache-2.0):
kök `width="54.11mm" height="44.28mm" viewBox="0 0 5411 4428"` → 1 kullanıcı birimi = 0,01 mm.
351 grafik eleman: 26 beyaz dolu yol (1 kart arka planı dikdörtgeni + 25 daire), 183 siyah dolu yol
(50 sekizgen pad, 2 on iki kenarlı şekil, 131 daire: 120 adet r=51 ve 11 adet r=12 iz birleşim
noktası), 140 stroke'lu iz polyline'ı (129×102, 11×25 birim), 2 stroke'lu çerçeve.

Delikler: `M x+50,y C … C … C … C … x+50,y` biçiminde, `Z` olmadan başlangıca dönen dört kübik
Bezier (κ = 28,17/51 ≈ 0,5524; r=50 için 27,61/50). 25'inin hepsi r=50 birim = **Ø1,00 mm**; bu
dosyanın yanındaki CADCAM notu `Drill D21 CIRCLE D=1mm ComponentDrill` ile uyumludur. Her deliğin
etrafında iki eş merkezli siyah sekizgen vardır (202×254 ve 228×280 birim, merkezden sınıra en kısa
uzaklık 1,01 mm ve 1,14 mm). İki delik ayrıca ağırlık merkezi 9–11,5 mm uzaktaki büyük bir bakır
döküm poligonunun içindedir. r=51 birleşim noktaları hiçbir delikle eş merkezli değildir.

**Karar**:
1. Daire kanıtı: tek alt yol, `closed` veya uç farkı ≤1e-6 mm ise son nokta başlangıca eşitlenip
   mevcut `fit_closed_circle` uygulanır. Bu fonksiyon tek yönlü, ≤π/4 adımlı, toplam açısı tam 2π
   (1e-8) ve basit halka şartlarını zaten denetler; böylece 360° süpürme kanıtlanır, iki tur atan
   yol basit halka olmadığı için düşer, 3/4 yay uçları çakışmadığı için düşer.
2. Destek: 018'in dairesel pad kuralı birebir korunur. Dairesel destek yoksa beyaz olmayan, dolu,
   clip'siz, malzemesi tek `Polygon` olan eleman; ağırlık merkezi ≤0,02 mm ve
   `poligon.contains(merkez)` ile `sınır.distance(merkez) ≥ r + 0,01 mm` (kesin; çokgen
   yaklaşımlı disk kullanılmaz). Birden çok destekte en küçük alanlı pad seçilir. Arama Shapely
   `STRtree` ile sınırlıdır.
3. Büyük döküm poligonu ağırlık merkezi şartıyla düşer; sekizgen tek başına beyaz değildir ve aday
   olamaz.

**Reddedilen alternatifler**: pad'in sınır kutusundan delik türetmek (FR-003/018 yasak); dairesel
olmayan pad'leri dışlayıp gerçek delikleri bulmamak (kullanıcı değeri yok); uç toleransını 0,01 mm
yapmak (gerçek boşlukları kapatabilir).

## 4. Illustrator kabul oranı
Önceki tarama verisi saklanmadı (yalnız sayılar kayıtlı). 1129 dosyanın yeniden indirilmesi
Wikimedia hız sınırına takıldığından tam tekrar yapılmadı; sınırlı örnekle ölçüm validation.md'de.
