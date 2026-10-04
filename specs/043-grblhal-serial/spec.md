# Feature Specification: grblHAL seri desteği (D2)

Feature Branch: `043-grblhal-serial`
Created: 2026-10-04
Status: Specified
Input: Makine yol haritası kartı D2 `grblhal-serial`
([MACHINE_CONTROL_ROADMAP §7](../../docs/MACHINE_CONTROL_ROADMAP.md), main checkout'ta yerel).
Taban: D1 firmware tanıma ([spec 042](../042-firmware-identification/spec.md), PR #44). Bu dal #44'e
bağımlıdır ve ondan sonra birleştirilir.
Kullanıcı kararı (04.10.2026, açık metin, `docs/IS_TAKIP.md`): “FluidNC ve grblHAL için gerekeni yap
o zaman! onları da kontrol etmek istiyorum”. D başlama koşulu 2 karşılandı; koşul 1 (kart elde) ve 3
(H3) oluşmadı. Bu nedenle yalnız yazılım + FakeGRBL grblHAL profili yapılır; fiziksel doğrulama
**WAITING**.

## Kapsam özeti

USB seri ile bağlanan ve D1 tarafından **grblHAL** olarak tanınan bir kart, GRBL 1.1 kullanıcılarının
yaptığı her şeyi aynı tek `MachineController` üzerinden yapabilir: jog, G54 seçimi/sıfırı, preflight +
iş gönderimi (send-response ve kanıtlanmış bütçeyle karakter sayımı), pause/resume/stop, dry run, probe
grid, autolevel, iş kuyruğu ve salt okunur konsol. Hareket, D1 yetenek kaydındaki grblHAL profili ve
kartın kendi `$I` kanıtı uygun olduğunda açılır. Ayrı controller sınıfı yazılmaz (anayasa III).
grblHAL'in protokol farkları birincil kaynaktan ([research](research.md)) doğrulanmış tek bir lehçe
katmanıyla yorumlanır; desteklenmeyen her yapılandırma hareketi açıkça kapalı tutar (fail-closed).
GRBL 1.1 oturumunun baytları ve davranışı değişmez.

## User Scenarios and Testing

### US1 — grblHAL kartıyla GRBL 1.1 akışlarının tamamı (P1)

Operatör varsayılan ayarlı, 3 eksenli (XYZ), freze modlu bir grblHAL kartına bağlanır. Firmware satırı
`grblHAL 1.1f …; motion enabled` gösterir. Jog, G54 seçimi ve sıfırı, iş (send-response ve karakter
sayımı), pause/resume/stop, dry run, probe grid + autolevel, kuyruk ve konsol GRBL 1.1'deki gibi çalışır.
Bağımsız test: FakeGRBL `grblhal` profiliyle her akışın uçtan uca tamamlanması ve wire kanıtı.

Kabul:
1. `[FIRMWARE:grblHAL]`, OPT eksen alanı `3`, `[AXS:3:XYZ]`, NEWOPT `RT+` ve `LATHE` yokken hareket açılır.
2. grblHAL `$G` (ör. `G40 G49 G98 G50 … M5 M9 T0 F0 S0`) ve `$#` (`G59.1–3`, `G28/G30`, vektör `TLO`,
   `PRB`) cevaplarıyla jog, sıfır, iş ve probe hazırlığı kanıtını tamamlar.
3. `$$` içindeki metin/IP/`N/A` değerli grblHAL ayarları iş/probe ayar kanıtını bozmaz; `$13/$30/$31/$32`
   aynı kurallarla doğrulanır.
4. Karakter sayımı grblHAL için `min(rx,128)` bütçesiyle çalışır; iş başı `$I`'nın VER ve OPT satırları
   oturum kanıtıyla birebir aynı olmalıdır.
5. Pause (`!`) `Hold:0` doğrulaması, resume (`~`), stop/abort (0x18/0x84), jog iptali (0x85) GRBL ile aynı
   baytları kullanır; grblHAL'e özgü gerçek zamanlı bayt (0x87 dahil) gönderilmez.

### US2 — grblHAL protokol farkları doğru ve fail-closed yorumlanır (P1)

Operatör grblHAL'e özgü bir durum, alarm veya ayar gördüğünde uygulama ya doğru anlamı gösterir ya da
hareketi gerekçeli olarak durdurur/kapatır; asla belirsiz kanıtla hareket göndermez. Bağımsız test: saf
ayrıştırma/lehçe testleri ve controller ret testleri.

Kabul:
1. Durum: `Run:1`, `Run:2` → Run; `Alarm:<1..255>` → Alarm; `Tool` → Unknown (ham metin görünür);
   `|AR` değer-siz alanı geçerli. GRBL 1.1 oturumunda ayrıştırma değişmez.
2. Hareket kapanır ve gerekçe görünür: eksen sayısı 3 değil / bilinmiyor, AXS `3:XYZ` değil, NEWOPT'ta
   `LATHE`, NEWOPT `RT-` veya yok.
3. Manuel/iş/probe hazırlığı reddedilir: `$G`'de `G7/G8`, `G43`, `G43.2`, `G41/G42`, `G51` (ölçekleme),
   `G66`, `G95`, `G96/G97`, `G59.1–3`, `M6` (bekleyen takım değişimi), `M53` (feed hold kapalı);
   `$#`'ta X/Y bileşeni sıfır olmayan `TLO` veya `[G51:]`.
4. `ALARM:N` ve `error:N` için aileye göre anlam tablosu durum ipucunda gösterilir; grblHAL alarm 10
   (E-stop) GRBL alarm 10'dan (çift eksen homing) ayrıdır.
5. Push `[GC:]`/`[TLO:]` raporu ($10 parser-state) veya otomatik durum raporu ($481) hareketi
   kanıtsız ilerletmez; iş/probe/manual sırasında sorgu dışı kanıt fail-closed durdurur.

### US3 — Donanımsız kanıt ve saha hazırlığı (P2)

Geliştirici/ajan grblHAL'i kartsız doğrular; operatör kart geldiğinde salt okunur aracı ve saha
senaryolarını kullanır. Bağımsız test: grblHAL profilli fault-matrix/adversarial yeniden koşusu ve H2
yardımcılarının birim testi.

Kabul:
1. C1 hata matrisi ve adversarial paketlerinin seçili testleri FakeGRBL `grblhal` varsayılanıyla geçer.
2. `tests/hardware/test_readonly_grbl.py` önce `$I` ile aileyi tanır, grblHAL lehçesiyle doğrular;
   CI'da asla çalışmaz.
3. `docs/hardware/GRBL_VALIDATION.md` H043 senaryoları **NOT_RUN** olarak eklenir.

## Edge Cases

Uyumluluk modu (`Grbl 1.1f` + üç alanlı OPT) → Unknown (D1 korunur); `GrblHAL` karşılaması + üç alanlı OPT
(seviye ≥1, `$I+` yok) → tanınır, eksen bilinmediği için hareket kapalı; 4+ eksen; lathe; `RT-`;
`Alarm:11` (homing gerekli) açılışta; `Run:1` (bekleyen feed hold); `Tool` durumu; `|AR` alanı; `|SP1:0,,`
çoklu spindle alanı; push `[GC:]`; otomatik durum raporu; G92 etkin (`G92` bayrağı); bekleyen takım
değişimi `M6`; `M53`; `G51` ölçekleme; `TLO` vektörü; `G59.1–3` satırları; `[T:…|…]`, `[HOME:]`, `[TLR:]`
satırları; metin/`N/A` ayarlar ve `$` > 255; 0x85'in okunmamış jog satırını silmesi; E-stop'ta 0x18'in yok
sayılması; probe koordinat raporu kapalı; oturum ortası `GrblHAL` reset; iş başında OPT değişimi.

## Requirements

- **FR-001** grblHAL profili hareketi destekler; `motion_allowed` yalnız `IDENTIFIED`, OPT eksen alanı
  `3`, `[AXS:]` varsa `3:XYZ`, NEWOPT'ta `RT+` ve `LATHE` yokken doğrudur. Aksi hâlde kayıt hareketi kapalı
  tutar ve gerekçeyi not olarak yayımlar.
- **FR-002** D1 sınıflandırma kuralları değişmez; uyumluluk modu cevabı Unknown kalır, `$I+` gönderilmez.
- **FR-003** grblHAL karakter sayımı bütçesi `min(rx,128)`'dir (OPT RX kanıtı). İş başındaki `$I` için VER
  ve OPT satırlarının ikisi de oturum kanıtında birebir bulunmalıdır (bütün aileler); OPT'nin grblHAL ek
  alanları (eksen, takım) kapasite denetimini bozmaz.
- **FR-004** `parse_status` grblHAL kipinde `Run:1/2`, `Alarm:1..255` alt durumlarını temel duruma, `Tool`'u
  Unknown'a eşler ve değer-siz `AR` alanını kabul eder; GRBL kipi aynı kalır.
- **FR-005** grblHAL tanındığında sorgu kanıtı tek bir lehçe fonksiyonundan geçer: `$G` nötr kelimeleri
  (G92 bayrağı, G98/G99, G50, M50/M51/M56, M60, kalıcı hareket kipleri G5/G5.1/G33/G33.1/G73/G76/G81–G89)
  kanıt dışı kalır, diğer bilinmeyen kelimeler mevcut sıkı ayrıştırıcıyla reddedilir; `$#` `G59.1–3`
  satırları yok sayılır; `[TLO:x,y,z]` yalnız `x=y=0` ise `[TLO:z]` olur; `$$` sayısal olmayan değerleri
  kanıt dışıdır. Wire log ham baytları aynen tutar.
- **FR-006** Gönderilen gerçek zamanlı baytlar GRBL kümesiyle sınırlı kalır (`?`, `!`, `~`, 0x18, 0x84, 0x85);
  grblHAL'de anlamları kaynakla doğrulanır.
- **FR-007** `GrblHAL ` karşılaması reset kanıtıdır; tutarlıysa yalnız `$$` (D1). `[MSG:Info:/Warning:]`
  tanı olarak gösterilir, kimlik ve ACK sahipliğine girmez.
- **FR-008** Alarm/hata kodlarının aileye göre kısa anlamı tek modülde tutulur (GRBL 1.1 ve grblHAL) ve
  durum ipucunda gösterilir; metin kaynak koddan kopyalanmaz.
- **FR-009** FakeGRBL `grblhal` profili grblHAL durum alanlarını (`Bf`, `FS`, `WCO`, ilk raporda `Ov`),
  `$G`, `$#`, `$$` biçimlerini, reset karşılamasını ve isteğe bağlı `Alarm:N` alt durumunu üretir.
- **FR-010** C1 hata matrisi ve adversarial testlerinin seçili kümesi grblHAL profiliyle yeniden koşulur.
- **FR-011** Stop, cancel jog, abort ve disconnect firmware ailesinden bağımsız erişilebilir kalır.
- **FR-012** H2 salt okunur araç ailenin lehçesiyle doğrular; H043 saha senaryoları NOT_RUN eklenir.
- **FR-013** GRBL 1.1 altın TX izleri (D1) birebir eşleşir.

## Key Entities

D1 `FirmwareCapabilities` (grblHAL profili ve kanıt kapısı), lehçe fonksiyonu `normalize_query_line`
(`mikrocam/machine/grblhal.py`), alarm/hata anlam tablosu (`mikrocam/machine/firmware_codes.py`),
FakeGRBL grblHAL biçimleri (`mikrocam/machine/fake_firmware.py`). Yeni kalıcı format yoktur.

## Success Criteria

- **SC-001** FakeGRBL grblHAL profiliyle jog, G54 seçimi/sıfırı, send-response ve karakter sayımlı iş,
  pause/resume, stop, probe grid, kuyruk ve konsol uçtan uca geçer.
- **SC-002** US2 kabulündeki desteklenmeyen her yapılandırmada hareket isteklerinin %100'ü sıfır hareket
  baytıyla reddedilir veya mevcut fail-closed durdurma yoluna gider.
- **SC-003** Seçili C1/adversarial testleri grblHAL profiliyle geçer; GRBL 1.1 altın izleri değişmez.
- **SC-004** Mimari testler, `pip check`, tam paket, masaüstü smoke ve son-head Windows CI geçer.

## Uygulama varsayımları

Kullanıcı kararı değildir; kod ve testte sabitlenmiştir, saha kanıtıyla değiştirilebilir.

- **UA-1** Hedef, grblHAL'in varsayılan rapor ayarlarıdır ($10 parser-state push, alarm/run alt durumu
  kapalı, `$481=0`). Bu ayarlar açıksa ek satırlar kabul edilir ama sorgu dışı `[GC:]`/`$`/`[G5`/`[TLO`
  kanıtı aktif iş/probe/manual işlemini mevcut fail-closed yoldan durdurur; ayar okunmaz veya yazılmaz.
- **UA-2** grblHAL RX 1024 bildirse de C3 penceresi 128 baytla sınırlıdır (C3'ün doğrulanmış üst sınırı;
  grblHAL halka tamponu RX−1 kullanılabilir olabilir). Daha büyük pencere H3 ölçümüyle ayrı iş olur.
- **UA-3** Yalnız 3 eksen (XYZ) ve freze modu ($32=0, NEWOPT'ta `LATHE` yok) desteklenir.
- **UA-4** grblHAL 0x85 jog iptalinde RX tamponunu boşaltır; iptal edilen jog satırı okunmamışsa `ok`
  gelmez, mevcut iptal süresi dolar ve fail-closed abort/reset yolu çalışır (hareket başlamamıştır).
- **UA-5** MPG modu, SD akışı ve 4+ eksen desteklenmez; ilgili raporlar (`|MPG:1`'de ana akış cevapsız,
  boşluklu `|SD:`, 4 değerli konum) zaman aşımı veya geçersiz rapor olarak fail-closed işlenir.
- **UA-6** E-stop alarmında (grblHAL alarm 10) kart 0x18'i yok sayar; Abort “stop unverified” kalır.
- **UA-7** Probe koordinat raporu ($10 bit 7) kapalıysa probe “contact evidence” eksikliğiyle reddedilir.
- **UA-8** Alarm/hata açıklamaları MikroCAM'in kendi kısa İngilizce ifadeleridir; yalnız kod numaraları
  ve anlamları (olgu) kaynaktan alınır.
- **UA-9** `RT-` (legacy gerçek zamanlı komutlar kapalı) iken `?`/`!`/`~` bir `$` satırı veya yorum
  işlenirken düz karakter olarak tampona girebilir; bu nedenle hareket `RT+` ister.
- **UA-10** Otomatik/push durum raporları sorguya atfedilebilir; atıf yalnız referans olaydan (ACK veya
  yazma) sonra alınan rapora dayanır, en kötü durumda işlem fail-closed biter.
- **UA-11** `$#`'taki `G59.1–3`, `G28/G30`, `[HOME:]`, `[T:]`, `[TLR:]` satırları kanıt dışıdır; sıfır sonrası
  değişmezlik doğrulaması GRBL'deki envanterle (G54–G59, G92, TLO) sınırlıdır. MikroCAM bu kayıtları yazmaz.

## Clarifications

### Session 2026-10-04

- Ajan kullanıcıya soru sormadan çalışır; açık noktalar yukarıda “uygulama varsayımı” olarak kayıtlıdır.
- Ayrı `MachineController` sınıfı yazılmaz; fark tek profil, tek lehçe fonksiyonu ve ayrıştırıcı bayrağıdır.

## Tehlike analizi

Bu spec grblHAL kartlarında **hareketi açar**.

| Tehlike | Kontrol | Kanıt |
| --- | --- | --- |
| grblHAL'e GRBL varsayımıyla yanlış eksen/kip yorumu (4+ eksen, lathe çap modu, ölçekleme) | Eksen=3, AXS `3:XYZ`, `LATHE` yok kapısı; `G7/G8/G51/G95/G96` ret; `$32=0` | Sınıflandırma + lehçe + controller ret testleri |
| `[GC:]`/`$#` farkının sıfırı yanlış hesaplatması (vektör TLO, G59.x) | Vektör TLO yalnız X=Y=0 ise Z'ye indirgenir; G59.x yok sayılır; sıfır sonrası okuma doğrulaması korunur | Sıfır uçtan uca + TLO ret testi |
| Bekleyen takım değişimi (`M6`, `Tool`) veya feed hold kapalıyken (`M53`) hareket | `M6`/`M53` modal ret; `Tool` Unknown → Idle değil | Lehçe + durum testleri |
| `RT-` iken `?`/`!` düz karakter olup iş satırını bozması, pause'un çalışmaması | Hareket `RT+` ister | Kapı testi |
| Bilinmeyen grblHAL alt durumunun Idle/Run sanılması | Yalnız belgelenmiş `Run:1/2`, `Alarm:n` eşlenir; diğerleri Unknown | Durum testleri |
| Büyük RX'e güvenip tampon taşması | Bütçe `min(rx,128)`; iş başı VER+OPT eşleşmesi | C3 testleri |
| Alarm 10'un yanlış anlamlandırılıp operatörün E-stop'u gözden kaçırması | Aileye göre anlam tablosu | Tablo testleri |
| Push/otomatik raporun eski durumu taze sanması | Atıf alım sırasına dayanır; push sorgu kanıtı aktif işlemi durdurur | Adversarial testler |
| 0x85'in okunmamış satırı silmesiyle ACK beklemede kalma | Mevcut deadline → fail-closed abort | Jog iptal testi |
| Durdurma yolunun aileye bağlanması | Stop/abort/cancel/disconnect kapısız | Fault-matrix grblHAL koşusu |
| Uyumluluk modu kartın GRBL sanılması | D1: Unknown, hareket kapalı | D1 testleri korunur |

Yazılım kontrolleri fiziksel E-stop, muhafaza ve interlock'un yerini tutmaz. Gerçek grblHAL kartında
hareket H043 senaryolarıyla doğrulanana kadar **WAITING/NOT_RUN** kalır.
