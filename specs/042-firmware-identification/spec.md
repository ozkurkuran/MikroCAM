# Feature Specification: Firmware ailesi, sürümü ve yetenek kaydı (D1)

Feature Branch: `042-firmware-identification`
Created: 2026-10-04
Status: Specified
Input: Makine yol haritası kartı D1 `firmware-identification`
([MACHINE_CONTROL_ROADMAP §7](../../docs/MACHINE_CONTROL_ROADMAP.md), main checkout'ta yerel).
Kullanıcı kararı (04.10.2026, açık metin, `docs/IS_TAKIP.md`): “FluidNC ve grblHAL için gerekeni yap
o zaman! onları da kontrol etmek istiyorum”. Bu karar D başlama koşulu 2'yi karşılar. Koşul 1 (kart
elde) ve 3 (H3) oluşmadı: yazılım yalnız FakeGRBL profilleriyle yapılır, fiziksel doğrulama WAITING.

## Kapsam özeti

Bağlantıda karşılama satırı ve salt okunur `$I` cevabından firmware ailesi (GRBL 1.1, grblHAL,
FluidNC, bilinmeyen) ve sürümü tanınır; tek bir değişmez **yetenek kaydı** üretilir. Tek
`MachineController` korunur (ayrı controller sınıfı yok). Bilinmeyen veya henüz profili
doğrulanmamış firmware'de hareket özellikleri açıkça kapalıdır. GRBL 1.1 oturumunun bütün
hareket/iş/probe/konsol baytları, eklenen tek salt okunur `$I` sorgusu dışında birebir korunur.
D2 (grblHAL seri, spec 043) ve D3 (FluidNC seri, spec 044) bu kaydın aile profiline bağlanır.

## User Scenarios and Testing

### US1 — Bağlanınca firmware kimliği görünür (P1)

Operatör Machine panelinde Connect'e basar. Panel firmware ailesini, sürümünü, build tarihini,
bildirilen RX tamponunu, karakter sayımı bütçesini ve hareketin açık/kapalı olduğunu gerekçesiyle
gösterir. Bağımsız test: FakeGRBL'in GRBL 1.1, grblHAL, FluidNC ve bilinmeyen profilleriyle bağlanıp
gözlemi ve panel metnini doğrulamak.

Kabul:
1. GRBL 1.1h `$I` cevabı `GRBL 1.1h`, build `20190830`, RX 128, bütçe 128 ve “hareket açık” verir.
2. `Grbl 3.x [FluidNC v3.x.y …]` karşılaması ve `[VER:3.x FluidNC v3.x.y…:]` FluidNC olarak tanınır;
   “Grbl” ile başlaması onu GRBL 1.1 yapmaz.
3. `GrblHAL 1.1f …` karşılaması veya `[FIRMWARE:grblHAL]` satırı grblHAL olarak tanınır.
4. Kanıt eksik, bozuk, çelişkili veya zaman aşımına uğramışsa aile **Bilinmeyen** olur; tanı gösterilir.
5. Tanıma sürerken panel “Tanınıyor…” gösterir; bağlantı kesilince kimlik temizlenir.

### US2 — Bilinmeyen firmware'de hareket kapalı, GRBL 1.1 birebir korunur (P1)

Operatör desteklenmeyen bir kartla bağlanırsa jog, iş sıfırı, G54 seçimi, iş gönderimi, kuyruk ve
probe başlatılamaz; durdurma/iptal/abort yolları her durumda erişilebilir kalır. GRBL 1.1 kartla
bütün mevcut akışlar aynı baytları üretir. Bağımsız test: main `70800e5b` üzerinde üretilen altın
TX izleriyle 13 FakeGRBL senaryosunun karşılaştırılması ve bilinmeyen/grblHAL/FluidNC profillerinde
hareket isteklerinin hiç yazma üretmeden reddi.

Kabul:
1. GRBL 1.1 senaryolarında TX dizisi, altın izin kimlik `$I\n` eklenmiş hâline birebir eşittir;
   son gözlem (durum, konum, işlem fazları) aynıdır.
2. Bilinmeyen, grblHAL veya FluidNC tanımasında `can_jog/can_zero/can_select_g54`, `job.can_start`,
   `probe.can_start` ve kuyruk başlatma kapalıdır; doğrudan istekler `ValueError` verir ve
   hiçbir hareket/yazma baytı göndermez. Salt okunur konsol sorguları kullanılabilir kalır.
