# Research: FluidNC seri (USB) desteği (044)

Bütün FluidNC biçimleri 04.10.2026'da birincil kaynaktan, bdring/FluidNC deposunun iki sabit
etiketinden okundu. `wiki.fluidnc.com` kullanılmadı; kaynak kod tek doğruluk kaynağıdır. Kod yalnız
davranış/biçim kanıtı olarak incelendi; MikroCAM'e FluidNC kodu (GPLv3) **kopyalanmadı** (anayasa
VII). `THIRD_PARTY_CHANGES.md` kaydı gerekmez.

## Kaynaklar

| Kısa ad | Kaynak | Sabit sürüm |
| --- | --- | --- |
| V3 | https://github.com/bdring/FluidNC etiket `v3.9.9` | `3fd629d3089def7d486b2892f1c379bc6764b38b` (03.10.2025) |
| V4 | Aynı depo etiket `v4.1.1` | `fdc17a2c9c0367b07345c16da3937ff0739d4702` (23.09.2026) |
| D1 | `specs/042-firmware-identification/research.md` R3 | `9b8236fa` (main) + `v3.4.0/v3.7.8/v4.1.1` |

Aşağıda `V3 Report.cpp:149` = `FluidNC/src/Report.cpp` satır 149 (etiket v3.9.9). İki sürümde
aynı olan davranışlar için iki satır da verilir.

## R1 — Karşılama, özel mesaj ve yumuşak reset

- Karşılama `report_init_message()` ile `$Start/Message` şablonundan üretilir; önce boş bir satır
  basılır, sonra şablon (`\V` protokol, `\B` git bilgisi, `\X`/`\R` MCU/radyo, `\H` `'$' for help`)
  açılır (V4 `Report.cpp:137-187`, V3 `Report.cpp:149-196`). Varsayılan şablon V4
  `Grbl \V [FluidNC \B (\X) \H]` (V4 `SettingsDefinitions.cpp:108`), V3 `Grbl \V [FluidNC \B (\R) \H]`
  (V3 `SettingsDefinitions.cpp:93`); ayar en fazla 40 karakterlik **kullanıcı metnidir** ve boş
  olabilir. Sonuç: karşılama metnine reset kanıtı olarak güvenilemez (D1 UA-8 devri).
- `0x18` → `protocol_do_soft_restart()`: sistem/planner sıfırlanır, **`allChannels.flushRx()`** ile
  henüz işlenmemiş bütün giriş satırları atılır, sonra karşılama basılır; Idle'da `after_reset`
  makrosu çalışır (V4 `Protocol.cpp:654-705`, flushRx `:684`, karşılama `:685`, makro `:703`;
  V3 `Protocol.cpp:401-446`, `:424`, `:425`, `:443`). Karşılamadan önce gönderilen her komut kaybolur
  ve ACK almaz.
- Boot: `protocol_do_start()` aynı yumuşak reset olayını gönderir; homing yapılandırılmışsa
  `ALARM:14` (Unhomed), değilse Idle; ardından `startup_line0/1` çalışır (V4 `Protocol.cpp:707-731`,
  V3 `Protocol.cpp:448-467`).

## R2 — ESP32 boot ve DTR/RTS

- FluidNC deposundaki gerçek boot yakalaması ESP32 ROM satırlarını gösterir: `ets Jul 29 2019 …`,
  `rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)`, `configsip:`, `clk_drv:`, `mode:DIO`,
  `load:`, `entry 0x…`, ardından `[MSG:…]` boot logları ve karşılama (V3/V4
  `FluidNC/src/tests/parser-result.txt:1-36`). S2/S3/C3 ROM'u `ESP-ROM:` ile başlar (Espressif ROM
  biçimi; depoda örnek yok, uygulama varsayımı).
- `setup()` ilk iş olarak durumu `Starting` yapar (V4 `Main.cpp:35`) ve konsolu açtıktan sonra her
  boot'ta `log_info("FluidNC " << git_info << " " << git_url)` basar (V4 `Main.cpp:43,55`;
  V3 `Main.cpp:49`) → `[MSG:INFO: FluidNC v4.1.1 https://github.com/bdring/FluidNC]`. `log_info`
  `$Message/Level` Info altındaysa basılmaz (V4 `Logging.h:80`, V3 `Logging.h:76`).
- `Starting` durumu V4'te durum raporunda görünür (V4 `Report.cpp:457-458`); V3'te yoktur
  (V3 `Report.cpp:438-470`).
