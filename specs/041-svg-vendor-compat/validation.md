# Doğrulama: SVG üretici uyumluluğu (041)

Dal `041-svg-vendor-compat`, taban `origin/test/vendor-svg-fixtures` (`bb9a886c`, PR #41).
Ortam: Windows 11, CPython 3.13 (`E:/VSCode/Flatcam/MikroCAM/.venv`, resvg_py dahil tam
`requirements-dev`). Loglar worktree `.venv/041-*.log` (git tarafından yok sayılır).

## Önce-test (RED)
Yeni testler uygulamadan önce çalıştırıldı: 7 FAIL + 3 toplama hatası (modül/sembol yok), 95 PASS
(`.venv/041-red.log`). Başarısız olanlar: gerçek Proteus Geometry/Gerber içe aktarma ve drill
incelemesi, 020'nin SVG 1.0 DOCTYPE'ı, yeni `svg_doctype`, `non_scaling_stroke_width`,
`COINCIDENT_ENDPOINT_MM` sembolleri.

## Seçilen kesin anlamlar
1. **DOCTYPE**: yalnız `(-//W3C//DTD SVG 1.0//EN, http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd)`
   ve `(-//W3C//DTD SVG 1.1//EN, http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd)`; kök elemandan
   önce (yalnız boşluk, XML bildirimi/PI ve yorumdan sonra), tek kez, iç alt kümesiz. Aynı uzunlukta
   boşlukla silinir; expat DTD görmez. Kalan metinde `<!DOCTYPE`/`<!ENTITY` veya tanımsız entity → hata.
   Geometri içe aktarıcısı ve 020 algılayıcısı aynı `strip_svg_doctype` fonksiyonunu kullanır.
2. **non-scaling-stroke**: miras alınmaz; yalnız şekillerde `none`/`non-scaling-stroke`.
   Boyanmayan stroke (none, genişlik 0, opaklık 0) → kesin no-op. Boyanan stroke → genişlik kök
   viewport CSS pikselinde (1 px = 25,4/96 mm, yakınlaştırma 1; mutlak birimler kendi uzunluğu);
   kullanıcı→mm matrisi benzerlikse kullanıcı genişliği `w·25,4/96/s` ile kesin eşdeğer. Benzerlik
   olmayan dönüşüm (eşit olmayan ölçek, eğiklik, farklı eksenli `preserveAspectRatio="none"`),
   ölçekleyen kök `transform`, SVG 2 ek değerleri/anahtar sözcükleri ve grup/`use`/kök üzerindeki
   değer → açık hata. Belge başına en fazla iki bildirim.
3. **Proteus delikleri**: tek alt yol, uç farkı ≤1e-6 mm ise bu uçta kapatılır ve değişmemiş
   `fit_closed_circle` ile sınanır (≥12 nokta, basit halka, tek yön, ≤45° adım, toplam tam 2π,
   radyal/orta nokta hatası ≤ min(0,01 mm, %2 r)). Destek: önce 018 dairesel pad kuralı; yoksa
   ağırlık merkezi ≤0,02 mm, merkezi içeren ve sınır uzaklığı ≥ r+0,01 mm olan beyaz olmayan dolu
   clip'siz tek poligon (en küçük alanlı). Merkez/çap yalnız beyaz daireden.

## Gerçek dosya sonuçları
- **Proteus** `proteus-breath-analyzer/B_A_.svg` (Apache-2.0, değiştirilmemiş): Geometry ve Gerber
  içe aktarma PASS, 351 eleman, malzeme sınırı (0, 0, 54,11, 44,28) mm, ~0,4 s. 209
  `non-scaling-stroke` kullanımının tamamı boyanmayan stroke'ta (tek `non-scaling-stroke-unpainted`
  bildirimi); 140 iz polyline'ı 25/102 birim (0,25/1,02 mm) normal stroke ile genişler.
- **Proteus drill**: 25/25 aday. Bağımsız doğrulama: test, dosyanın ham `d` metninden beyaz
  `MCCCC` yollarının kontrol noktası sınırlarıyla merkez/yarıçap hesaplar (25 daire, r=50 birim =
  0,5 mm); her aday bu merkezlere 1e-6 mm içinde bire bir eşleşir (flip açık/kapalı). Çap
  1,000116–1,000138 mm: dört kübik Bezier yaklaşımı (κ≈0,5522) gerçek dairenin en fazla %0,027 r
  dışında; tek takım grubu Ø1,00012 mm, 25 merkez. Upstream CADCAM notu: `Drill D21 CIRCLE D=1mm`.
  Her delik iki eş merkezli sekizgen pad içindedir (202×254 ve 228×280 birim); seçilen küçük olandır.
  İki delik ayrıca ağırlık merkezi 9–11,5 mm uzaktaki büyük bakır döküm poligonu içindedir ve onu
  destek olarak kullanmaz. Merkezler (mm, flip): x=6,05 (5 delik), 46,49 (4), y=6,40 (5), 21,64 (7),
  28,66 (4) sıraları — tam liste `test_vendor_export_fixtures.py` içindeki bağımsız hesaptan gelir.