3. Tanıma bitmeden (PENDING) hareket ve konsol kapalıdır; ACK sahipliği karışmaz.

### US3 — Yetenek kaydı D2/D3 ve C3 için tek kaynaktır (P2)

Geliştirici (D2/D3 ajanı) grblHAL/FluidNC farklarını yeni controller sınıfı yazmadan aile profiline
ekler. Karakter sayımlı gönderim (C3) RX bütçesini yalnız kanıtlanmış kayıttan alır. Bağımsız test:
saf sınıflandırma testleri, profil alanları ve C3 bütçe kapısı.

Kabul:
1. Kayıt: aile, sürüm, build, protokol sürümü, build bilgisi, OPT harfleri, NEWOPT öğeleri, planner
   blok sayısı, bildirilen RX tamponu, karakter sayımı bütçesi, ek durumlar, belgelenmiş gerçek
   zamanlı komutlar (ad ile), durum raporu alanları, hareket desteği ve gerekçe notu.
2. Karakter sayımı yalnız oturum kaydında bütçe varsa ve iş başındaki `$I` kanıtı oturum kimliğiyle
   aynıysa başlar; GRBL 1.1 için bütçe `min(rx, 128)` olarak değişmez kalır.
3. grblHAL `0x87` (tam durum) ile FluidNC `0x87` (Macro0) farklı adlarla kayıtlıdır.

## Edge Cases

Port açılışında reset (ilk `$I`/`$$` kaybı, karşılama sonrası yeniden tanıma); oturum ortası reset
(aynı/farklı firmware); `$I` → `error:N`; `$I` zaman aşımı; `$I` cevabı içinde ayar satırı (sıra
bozulması); yinelenen/bozuk/çok uzun/ASCII dışı köşeli satır; 32'den fazla kanıt satırı; OPT'siz
GRBL 1.1; OPT'de `+`/`0` seçenek harfleri; RX>255 olan 3 alanlı OPT (grblHAL uyumluluk modu);
FluidNC özel başlangıç mesajı; grblHAL uyumluluk modu `Grbl 1.1f` karşılaması; Grbl_ESP32
`1.3a`; GRBL 0.9 `[0.9j…]`; karşılama ile `$I` çelişkisi; `[MSG:` satırlarının kanıta karışmaması;
tanıma sırasında Stop/Abort/Disconnect; tekrar bağlanma.

## Requirements

- **FR-001** Bağlantı açıldıktan sonra controller ilk ayar okumasından (`$$\n`) hemen önce tek bir
  salt okunur `$I\n` göndermelidir. Hareket, ayar yazma, wake/reset veya `$I+` gönderilmez.
- **FR-002** Kimlik yalnız `$I` cevabının köşeli satırları (`[MSG:` hariç) ve terminal `ok` ile
  tamamlanır. `error:N`, zaman aşımı (3 s) veya sıra bozulması kimliği **Bilinmeyen/FAILED** yapar;
  sıra bozulmasında ayar kanıtı da geçersiz sayılır (fail-closed).
- **FR-003** Sınıflandırma birincil kaynaklarda belgelenen biçimlere dayanır ([research](research.md)):
  FluidNC `[VER:<p> FluidNC v<x.y.z>…:]`; grblHAL `[FIRMWARE:grblHAL]` veya `GrblHAL ` karşılaması
  ve `<1.1f>.<YYYYMMDD>` VER; GRBL yalnız `1.1[a-z]` VER, en fazla üç alanlı OPT ve uint8 sınırları.
  Çelişki, belirsizlik veya tanınmayan ek etiket Bilinmeyen'dir.
- **FR-004** Karşılama satırı tek başına kimlik sayılmaz; yalnız reset tespiti ve `$I` ile çelişki
  denetimi için kullanılır. `Grbl ` veya `GrblHAL ` ile başlayan satır reset olarak işlenir.
- **FR-005** Reset karşılaması mevcut kimlikle tutarlıysa yalnız mevcut `$$\n` isteği gönderilir
  (GRBL 1.1 reset baytları değişmez); kimlik yoksa veya tutarsızsa `$I\n` + `$$\n` ile yeniden tanınır.
