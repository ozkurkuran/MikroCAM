# Feature Specification: FluidNC seri (USB) desteği (D3)

Feature Branch: `044-fluidnc-serial`
Created: 2026-10-04
Status: Specified
Input: Makine yol haritası kartı D3 `fluidnc-serial`
([MACHINE_CONTROL_ROADMAP §7](../../docs/MACHINE_CONTROL_ROADMAP.md), main checkout'ta yerel).
Kullanıcı kararı (04.10.2026, açık metin, `docs/IS_TAKIP.md`): “FluidNC ve grblHAL için gerekeni yap
o zaman! onları da kontrol etmek istiyorum”. D başlama koşulu 2 karşılandı; koşul 1 (kart elde) ve 3
(H3) oluşmadı. Yazılım yalnız FakeGRBL FluidNC profiliyle yapılır; fiziksel doğrulama **WAITING**.
Bağımlılık: D1 (spec 042, PR #44). Kapsam yalnız USB seri; TCP/WebSocket (D4) ve SD'den iş (D5) dışarıda.

## Kapsam özeti

FluidNC (ESP32) kartı USB seri ile bağlandığında GRBL 1.1 kullanıcısının yapabildiği her şey —
jog, G54 seçimi/iş sıfırı, preflight + iş gönderimi, pause/resume/stop, dry run, probe grid,
autolevel çıktısının gönderimi, iş kuyruğu ve salt okunur konsol — aynı tek `MachineController`
üzerinden, D1 yetenek kaydı açtığında kullanılabilir. Ayrı controller sınıfı yoktur (anayasa III).
FluidNC'nin GRBL'den farklı olduğu yerlerde (başlangıç satırları yerine YAML makroları, `$$`
vekil ayarları, `$#` TLO biçimi, özelleştirilebilir karşılama, ESP32 boot/reset, otomatik rapor,
`0x87` Macro0) MikroCAM kanıtı FluidNC'nin kendi salt okunur biçimlerinden yeniden türetir ya da
açıkça **desteklenmez** der ve hareketi kapalı tutar (fail-closed). GRBL 1.1 baytları değişmez.

## User Scenarios and Testing

### US1 — FluidNC kartı tanınır, boot/reset güvenle izlenir ve manuel hareket açılır (P1)

Operatör FluidNC kartının COM portunu seçip Connect'e basar. Port açılışı ESP32'yi yeniden
başlatabilir; MikroCAM boot satırlarını ve özel karşılamayı reset olarak işler, kart hazır olunca
kimliği ve ayarları yeniden okur. Firmware satırı `FluidNC x.y.z … motion enabled` gösterir.
Jog, Use G54 ve G54 sıfırı GRBL 1.1'deki gibi çalışır; her işlemden önce FluidNC başlangıç
makroları (`startup_line0/1`, `after_reset`) ve otomatik rapor durumu salt okunur doğrulanır.
Bağımsız test: FakeGRBL `fluidnc` (v4.1.1) ve `fluidnc3` (v3.9.9) profilleriyle bağlanma, boot
dizisi, özel karşılama ve manuel işlem yolculukları.

Kabul:
1. FluidNC 3.x/4.x tanınınca `motion_allowed` doğrudur; diğer ana sürümler tanınır ama hareket kapalıdır.
2. Jog/zero/G54 öncesi TX `$/macros/startup_line0`, `$/macros/startup_line1`, `$/macros/after_reset`,
   `$RI` sorgularını içerir; `$N` FluidNC'ye hiç gönderilmez. Dolu makro veya açık otomatik rapor
   işlemi hareket baytı gönderilmeden reddeder.
3. Bağlantıdan sonra gelen ESP32 ROM satırları (`ets …`, `rst:0x…`, `ESP-ROM:`) veya
   `[MSG:INFO: FluidNC v…]` yeniden başlama sayılır: kimlik ve birim kanıtı temizlenir, aktif
   işlemler reset olarak biter; 2 s sessizlik ve `Starting` olmayan taze durumdan sonra `$I`+`$$`
   yeniden gönderilir. Kart hazır olmadan yazma yapılmaz.
4. Tanınmış FluidNC oturumunda protokol biçiminde olmayan herhangi bir satır (ör. özel
   `$Start/Message` karşılaması) olası reset sayılır; aktif hareket durdurulur ve aynı bekleme
   yolu ile yeniden tanıma yapılır. Karşılama metnine güvenilmez.

### US2 — İş, kuyruk, probe ve durdurma yolları FluidNC'de çalışır (P1)

Operatör preflight'tan geçmiş bir işi, kuyruğu veya probe grid'ini FluidNC kartında başlatır;
Pause/Resume/Stop/Abort GRBL 1.1'deki baytlarla çalışır. Karakter sayımı FluidNC'de RX tamponu
kanıtlanamadığı için reddedilir. Bağımsız test: send-response iş, hold/resume, stop, kuyruk ve
probe grid'in FluidNC profilinde tamamlanması; C1 hata matrisi testlerinin FluidNC profilinde
yeniden çalıştırılması.

Kabul:
1. İş kabulü FluidNC `$$` vekil ayarlarından `$13` birim, `$32=0` (lazer modu kapalı) ve
   `$30` azami devir ile yapılır; FluidNC `$31` bildirmez, alt sınır 0 kabul edilir (uygulama varsayımı).
2. `$#` içindeki v4 vektör `[TLO:x,y,z]` yalnız X/Y bileşenleri 0 ise Z TLO olarak kabul edilir.
3. Feed hold `!`, resume `~`, stop/abort `0x18`/`0x84`, jog iptali `0x85` aynıdır; `0x87`–`0x8A`
   (FluidNC Macro0–3) hiçbir yoldan gönderilemez.
4. Character counting FluidNC'de iş başlamadan reddedilir; send-response etkilenmez.

### US3 — Tanı, saha protokolü ve hata matrisi (P2)

Operatör konsolda FluidNC YAML yapılandırmasını salt okunur `$CD` (Config/Dump) ile görür;
`[MSG:…]` satırları tanı alanına düşer. H protokolüne FluidNC senaryoları NOT_RUN olarak eklenir.
Bağımsız test: konsol `$CD` yalnız FluidNC'de, `$N` FluidNC'de reddedilir; H2 salt okunur envanter
FluidNC'de makro ve `$RI` sorgularını ekler; hata matrisi FluidNC profiliyle yeşildir.

Kabul:
1. `$CD` konsolda yalnız tanınmış FluidNC oturumunda gönderilir; GRBL/bilinmeyen oturumda bayt
   yazılmadan reddedilir. FluidNC'de `$N` reddedilir (FluidNC'de başlangıç satırı sorgusu değildir).
2. `docs/hardware/GRBL_VALIDATION.md` H044 satırları ve uyumluluk matrisi NOT_RUN'dır.
3. C1 matrisinin (bağlanma, jog, sıfır, iş, hold, probe, konsol) ACK sınırı, parçalı ACK, aktif hata,
   SerialException, non-Idle ve tekrar bağlanma testleri FluidNC profilinde geçer.

## Edge Cases

Port açılışında ESP32 reset ve ilk `$I`/`$$`'ın kaybı; FluidNC yumuşak resetinde `flushRx` ile
bekleyen komutların kaybı; boş veya özel `$Start/Message`; `$Message/Level` Info altında (boot
satırı ve `$RI` cevabı yok); boot sırasında ASCII dışı çöp bayt; `Starting` durumu; v3'te
`Starting` olmaması; `after_reset`/`startup_line*` dolu; `$RI` açık; `$CD` uzun YAML; 4+ eksen;
`M56` park override; boş `|A:` alanı; SD ilerleme alanı; `Alarm` (FluidNC alt kod basmaz);
`ALARM:14` (Unhomed) boot; `error:130` jog iptali (FluidNC `ok` döner); çok iğli yapılandırma
(`$30/$32` mevcut iğe aittir; M6/M61 preflight'ta reddedilir); ESP32-S3 yerel USB'de DTR/RTS ile
indirme moduna geçiş; tanınan sürümün 3.x/4.x dışı olması.

## Requirements

- **FR-001** Tanınmış FluidNC 3.x/4.x için yetenek kaydı `motion_supported=True` olur; diğer FluidNC
  ana sürümleri tanınır, hareket kapalı kalır ve gerekçe gösterilir. RX bütçesi yoktur.
- **FR-002** Manuel, iş ve probe sahipleri FluidNC'de `$N` yerine sırasıyla `$/macros/startup_line0`,
  `$/macros/startup_line1`, `$/macros/after_reset` ve `$RI` sorgularını kullanır; üç makro boş ve
  otomatik rapor kapalı olmadıkça hareket ve reset (`0x18`) yetkisi verilmez. GRBL'de `$N` aynen kalır.
- **FR-003** FluidNC iş kabulü `$13`, `$30`, `$32` vekil ayarlarını doğrular; `$31` yoksa alt sınır 0.
  Probe kabulü mevcut `$13`/`$32` kontrolünü kullanır.
- **FR-004** `$#` TLO satırı skaler (GRBL, FluidNC v3) veya X/Y'si sıfır üç bileşenli vektör (FluidNC
  v4) olabilir; başka biçim reddedilir.
- **FR-005** Boot işaretleri (ESP32 ROM `ets `, `rst:0x`, `ESP-ROM:` ve `[MSG:INFO: FluidNC v`) her
  aile için yeniden başlama sayılır; tanınmış FluidNC oturumunda serbest metin satırı olası reset
  sayılır. İkisi de kimlik/birim kanıtını geçersiz kılar ve aktif işlemleri bitirir.
- **FR-006** Yeniden başlama sonrası `$I`+`$$` ancak son serbest/MSG satırından 2 s sonra ve
  `Starting` olmayan taze bir durum raporuyla gönderilir; varsayılan karşılama geldiğinde D1 yolu
  hemen çalışır. Otomatik tekrar yoktur; zaman aşımı fail-closed kalır.
- **FR-007** `0x87`–`0x8A` hiçbir doğrulayıcıdan geçemez; kayıtta Macro0–3 olarak adlandırılır.
- **FR-008** Konsol `$CD` komutunu yalnız tanınmış FluidNC'de, `$N`'yi yalnız FluidNC dışında gönderir.
- **FR-009** FakeGRBL `fluidnc` (v4.1.1) ve `fluidnc3` (v3.9.9) profilleri karşılama, `$I`, `$$`,
  `$#`, makro, `$RI`, `$CD`, `FS` alanlı durum, özel karşılama, boot dizisi (ROM, `Starting`,
  `flushRx`) ve otomatik rapor durumu üretir; Macro baytları FakeGRBL'in de kullandığı
  doğrulayıcıda reddedilir. Gerçek seri port açılmaz.
- **FR-012** Konsol `$$` cevabındaki `$130-$132` satırları rapor birimi sayılmaz (GRBL ve FluidNC;
  044 sırasında bulunan hata, önce-test düzeltildi).
- **FR-010** GRBL 1.1 altın TX izleri (D1) birebir korunur; seri taşıma ve DTR/RTS davranışı değişmez.
- **FR-011** H2 salt okunur envanter FluidNC algılarsa makro/`$RI` sorgularını ekler (yalnız okuma);
  H044 saha senaryoları NOT_RUN olarak eklenir.

## Key Entities

`fluidnc` saf modülü (boot/serbest metin sınıflandırma, makro/`$RI` kanıtı, `$$` doğrulaması),
`StartupEvidence` (aileye göre başlangıç kanıtı sorgu planı; manuel/iş/probe üç somut kullanım),
`FirmwareIdentification` yeniden başlama bekleme durumu, FakeGRBL FluidNC davranışı (`FakeFluidNC`).

## Success Criteria

- **SC-001** FluidNC profilinde jog, zero, G54, send-response iş, hold/resume, stop, kuyruk ve probe
  grid yolculuklarının hepsi tamamlanır; GRBL 1.1 13 altın iz değişmez.
- **SC-002** Dolu makro, açık `$RI`, eksik `$RI` cevabı, 4+ eksen, `M56`, bilinmeyen ana sürüm ve
  character counting senaryolarının %100'ü sıfır hareket baytıyla reddedilir.
- **SC-003** Boot/özel karşılama senaryolarının hiçbirinde kart hazır olmadan `$I`/`$$` gönderilmez
  ve eski birim/kimlik kanıtıyla hareket açılmaz.
- **SC-004** Mevcut test paketi, mimari testler, `pip check`, masaüstü smoke ve son-head Windows CI geçer.

## Uygulama varsayımları

Kullanıcı kararı değildir; kodda/testte sabitlenmiş, saha kanıtıyla değiştirilebilir varsayımlardır.

- **UA-1** Desteklenen FluidNC protokol ana sürümleri 3 ve 4'tür (kaynaklar v3.9.9, v4.1.1). Daha
  eski 3.x sürümlerinde makro/`$RI` sorgusu hata verirse işlem fail-closed reddedilir.
- **UA-2** GRBL `$N0/$N1` karşılığı FluidNC'de `macros/startup_line0/1` (yalnız boot sonrası ilk
  Idle'da) ve `macros/after_reset` (`0x18` sonrası Idle'da) makrolarıdır; üçü boş olmalıdır.
  `after_homing`/`after_unlock` MikroCAM `$H`/`$X` göndermediği için kontrol edilmez.