- FluidNC kendisi “geleneksel ESP32 RTS/DTR reset davranışını” S3 yerel USB'de taklit eder:
  R1D1→R0D0→R1D0 dizisi yeniden başlatır, R1D0→R0D1 dizisi **indirme moduna** (bootloader) geçirir
  (V4 `esp32/esp32s3/USBCDCChannel.cpp:57-75`). Klasik ESP32 + CP210x/CH340 kartlarında aynı
  otomatik reset devresi vardır. Port açılışında sürücünün DTR/RTS değiştirmesi kartı yeniden
  başlatabilir veya (S3'te) indirme modunda bırakabilir.

## R3 — `$$`: GRBL ayarları yok, vekil (proxy) değerler var

- `$$` = `GrblSettings/List`: önce `$13=<0|1>` (`Report/Inches`) basılır, sonra yalnız `GRBL`
  tipli ve sayısal adı olan ayarlar (V4 `ProcessSettings.cpp:195-208,1078`; V3 `:192-205,907`;
  `$13` V4 `:774-782`, V3 `:717`). V3'te `$$` döngü/hold sırasında reddedilir (V3 `:907`).
- GRBL tipli ayarlar: `$10` (`Report/Status`, V4 `SettingsDefinitions.cpp:101`, V3 `:86`) ve
  yapılandırmadan türetilen salt okunur vekiller: `$20` soft limit, `$21` hard limit, `$22` homing,
  `$23` homing yönleri, `$30` **mevcut iğin** azami devri, `$32` mevcut iğin lazer modu
  (`isRateAdjusted`), `$100-$10n`, `$110…`, `$120…`, `$130…` eksen değerleri
  (V4 `SettingsDefinitions.cpp:125-153`, V3 `:106-128`). **`$31` (asgari devir) yoktur.**
- Liste en yeni oluşturulanı başa koyar (V4 `Settings.cpp:73,78`, V3 `:70,75`), dolayısıyla tipik
  sıra `$13,$20,$21,$22,$23,$30,$32,$100…$132,$10`. Float vekiller `%.3f`, int vekiller tamsayı
  basar (V4 `Settings.h:222`, `Settings.cpp:540`; V3 `Settings.h:229`, `Settings.cpp:543`).
- İğ değişimi yalnız `M6` (tool_change) veya `M61` ile olur (V4 `GCode.cpp:1724-1731,1753-1757`,
  V3 `GCode.cpp:1618,1643`); MikroCAM preflight `M6`/`M61`'i desteklenmeyen kip olarak reddeder
  (`mikrocam/core/gcode_parser.py:11-12,44`), dolayısıyla `$30/$32` iş boyunca aynı iğe aittir.
- Sonuç: iş kabulü `$13`, `$30`, `$32` ile yeniden türetilir; `$31` yerine alt sınır 0 (UA-4).
  `$20/$21/$22` MikroCAM kabulünde zaten kullanılmaz (GRBL'de de yalnız saha kaydıdır).

## R4 — `$N` yok; başlangıç satırları ve reset makroları YAML'dadır

- `$N` komut listesinde yoktur (V4 `ProcessSettings.cpp:1067-1145`). Bilinmeyen anahtar önce YAML
  yolu, sonra ayar adı/numarası, en son **adında anahtar geçen bütün ayarların listesi** olarak
  yorumlanır (V4 `:1150-1270`, kısmi eşleşme `:1255`; V3 `:1069`). `$N` bu yüzden “n” içeren
  ayarları listeleyip `ok` döner; GRBL `$N0=/$N1=` kanıtı **değildir**.
- GRBL `$N0/$N1` karşılığı YAML `macros/startup_line0` ve `macros/startup_line1`: “Legacy Grbl
  feature (formerly $N0) … the first time the firmware enters Idle after boot” (V4
  `Machine/Macros.cpp:37-51`). `macros/after_reset` power-on ve **Ctrl-X sonrası** Idle'da çalışır
  (V4 `Macros.cpp:89-95`, çağrı `Protocol.cpp:703`; V3 `Protocol.cpp:443`). `after_homing`,
  `after_unlock` yalnız `$H`/`$X` sonrası çalışır (V4 `Macros.cpp:81-102`).
- Salt okunur okuma: `$/macros/<ad>` → `$/macros/<ad>=<değer>` ve `ok` (`setting_prefix()` V4
  `Configuration/RuntimeSetting.cpp:32-37`, Macro okuma `:392-401`; V3 `:30-35,314-323`; makrolar
  grubu V3/V4 `Machine/Macros.h:43-51`). `macros` bölümü her zaman vardır (V4
  `Machine/MachineConfig.cpp:247-248`).

## R5 — `$I`, `$#`, `$G`, durum raporu

- `$I`: V4 `[VER:4.1 FluidNC v4.1.1 (<MCU>-<VARIANT>) :<bilgi>]`, `[OPT:<harfler>]` (sayı yok),
  `[CLUSTER:16]`, `[MSG: Machine: <ad>]`, modül satırları `[MSG: …]` (V4 `Report.cpp:363-405`,
  `BTConfig.cpp:150-167`); V3 `[VER:3.9 FluidNC v3.9.9:<bilgi>]`, `[OPT:…]`, `[MSG: Machine: …]`
  (V3 `Report.cpp:379-417`). RX tamponu bildirilmez → karakter sayımı bütçesi yok.
- `$#`: G54…G59, G28, G30, G92 ve TLO (V4 `Report.cpp:202-216`, V3 `:211-238`). **V3 TLO skalerdir**
  `[TLO:z]` (V3 `:212-222`); **V4 TLO eksen vektörüdür** `[TLO:x,y,z…]` çünkü G43.1 her eksen için
  ofset tutar (V4 `GCode.cpp:1895-1903`). `$#` `[PRB:]` satırı içermez. Eksen sayısı kadar değer
  basılır (V4 `Report.cpp:71-96`) → 4+ eksenli makinede üç değerli ayrıştırıcı reddeder (UA-9).
- `$G`: `[GC:<hareket> G54 G17 G21 G90 G94 <M0/1/2/30> M3/M4/M5 M7/M8/M9 T F S]`; park override
  etkinse `M56` eklenir (V4 `Report.cpp:219-359`, M56 `:352`; V3 `:240-375`, `:368`).
- Durum: `<durum|MPos|WPos:…|Bf|Ln|FS:f,s|Pn|WCO|Ov|A:…|SD…>`; `FS` her raporda, WCO/Ov sayaçla
  (V4 `Report.cpp:499-617`, FS `:536`, WCO `:560`, A `:583`; V3 `:507-…`, `:543`, `:566`, `:588`).
  İğ durumu `Unknown` iken `|A:` boş kalabilir. Durum adları `Idle, Run, Hold:0/1, Jog, Home,
  Alarm, Check, Door:0-3, Sleep, Starting` (V4 `Report.cpp:425-462`). FluidNC `Alarm`'a alt kod basmaz.

## R6 — Gerçek zamanlı baytlar ve `0x87`

- `0x18` reset, `?`, `~`, `!`, `0x84` güvenlik kapısı, `0x85` jog iptali GRBL ile aynıdır;
  **`0x87`–`0x8A` Macro0–3** olayıdır (V3/V4 `RealtimeCmd.h:19-29`, işleyici `RealtimeCmd.cpp:87-97`).
  grblHAL'de `0x87` tam durum raporudur; FluidNC'ye gönderilirse kullanıcı makrosu (hareket olabilir)
  çalışır. MikroCAM'de bu baytlar hiçbir doğrulayıcıdan geçemez.
- Jog iptali FluidNC'de G-code hatası sayılmaz: `JogCancelled` (130) `ok`'a çevrilir
  (V4 `GCode.cpp:1658-1659`, `Error.h:80`; V3 `GCode.cpp:1547-1548`, `Error.h:78`).

## R7 — Otomatik rapor ve mesaj satırları

- Otomatik rapor kanal başınadır, varsayılan 0'dır (V4 `Channel.h:92`, V3 `Channel.h:61`) ve `$RI=<ms>`
  ile açılır; açıkken durum raporu yanında modal değişimde `[GC:…]` ve offset değişiminde `[G54:…]`
  satırlarını **istenmeden** gönderir (V4 `Channel.cpp:256-301`, V3 `Channel.cpp:102-140`).
  Bu satırlar MikroCAM sahiplerinin işlem kanıtını bozar.
- `$RI` (değer olmadan) yalnız okur: `[MSG:INFO: <kanal> auto reporting is off]` veya
  `… auto report interval is <n> ms]` + `ok` (V4 `ProcessSettings.cpp:1005-1034,1138`;
  V3 `:851-858,952`). USB konsol kanalı `uart_channel0`'dır (V4 `UartChannel.cpp:10`,
  `Channel.cpp:45-48`, `esp32/esp32/Console.cpp:6`).
- Log biçimi `[MSG:INFO: …]`, `[MSG:WARN: …]`, `[MSG:ERR: …]`, `[MSG:DBG: …]`; `[` ile başlayan her
  satıra `]` eklenir (V4 `Logging.h:77-92`, `Logging.cpp:35-36`). Alarm öncesi `[MSG:INFO: ALARM: …]`
  satırı ve ardından `ALARM:n` gelir (V3 `Protocol.cpp:229-233`).
- `$CD` = `Config/Dump` YAML'ı serbest metin satırları olarak basar (V4 `ProcessSettings.cpp:1074`,
  `Configuration/Generator.h:45-62`; V3 `:903`).