- **FR-006** Yetenek kaydı değişmez, sınırlı ve doğrulanmış bir dataclass olmalı; `MachineSnapshot`
  içinde `firmware` gözlemi olarak yayımlanmalıdır. Disconnect/hata/oturum sıfırlaması kaydı temizler.
- **FR-007** Hareket uygunluğu (jog, sıfır, G54, iş, kuyruk, probe) yalnız `IDENTIFIED` ve
  `motion_supported=True` iken açılabilir. D1'de yalnız GRBL 1.1 profili hareketi destekler;
  grblHAL ve FluidNC profilleri D2/D3 doğrulamasına kadar kapalıdır.
- **FR-008** Stop, cancel jog, abort, disconnect ve mevcut gerçek zamanlı durdurma baytları firmware
  kimliğinden bağımsız olarak erişilebilir kalmalıdır.
- **FR-009** Konsol salt okunur sorguları tanıma tamamlanınca (FAILED dahil) mevcut koşullarla
  açılır; tanıma sürerken kapalıdır.
- **FR-010** Karakter sayımı bütçesi yalnız yetenek kaydından gelir: GRBL 1.1 için `min(rx,128)`,
  diğer aileler için D2/D3 kanıtlayana kadar yok. İş başındaki `$I` kanıtı oturumdaki VER ile aynı
  olmalı; aksi hâlde kaynak gönderilmeden reddedilir. Varsayılan send-response etkilenmez.
- **FR-011** Kayıt belgelenmiş gerçek zamanlı komutları ad ile tutar; aynı byte'ın aileler arasında
  farklı anlamı (`0x87`) açıkça ayrılır. D1 yeni gerçek zamanlı byte göndermez.
- **FR-012** FakeGRBL; `grbl` (mevcut varsayılan, aynı baytlar), `grblhal`, `fluidnc` ve `unknown`
  (GRBL 0.9) profilleriyle karşılama ve `$I` cevabı üretmelidir. Gerçek seri port açılmaz.
- **FR-013** Machine paneli firmware satırını ince UI olarak gösterir (aile, sürüm, build, RX, bütçe,
  hareket durumu ve gerekçe); ham kanıt wire log'da kalır.
- **FR-014** H1 donanım protokolüne grblHAL/FluidNC/bilinmeyen tanıma senaryoları NOT_RUN olarak
  eklenir; hiçbir fiziksel hücre geçti sayılmaz.

## Key Entities