- **Illustrator DOCTYPE**: yeni CC0 fixture `illustrator-commons-hex-star-doctype/` (Illustrator
  16.0.4, standart SVG 1.1 DOCTYPE, tek Commons sürümü, SHA-1 doğrulandı) Geometry/Gerber, flip
  açık/kapalı içe aktarılır; malzeme, ham altıgen noktalarının 1,5 birim miter ofsetine simetrik
  fark alanı <1e-9 mm² ile eşittir. 020 Illustrator olarak tanır.
- **Illustrator kabul oranı (yerel, ağsız)**: PR #41'in saklanan 1129 dosyalık Commons derleminde
  `Adobe Illustrator` işaretli 731 dosya (önceki kayıtla aynı ölçüt): eski kod (`bb9a886c`) 91,
  yeni kod **367** içe aktarır (%12,4 → %50,2); gerileme 0. DOCTYPE dağılımı: SVG 1.1 441 (270
  geçti), SVG 1.0 17 (6 geçti), iç alt küme 48 (hepsi açık hata), SVG 1.1 Tiny 1 (hata), DOCTYPE'sız
  224 (91, değişmedi). Kalan başlıca nedenler: pattern 54, kısmi opaklık 38, linearGradient 35,
  dash 32, kendini kesen stroke 29, metin 20, geçersiz/boş malzeme 19, font CSS 29, karmaşık dolgu
  bütçesi 9, UTF-8 dışı bildirim 8. Bu bir içe aktarma kabul ölçümüdür, görsel doğruluk iddiası değildir.

## Testler
Yerel (kaynak checkpoint, commit öncesi çalışma ağacı):
- Odaklı yeni/değişen testler + `tests/architecture`: 318 PASS (`.venv/041-focused.log`).
- İlgili SVG/CAD source/drill/import report/manufacturing testleri + architecture: 1863 PASS,
  205,5 s (`.venv/041-related.log`).
- `pip check`: temiz. Yeni bağımlılık yok; legacy büyüme testi PASS (legacy 0 satır).
- Modül/fonksiyon sınırı: en büyük değişen modül `svg_document.py` 216 satır; yeni fonksiyonlar <80.
- Tam paket (`QT_QPA_PLATFORM=offscreen`): **6006 PASS, 3 skip, 310 alt test, 11 mevcut uyarı,
  421,5 s, exit 0** (`.venv/041-full.log`, `.venv/041-full.xml`).
- Gerçek masaüstü `tests/smoke_app.py` (OpenGL, 120 s watchdog): **exit 0, 98,8 s**, SVG drill
  dialog/Excellon/yeniden içe aktarma dahil tüm yolculuklar ve normal kapanış (`.venv/041-smoke.log`).
  Yetim worker kalmadı.
- Windows CI: aşağıdaki Teslim bölümü.

## Açık kalanlar
- Benzerlik olmayan dönüşümde boyanan non-scaling stroke (standartta tanımlı, bu dilimde açık hata);
  kök `transform` ile boyanan non-scaling stroke.
- İç entity alt kümeli eski Illustrator dosyaları (48/731), SVG 1.1 Tiny/Basic DOCTYPE.
- Görsel (033, resvg) SVG yolu DOCTYPE'ı hâlâ reddeder; ayrı güvenlik değerlendirmesi gerekir.
- Gerçek Illustrator clip örneği, gerçek Illustrator/Proteus DXF, diğer Proteus sürümleri.
- Fiziksel delme/üretim doğrulaması yapılmadı (donanım gerektirmez kapsamı dışında).

## Teslim
[PR #42](https://github.com/ozkurkuran/MikroCAM/pull/42), `main` hedefli; PR #41'e bağımlıdır ve
ondan sonra birleştirilmelidir (dal PR #41'in commit'lerini içerir). Birleştirme yapılmadı.
Final-head Windows CI sonucu, bu belge commit'inden sonra değişmeyeceği için PR'da ve merkezi takip
dosyasında (`docs/IS_TAKIP.md`, "SVG üretici uyumluluğu (041)") kayıtlıdır; eski bir head'in sonucu
yeni head'e aktarılmaz.