## R8 — Probe, alarm ve hata kodları

- G38.x döngüsü sonunda `[PRB:x,y,z:<0|1>]` bütün kanallara basılır; temas yoksa `ALARM:5`,
  başlangıçta tetikliyse `ALARM:4` (V4 `MotionControl.cpp:355-396`, V3 `:333-346`).
- Alarm kodları 1-18 (ör. 14 Unhomed, 15 Init, 17 GCodeError; V4 `Alarm.h:5-23`); hata kodları
  GRBL'in 1-40'ına ek 60-181 (dosya sistemi, NVS, yapılandırma, ifade; V4 `Error.h:14-98`).
  MikroCAM kodları metne çevirmez; ham `ALARM:n`/`error:n` gösterir (UA-8).

## R9 — RX tamponu

FluidNC `[OPT:]` sayı içermez (R5) ve `Bf:` alanı yalnız `$10` maskesiyle anlık serbest alanı
verir (V4 `Report.cpp:516-518`); kanal kuyruğu satır bazlı düşürme yapar (V4 `Channel.cpp:132-160`).
Karakter sayımı için kanıtlanmış bir sabit bütçe yoktur → D1 `_streaming_budget` FluidNC'ye bütçe
vermez; C3 modu reddedilir.

## Kararlar

| Karar | Gerekçe | Reddedilen alternatif |
| --- | --- | --- |
| FluidNC'de `$N` yerine üç makro + `$RI` okuması | `$N` FluidNC'de anlamsız (R4); `after_reset` `0x18` sonrası çalışır | `$N` göndermek (yanlış kanıt) veya `$CD` YAML'ını ayrıştırmak (kırılgan, büyük) |
| `$RI` her hareket öncesi | Otomatik rapor kanal başına ve oturumdan bağımsız açık kalabilir (R7) | Sessizce tolere etmek (istenmeyen `[GC:` işi ortasında durdurur) |
| `$31` yok → alt sınır 0 | Kaynakta yok (R3); üst sınır ve lazer modu korunur | İşleri tamamen reddetmek (hedefi boşa çıkarır) |
| v4 TLO vektörü X/Y=0 ise Z | Kaynak biçimi (R5); MikroCAM yalnız Z TLO modelini bilir | Vektörü yok saymak |
| Boot işaretleri + FluidNC'de serbest metin = yeniden başlama | Karşılama kullanıcı metni (R1), ROM/boot logları değil (R2) | Karşılama metnine güvenmek (D1 UA-8) |
| Hazır olana kadar bekle (2 s sessizlik + `Starting` olmayan durum) | Boot sırasında ve `flushRx` öncesi giden komutlar kaybolur (R1, R2) | Hemen `$I` göndermek (kaybolur, sahiplik bozulur) |
| DTR/RTS değiştirilmez | GRBL/Arduino davranışını korur; CH340 her iki ailede ortak, VID/PID ayırt edemez | `dtr=False/rts=False` (fiziksel kanıtsız, GRBL'i etkiler) |
| `$CD` yalnız konsolda | Tanı; YAML yapılandırması uygulamada yorumlanmaz | Ayar yazma / YAML düzenleme (kapsam dışı, tehlikeli) |
| Ana sürüm kapısı 3/4 | Biçimler yalnız v3.9.9/v4.1.1'de doğrulandı | Her sürümde hareket |
| Konsol `$$`'de `$130-$132` satırları yok sayılır | `$13` önekini paylaşırlar; GRBL ve FluidNC `$$` ikisinde de var (gerçek GRBL'de de konsol `$$` başarısız olurdu) | Ayrı bir hotfix PR'ı (aynı test-önce düzeltme, FluidNC için zorunlu) |