- **UA-3** Otomatik rapor kapalı olmalıdır (`$RI` → `auto reporting is off`). `$Message/Level`
  Info altındaysa cevap gelmez ve işlem gerekçeyle reddedilir.
- **UA-4** FluidNC `$31` bildirmez; iş devri alt sınırı 0 kabul edilir. Hız haritası tabanının altındaki
  devirler denetleyicide yükseltilebilir; bu fiziksel güvenlik değil, mekanik hız uyumu konusudur.
- **UA-5** DTR/RTS politikası değiştirilmez (GRBL Arduino davranışı korunur); port açılışı ESP32'yi
  yeniden başlatabilir. Boot yazılımda izlenir, gerçek kartta H044 ile ölçülecektir (WAITING).
- **UA-6** Yeniden başlama sessizlik süresi 2 s'dir; özel karşılama + Info altı mesaj seviyesi
  birlikteyse ilk tanıma başarısız olabilir (Disconnect/Connect; varsayılan karşılama önerilir).
- **UA-7** Tanınmış FluidNC oturumunda serbest metin satırı her zaman olası reset sayılır (yanlış
  pozitif yalnız işlemi durdurur ve yeniden tanır; güvenli taraftır). `$CD` YAML'ı konsol sahibidir.
- **UA-8** Alarm/hata kodları ham gösterilir; FluidNC'ye özgü kod metin tablosu eklenmez.
- **UA-9** 4+ eksenli FluidNC, `M56`, boş `|A:` ve boşluk içeren SD ilerleme alanı desteklenmez;
  ayrıştırıcılar reddeder ve hareket kapanır.