`FirmwareFamily`, `IdentificationPhase`, `FirmwareCapabilities` (yetenek kaydı),
`FirmwareObservation` (faz + kayıt + karşılama + kanıt + tanı), aile profili tablosu,
`FirmwareIdentification` (controller'a ait tek sorgu koordinatörü). Ayrıntı: [data-model](data-model.md).

## Success Criteria

- **SC-001** 13 altın GRBL 1.1 senaryosunun 13'ünde TX dizisi ve son gözlem beklenen hâle eşittir.
- **SC-002** Bilinmeyen/grblHAL/FluidNC profillerinde hareket isteklerinin %100'ü sıfır hareket baytıyla
  reddedilir; stop/abort/disconnect testleri geçer.
- **SC-003** Birincil kaynaklardan alınan her örnek satır kümesi beklenen aileye sınıflanır; çelişkili
  örneklerin hiçbiri GRBL 1.1 olarak sınıflanmaz.
- **SC-004** Mevcut test paketi, mimari testler, `pip check`, masaüstü smoke ve son-head Windows CI geçer.

## Uygulama varsayımları

Bunlar kullanıcı kararı değildir; kodda ve testlerde sabitlenmiş, gerekirse D2/D3'te değiştirilebilir
varsayımlardır.

- **UA-1** “Birebir korunur” şu anlama gelir: oturum başına eklenen tek salt okunur `$I\n` (ve port
  açılışı resetinde karşılama sonrası tekrarı) dışında GRBL 1.1 TX dizisi ve davranışı aynıdır.
  Kimlik, `$$\n`'den önce gönderilir; çünkü ayarların ve sonraki sahiplerin aileye göre yorumlanması
  kimliğe bağlıdır. Mevcut testlerin bağlantı baytı varsayımları buna göre güncellenir.
- **UA-2** grblHAL ve FluidNC D1'de tanınır, fakat durum/alarm/`$$` farkları D2/D3'te işlenene kadar
  hareket kapalıdır. Bu, doğrulanmamış protokol farklarıyla hareket riskini önler.
- **UA-3** GRBL ailesi yalnız `1.1` sürümüdür; `0.9`, Grbl_ESP32 `1.3a` vb. Bilinmeyen'dir.
- **UA-4** gnea GRBL OPT sayıları `uint8` basar (≤255) ve tam üç alanlıdır; RX>255 veya fazla alan
  grblHAL uyumluluk modu ya da başka bir çatal olabilir ve Bilinmeyen sayılır.
- **UA-5** OPT'siz `[VER:1.1x…]` GRBL 1.1 kabul edilir; RX bilinmez ve karakter sayımı kapalı kalır.
- **UA-6** `[MSG:` satırları kimlik kanıtına alınmaz; mevcut tanı yoluna gider (GRBL açılış kilidi
  mesajı kimliği bozmamalıdır).
- **UA-7** Konsol, bilinmeyen firmware'de de tanı için açıktır; yalnız mevcut salt okunur komutlar.
- **UA-8** FluidNC `$Start/Message` ile karşılamayı değiştirebilir; `Grbl `/`GrblHAL ` ile başlamayan
  bir reset karşılaması D1'de tespit edilemez. Bu risk D3'e devredilir; D1'de FluidNC hareketi kapalıdır.
- **UA-9** Kimlik zaman aşımı mevcut ayar zaman aşımıyla aynı (3 s) kabul edilir; otomatik tekrar yoktur.

## Clarifications

### Session 2026-10-04

- Kullanıcı grblHAL ve FluidNC desteğini açıkça başlattı; kart yok, H3 yapılmadı. Ajan kullanıcıya
  soru sormadan çalışır; açık noktalar yukarıda “uygulama varsayımı” olarak kayıtlıdır.
- Ayrı `MachineController` sınıfı yazılmaz (yol haritası notu, anayasa III).

## Tehlike analizi

| Tehlike | Kontrol | Kanıt |
| --- | --- | --- |
| FluidNC/grblHAL “Grbl” karşılamasıyla GRBL 1.1 sanılıp doğrulanmamış protokolle hareket | `$I` yetkili; karşılama yalnız çelişki denetimi; grblHAL/FluidNC hareketi D2/D3'e kadar kapalı | Sınıflandırma + controller ret testleri |
| Bilinmeyen firmware'e jog/iş/probe gönderilmesi | Tek uygunluk kapısı `manual.eligible()`; tüm hareket sahipleri ona bağlı | Sıfır hareket baytı testleri |
| `$I` ACK'inin ayar veya başka sahibe atanması | Kimlik tüketicisi diğer sahiplerden önce; PENDING iken konsol/hareket kapalı | Sıra/parçalı/timeout testleri |
| RX bütçesinin kanıtsız büyümesi (taşma, bozuk komut) | Bütçe yalnız GRBL 1.1 için `min(rx,128)`; diğer aileler yok; iş başı VER eşleşmesi | C3 bütçe kapısı testleri |
| `0x87` aileler arası farklı anlam (grblHAL tam durum / FluidNC Macro0) | Kayıtta adlandırılmış komutlar; D1 yeni gerçek zamanlı byte göndermez | Profil testi |
| grblHAL resetinin (`GrblHAL …`) fark edilmemesi | Reset tespiti `GrblHAL ` önekini kapsar; iş/manual/probe reset yoluna düşer | Reset testleri |
| Firmware değişimi/yeniden flaşlama sonrası eski kimlikle devam | Tutarsız karşılama → yeniden tanıma, o sırada hareket kapalı | Reset tutarsızlık testi |
| Durdurma yolunun kimlik kapısına takılması | Stop/abort/cancel/disconnect kapıya bağlı değil | Stop yolu testleri |
| FluidNC özel karşılamasıyla resetin kaçması | D1'de FluidNC hareketi kapalı; D3'e açık risk olarak devredildi | UA-8, research |

Yazılım kontrolleri fiziksel E-stop ve interlock'un yerini tutmaz. Gerçek kartlarda tanıma H1
protokolündeki H042 senaryolarıyla doğrulanana kadar **WAITING/NOT_RUN** kalır.
