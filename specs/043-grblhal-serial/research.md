# Research: grblHAL seri desteği (043)

Bütün biçimler 04.10.2026'da birincil kaynak koddan okundu ve satır numaralarıyla aşağıdadır. Kaynak
kod yalnız davranış/biçim kanıtı olarak incelendi; MikroCAM'e kod veya açıklama metni kopyalanmadı
(grblHAL ve gnea GRBL GPLv3'tür; anayasa VII). Alarm/hata tablolarında yalnız kod numaraları ve
anlamları (arayüz olgusu) kullanıldı; açıklamalar MikroCAM'in kendi kısa ifadeleridir.

## Kaynaklar

| Kısa ad | Kaynak | Sabit sürüm |
| --- | --- | --- |
| HAL | https://github.com/grblHAL/core (`report.c`, `protocol.c`, `config.h`, `grbl.h`, `stream.h`, `gcode.h`, `alarms.h`, `errors.h`, `motion_control.c`, `system.c`, `settings.c`, `grbllib.c`) | `c3a887e3e366f91e26813bb6072479d719cac83a` (D1 ile aynı commit) |
| GRBL | https://github.com/gnea/grbl (`grbl/report.c`, `grbl/report.h`, `grbl/system.h`, `doc/csv/alarm_codes_en_US.csv`) | `bfb67f0c7963fe3ce4aaf8a97f9009ea5a8db36e` |
| D1 | [042 research](../042-firmware-identification/research.md) | PR #44 head `164da247` |

Satır numaraları yukarıdaki sabit commit'lere aittir (`HAL report.c:1274` = grblHAL `report.c` satır 1274).

## R0 — Ayrı hotfix: GRBL OPT harfleri `0` ve `+`

GRBL `report.c:375-441` OPT harflerini basar; `'0'` `SPINDLE_ENABLE_OFF_WITH_ZERO_SPEED` ile (`:407`),
`'+'` `ENABLE_SAFETY_DOOR_INPUT_PIN` ile (`:419`). C3 `verified_capacity` deseni bu iki harfi
reddediyordu; bu kartlarda karakter sayımı güvenli tarafta ama yanlışlıkla kapanıyordu. Spec dışı,
önce-test hotfix commit'i olarak düzeltildi (043 dalındaki ilk commit). grblHAL de `0` ve `+` basar
(HAL `report.c:960`, `:972`).

## R1 — Çerçeveleme, karşılama, mesajlar

- `ok`/`error:N` biçimi GRBL ile aynı (HAL `report.c:213-226`); `ALARM:N` aynı (`:229-235`).
- `[MSG:` satırları `Info: `, `Warning: `, `Error: `, `Debug: ` önekleri alabilir (`report.c:238-269`).
  Mevcut controller `[MSG:` satırlarını tanıya yönlendirir; kimlik/ACK sahipliğine girmez (D1 UA-6).
- Karşılama seviye 0'da `\r\nGrblHAL 1.1f ['$' or '$HELP' for help]\r\n` (`report.c:307-316`); D1 reset
  tespiti `GrblHAL ` önekini zaten kapsar.

## R2 — `$I` ve hareket kapısı kanıtı

- OPT: `[OPT:<harfler>,<planner>,<rx>,<eksen>,<takım>]`; planner `plan_get_buffer_size()` (`:1001`), RX
  `hal.rx_buffer_size` (`:1003`), eksen ve takım sayısı yalnız uzatılmış çıktıda (`:1004-1009`); seviye 0'da
  uzatılmış çıktı zorunludur (`:918-920`). Varsayılan `RX_BUFFER_SIZE 1024` (`stream.h:53`).
- `[AXS:<n>:<harfler>]` (`:1018-1028`), `[NEWOPT:ENUMS,RT+|RT-,…]` (`:1030-1110`; `RT±` legacy gerçek
  zamanlı komut ayarı `:1031`, lathe modunda `LATHE` `:1066-1073`), `[FIRMWARE:grblHAL]` (`:1111`).
- Karar: hareket yalnız eksen alanı `3`, AXS varsa `3:XYZ`, `RT+` ve `LATHE` yokken açılır. MikroCAM
  konum/WCO/probe ayrıştırıcıları tam üç eksen bekler (`grbl._vector`); 4+ eksen raporu geçersiz olur.

## R3 — Gerçek zamanlı komutlar

- `0x18` reset; E-stop sinyali etkinse reset yapılmaz (`protocol.c:863-866`). `0x84` güvenlik kapısı
  (`:899-904`). `0x85` jog iptali satırı temizler ve **RX okuma tamponunu boşaltır** (`:906-917`).
- `0x87` tam durum raporu (`:877-881`) ve diğer grblHAL baytları (`grbl.h:103-157`) MikroCAM tarafından
  gönderilmez. `0x80` (`:883-887`) otomatik raporlama açıkken yok sayılır.
- Yazdırılabilir `?`, `~`, `!` ikinci aşamada işlenir (`protocol.c:1005-1021`): ana ayrıştırıcının o anki
  satırı `$`/yorum değilse veya legacy RT açıksa gerçek zamanlıdır. `keep_rt_commands` ana ayrıştırıcının
  tek `line` yapısındadır (`protocol.c:56-61`, `:851-854`, `:99-103`). Varsayılan `DEFAULT_LEGACY_RTCOMMANDS On`
  (`config.h:826`). `RT-` iken bir `$` satırı veya yorum işlenirken gelen `?`/`!` girdiye karışabilir →
  hareket `RT+` ister (UA-9).

## R4 — Durum raporu (`report_realtime_status`, `report.c:1240-1652`)

- Durumlar: `Idle`, `Run` + `:1` (bekleyen feed hold; ayardan bağımsız `:1273-1274`) veya `:2` (probe,
  `run_substate` ayarıyla `:1268-1276`), `Hold:<0|1>` (`:1279-1281`), `Jog`, `Home`, `Alarm` veya
  `Alarm:<kod>` (alarm alt durumu ayarı veya 0x87 ile `:1291-1297`; E-stop da Alarm), `Check`,
  `Door:<0-3>`, `Sleep`, `Tool` (`:1312`).
- Alanlar: `MPos`/`WPos`, `Bf`, `Ln`, `DTG`, `FS:<f>,<s>[,<gerçek rpm>]` veya `F`, `SP<n>:` (çoklu spindle,
  boş alt alanlı `…,,` `:1385-1393`), `Pn`, `Ov`, `WCO`, `WCS`, `A`, `Sc`, `AR` **değersiz olabilir**
  (`:1546-1551`), `MPG`, `H`, `D`, `T`, `P`, `TLR`, `In`; `FW:grblHAL` yalnız 0x87 tam raporunda (`:1590-1593`).
- WCO/Ov sayaçlı tekrar (`config.h:247-256`; `report.c:1446-1484`): controller WCO önbelleği GRBL'deki gibi
  çalışır.
- Varsayılanlar: parser-state push kapalı (`config.h:715`), alarm alt durumu kapalı (`:729`), run alt
  durumu kapalı (`:742`), otomatik rapor `$481=0` (`config.h:2150`; açılışta `grbllib.c:477`).
- Push raporlar: parser-state açıkken durum raporu sonrası `[GC:…]` (`report.c:1600-1647`), TLO raporu
  (`:1633-1634`, işleme `protocol.c:616-620`), homing başında (`motion_control.c:885-888`) ve takım değişimi sonunda
  (`state_machine.c:480-481`) zorla durum raporu.

## R5 — `$G` (`report_gcode_modes`, `report.c:757-888`)

Sıra: hareket kipi (`motionmode_to_str` `:740-755`: G0–G3, G5, G5.1, G33, G33.1, G38.2–5, G73, G76,
G81–G86, G89, G80; `gcode.h:98-126`), WCS (G54–G59, G59.1–3 `gcode.h:194-196`), etkin G92 bayrağı
` G92` (`:766-767`), lathe'de G7/G8 (`:771-772`), düzlem, G20/G21, G66, G90/G91, G93/G94/G95
(`:784-785`), lathe G96/G97, G40/G41/G42 (`:790-797`), G49/G43/G43.1/G43.2 (`:801-808`), G98/G99
(`:811`), G50 veya `G51:<eksenler>` (`:813-818`), M0/M1/M2/M30/M60, M3/M4/M5, bekleyen takım değişimi
` M6` (`:853-854`), M7/M8/M9, M50/M51/M53/M56 (`:867-878`), T, F, S.

Karar (lehçe): nötr → kanıt dışı: G92 bayrağı (sayısal G92 `$#`'tan doğrulanır), G98/G99, G50, M50, M51,
M56, M60, kalıcı hareket kipleri (MikroCAM'in jog `$J=`, `G10 L20`, `G54` ve probe satırları hareket
kipini açıkça verir veya hareket içermez). Geri kalan ek kelimeler mevcut sıkı ayrıştırıcıda reddedilir.

## R6 — `$#` (`report_ngc_parameters`, `report.c:613-724`)

`[G51:]` (ölçekleme etkinse), `[G54:]…[G59:]`, `[G59.1:]…[G59.3:]`, `[G28:]`, `[G30:]`, `[G92:]`,
`[T:…|…]` takım tablosu, `[HOME:…:<maske>]` (homing açıksa), `[TLO:]`, `[PRB:…:<0|1>]`, `[TLR:]`/`[TLR@:]`.
TLO: `TOOL_LENGTH_OFFSET_AXIS -1` varsayılandır (“all axes”, `config.h:302`) → `[TLO:x,y,z]` vektörü
(`report.c:563-572`); seviye >2'de Z (`grbl.h:240-243`). Karar: vektör yalnız X=Y=0 ise Z'ye indirgenir.

## R7 — `$$`, `$N`, `$13`, `$32`

- `$$` seviye ≤1'de bütün çekirdek+sürücü+eklenti ayarlarını basar (`system.c:300-317`); değeri olmayan
  ayar `$<id>=N/A` (`report.c:445-456`), metin/IP/parola biçimleri vardır (`settings.c:524`). Kimlikler
  255'i aşar. Karar: sayısal olmayan değerler kanıt dışı; `$13/$30/$31/$32` sayısal kalır.
- `$13` rapor inç (`settings.c:2383`), `$32` çalışma modu Normal/Laser/Lathe (`settings.c:2415`).
- `$N<n>=<satır>` (`report.c:890-895`), `N_STARTUP_LINE 2` (`grbl.h:166`).

## R8 — Probe

`[PRB:x,y,z:<0|1>]` (`report.c:540-549`); döngü sonunda yalnız `$10` probe-koordinat biti açıksa basılır
(`motion_control.c:1090-1091`, varsayılan açık `config.h:690`). Temassız sonuç `Alarm_ProbeFailContact`
(5) (`motion_control.c:1063-1068`), GRBL ile aynı.

## R9 — Alarm ve hata kodları

- grblHAL alarmları 1–22 (`alarms.h:27-51`); “0–9 eski Grbl ile aynı, 15 eski Grbl 10'a eşit”
  (`alarms.h:28`). GRBL 1.1h alarm 10 çift eksen homing hatasıdır (GRBL `system.h:41-50`,
  `alarm_codes_en_US.csv`). Aynı sayı iki ailede farklı anlamdadır → tablo aileye göre seçilir.
- grblHAL hataları 1–92 ve 253 (`errors.h:32-129`); 1–37 GRBL 1.1 ile aynı anlamda (GRBL `report.h:24-61`),
  38 GRBL'de “değer çok büyük”, grblHAL'de “geçersiz takım tablosu girdisi”.

## R10 — Karakter sayımı

RX 1024 bildirilir; grblHAL sürücü halka tamponlarında tam dolu = boyut−1 olabilir. C3 penceresi 1..128
bayt doğrulanmıştır (`job_stream.JobStream`). Karar: bütçe `min(rx,128)`; iş başı `$I` kanıtında VER ve
OPT birebir oturum kanıtıyla aynı olmalı; `verified_capacity` grblHAL'in iki ek OPT alanını kabul eder.

## Kararlar

| Karar | Gerekçe | Reddedilen alternatif |
| --- | --- | --- |
| Tek controller; profil + `parse_status(grblhal=True)` + tek lehçe fonksiyonu | Anayasa III, yol haritası notu | grblHAL controller sınıfı |
| Lehçe controller sınırında, wire log'dan sonra | Ham bayt tanı için korunur; manual/iş/probe tek kanıt yolunu kullanır | Her ayrıştırıcıya ayrı grblHAL dalı |
| Nötr kelimeleri at, diğerlerini reddet | En az değişiklik, belirsiz kipte fail-closed | Bütün grblHAL kelimelerini modele eklemek |
| `0x87` göndermemek | `?` + WCO önbelleği yeterli; 0x87 rapor bayraklarını değiştirir | Her sorguda tam rapor |
| Bütçe 128 | C3 üst sınırı; RX−1 belirsizliği | 1024/1023 pencere (ölçüm yok) |
| `RT+`, 3 eksen, `LATHE` yok kapısı | Gönderdiğimiz baytların ve 3 eksen ayrıştırıcının ön koşulları | Uyarıyla hareket açmak |
| Ayar ($10/$481) okumamak | Yeni sorgu ve yazma yok; push kanıtı zaten fail-closed | `$10` bitlerine göre kapı (ek karmaşıklık) |