- **UA-10** Homing ve unlock MikroCAM'de yoktur (GRBL ile aynı); `ALARM:14` Unhomed sonrası
  operatör başka bir araçla homing yapar ve yeniden bağlanır.

## Clarifications

### Session 2026-10-04

- Kullanıcı FluidNC desteğini açıkça başlattı; kart yok, H3 yapılmadı. Ajan soru sormadan çalışır;
  açık noktalar “uygulama varsayımı” olarak yukarıdadır.
- Ayrı `MachineController` sınıfı yazılmaz (yol haritası notu, anayasa III).

## Tehlike analizi

Bu spec FluidNC kartlarında hareketi açar. Yazılım kontrolleri fiziksel E-stop ve interlock'un
yerini tutmaz; FluidNC'de hareket gerçek kartta H044 ile doğrulanana kadar **fiziksel olarak
doğrulanmamış** sayılır.

| Tehlike | Kontrol | Kanıt |
| --- | --- | --- |
| `0x18` sonrası `after_reset` makrosunun hareket G-code'u çalıştırması | Reset yetkisi yalnız üç makro boş doğrulanınca; aksi hâlde `0x84` (park olabileceği söylenir) | Makro dolu/eksik testleri, stop baytı testi |
| Boot sonrası `startup_line0/1` hareketi | Makrolar her hareket öncesi okunur; dolu ise ret. Port açılışındaki ilk boot MikroCAM'in kontrolü dışındadır → kullanıcı belgesi ve H044 | Makro testleri, belge |
| `0x87` (FluidNC Macro0) gönderilip makro çalışması | Doğrulayıcı izin listesinde yok; kayıtta Macro adıyla | Doğrulayıcı ve tüm yolculuklarda bayt taraması |
| Port açılışında ESP32 reset; eski birim/kimlik ile hareket | Boot işaretleri reset sayılır; kimlik/birim temizlenir; hazır olana kadar yazma yok | Boot dizisi testleri |
| Özel karşılama ile yumuşak resetin kaçması | Tanınmış FluidNC'de serbest metin = olası reset; aktif hareket durdurulur | Özel karşılama testleri |
| Otomatik raporun beklenmeyen `[GC:`/`[G54:` satırlarıyla sahipleri bozması | `$RI` kapalı değilse hareket reddi | `$RI` testleri |
| Lazer modu açık iğe mekanik iş | `$32=0` zorunlu | Ayar testleri |
| `$31` eksikliği ile alt devir sınırının doğrulanamaması | Alt sınır 0; üst sınır `$30`; belge | Ayar testleri |
| v4 vektör TLO'nun yanlış yorumlanması | Yalnız X/Y=0 ise Z; değilse ret | Parametre testleri |
| 4+ eksen koordinatlarının 3 eksen sanılması | Durum ve `$#` tam üç değer ister | Ayrıştırıcı testleri |
| RX tamponu bilinmeden karakter sayımı | FluidNC bütçesi yok; mod reddedilir | C3 kapı testi |
| Bağlantı kopması/zaman aşımı | Mevcut fail-safe yollar aynen; FluidNC profilinde matris | Hata matrisi testleri |
| ESP32-S3 yerel USB'de DTR/RTS dizisiyle indirme moduna geçiş | Kimlik zaman aşımı → Unknown, hareket kapalı; DTR/RTS değiştirilmez | Zaman aşımı testi, H044 |

Durdurma yolları (Stop, Cancel jog, Abort, Disconnect) firmware kimliğinden bağımsız kalır.
