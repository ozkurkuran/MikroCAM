# Research: Firmware tanıma (042)

Bütün biçimler birincil kaynaklardan (resmî wiki ve kaynak kod) 04.10.2026'da okundu. Kaynak kod
yalnız davranış/biçim kanıtı olarak incelendi; MikroCAM'e kod kopyalanmadı (anayasa VII). Satır
numaraları aşağıdaki sabit commit'lere aittir.

## Kaynaklar

| Kısa ad | Kaynak | Sabit sürüm |
| --- | --- | --- |
| GRBL-SRC | https://github.com/gnea/grbl (`grbl/report.c`, `grbl.h`, `config.h`, `serial.h`, `planner.h`) | `bfb67f0c7963fe3ce4aaf8a97f9009ea5a8db36e` (master) |
| GRBL-WIKI | https://github.com/gnea/grbl/wiki/Grbl-v1.1-Interface ("Welcome Message", "`[VER:]` and `[OPT:]`") | wiki, 04.10.2026 |
| HAL-SRC | https://github.com/grblHAL/core (`report.c`, `grbl.h`, `config.h`, `system.c`) | `c3a887e3e366f91e26813bb6072479d719cac83a` (master, `GRBL_BUILD 20261004`) |
| HAL-WIKI | https://github.com/grblHAL/core/wiki/Report-extensions ("`$I` response", "`$I+`", NEWOPT, FIRMWARE, `Tool`, `0x87`) | wiki, 04.10.2026 |
| FNC-SRC | https://github.com/bdring/FluidNC (`FluidNC/src/Report.cpp`, `SettingsDefinitions.cpp`, `Logging.cpp`, `RealtimeCmd.h`, `git-version.py`) | `9b8236fa481ba36469389ca27997ba90136e1897` (main, v4.1.1 sonrası) |
| FNC-TAG | Aynı repo, etiketler `v3.4.0`, `v3.7.8`, `v4.1.1` (`FluidNC/src/Report.cpp`) | etiketler |

`wiki.fluidnc.com` bu ortamdan erişilemedi (TCP bağlantı hatası); FluidNC biçimleri bu nedenle
yalnız kaynak koddan ve etiketlerden doğrulandı.

## R1 — GRBL 1.1 (gnea)

- Karşılama: `report_init_message()` → `"\r\nGrbl " GRBL_VERSION " ['$' for help]\r\n"`
  (GRBL-SRC `report.c:170-173`). `GRBL_VERSION "1.1h"`, `GRBL_VERSION_BUILD "20190830"`
  (`grbl.h:25-26`). Wiki: “`Grbl X.Xx ['$' for help]` … always prints upon startup and after a reset”.
  Yani gerçek 1.1h örneği `Grbl 1.1h ['$' for help]`'dir (görev metnindeki `20190825` değil
  `20190830`).
- `$I`: `[VER:` `GRBL_VERSION "." GRBL_VERSION_BUILD ":" <EEPROM build bilgisi> `]`, ardından
  `[OPT:<harfler>,<BLOCK_BUFFER_SIZE-1>,<RX_BUFFER_SIZE>]` (`report.c:369-447`). İki sayı
  `print_uint8_base10` ile basılır, yani ≤255; OPT tam üç alanlıdır. Harf kümesi:
  `V N M C P Z H T A D 0 S R L + * $ # I E W 2` (`report.c:376-441`). Wiki örnekleri:
  `[VER:1.1d.20161014:]`, `[OPT:,15,128]`, `[VER:1.1d.20161014:Some string]`, `[OPT:VL,15,128]`,
  ardından `ok`.
- Varsayılan RX 128 (`serial.h:26-27`), planner 16 (satır numarası açıkken 15) → tipik `V,15,128`.
- Gerçek zamanlı komutlar (`config.h:51-83`): `0x18` reset, `?`, `~`, `!`, `0x84` güvenlik kapısı,
  `0x85` jog iptal, `0x86` yalnız DEBUG, `0x90-0x97`, `0x99-0x9E`, `0xA0`, `0xA1` override'lar.
- Durumlar (`report.c:477-506`): `Idle, Run, Hold:N, Jog, Home, Alarm, Check, Door:N, Sleep`.
- Bulgu: C3 `verified_capacity` OPT harf düzeni `+` ve `0` harflerini kabul etmez; bu durumda
  karakter sayımı güvenli tarafta reddedilir. D1 bu düzenin üstüne bir oturum kapısı ekler,
  C3 düzenini değiştirmez (GRBL baytlarını korumak için). Ayrı hotfix önerisi olarak raporlandı.

## R2 — grblHAL

- Karşılama (HAL-SRC `report.c:307-316`): `COMPATIBILITY_LEVEL == 0` iken
  `GrblHAL 1.1f ['$' or '$HELP' for help]`, aksi hâlde `Grbl 1.1f ['$' for help]`. `GRBL_VERSION`
  her iki dalda `"1.1f"`, `GRBL_BUILD` tarih sayısıdır (`grbl.h:39-45`). Varsayılan uyumluluk
  seviyesi 0 (`config.h:82-98`): 1 “Grbl” olarak raporlar.
- `$I` (`report_build_info`, `report.c:905-1175`; `system.c:629-655`): `[VER:1.1f.<build>:<bilgi>]`,
  `[OPT:<harfler>,<planner>,<rx>{,<eksen>,<takım>}]`. Seviye 0'da `extended` her zaman açıktır;
  ek satırlar `[AXS:n:XYZ]`, `[NEWOPT:ENUMS,RT±,…]`, `[FIRMWARE:grblHAL]`, `[SIGNALS:…]`,
  isteğe bağlı `[NVS STORAGE:…]`, `[FREE MEMORY:…K]`, `[DRIVER:…]`, `[DRIVER VERSION:…]`,
  `[DRIVER OPTIONS:…]`, `[BOARD:…]`, `[MAX STEP RATE:… Hz]`, `[COMPATIBILITY LEVEL:n]` (yalnız >0),
  `[AUX IO:…]`, `[PLUGIN:…]`. Seviye >0'da düz `$I` uzatılmamış (üç alanlı OPT) cevap verir; uzatılmış
  çıktı `$I+` iledir (`system.c:1023,1029`). HAL-WIKI aynı biçimi belgeler.
- Sonuç: uyumluluk seviyesi ≥1 olan grblHAL düz `$I` ile GRBL 1.1f'e çok benzer; RX genellikle
  1024'tür. gnea GRBL uint8 sınırı nedeniyle RX>255 GRBL değildir → Bilinmeyen (UA-4). D1 `$I+`
  göndermez; D2 isterse ayrı spec ile ekler.
- Durumlar (`report.c:1259-1313`): GRBL kümesine ek `Tool`; `Run:1/2`, `Alarm:N` alt kodları.
- Gerçek zamanlı (`grbl.h:103-147`): GRBL kümesi + `0x87` tam durum, `0x88/0x89` toggle, `0x8B`
  MPG, `0x8C` otomatik rapor, `0x98`, `0x9F` yazılım E-stop, `0xA2-0xA4`, `0x80-0x83` üst bitli
  eşdeğerler, `0x19` stop.

## R3 — FluidNC

- Varsayılan karşılama ayarı `$Start/Message` = `Grbl \V [FluidNC \B (\X) \H]` (FNC-SRC
  `SettingsDefinitions.cpp:107-108`; `\V` protokol sürümü, `\B` git bilgisi, `\X` MCU-VARIANT, `\H`
  `'$' for help`; `Report.cpp:136-175`). Örnek: `Grbl 4.1 [FluidNC v4.1.1 (esp32-wifi) '$' for help]`.
  v3.4.0'da sabit: `Grbl 3.4 [FluidNC v3.4.0 (wifi) '$' for help]` (FNC-TAG `v3.4.0 Report.cpp:177-191`).
  Ayar en fazla 40 karakterlik kullanıcı metnidir; karşılama bu yüzden kimlik kanıtı olamaz.
- `grbl_version`, etiketten `v` ve son bileşen atılarak üretilir (`git-version.py`: `v3.7.8` → `3.7`);
  `git_info` = etiket + isteğe bağlı ` (dal-commit[-dirty])`.
- `$I`: v3.x `[VER:3.7 FluidNC v3.7.8:<bilgi>]` (FNC-TAG `v3.7.8 Report.cpp:384`, `v3.4.0:382`);
  v4.x `[VER:4.1 FluidNC v4.1.1 (<MCU>-<VARIANT>) :<bilgi>]` (FNC-SRC `Report.cpp:366`).
  `[OPT:` yalnız harf içerir (`M`,`PH`,`A`,`B`,`S`,`R`,`E`,`W`), **tampon sayıları yoktur**
  (`Report.cpp:368-396`); v4'te `[CLUSTER:16]` ve `[MSG: Machine: <ad>]` izler. `[`-ile başlayan
  log satırlarına `]` eklenir (`Logging.cpp:35-36`).
- Durumlar (`Report.cpp:425-460`): GRBL kümesi, `Hold:0/1`, `Door:0-3`, ek `Starting`; `Alarm` alt
  kodsuz. Gerçek zamanlı (`RealtimeCmd.h`): GRBL çekirdeği + `0x87-0x8A` **Macro0-3**. grblHAL'de
  `0x87` tam durum raporudur: aynı byte farklı ve FluidNC'de hareket başlatabilecek anlamdadır.

## Kararlar

| Karar | Gerekçe | Reddedilen alternatif |
| --- | --- | --- |
| `$I` yetkili kanıt, karşılama yalnız çelişki/reset | FluidNC karşılaması ayarlanabilir; grblHAL uyumluluk modunda `Grbl` der | Karşılamadan sınıflama (FluidNC'yi GRBL sanar) |
| Kimlik `$$`'tan önce, tek ek bayt dizisi | Ayar/durum yorumunun aileye bağlanabilmesi; ACK sırası basit | `$I`'yı iş/hareket hazırlığına gömmek (hareket akışı baytlarını değiştirir) |
| Tek controller + aile profili tablosu | Yol haritası notu ve anayasa III; üç somut aile | Aile başına controller sınıfı |
| grblHAL/FluidNC D1'de hareketsiz | Durum/alarm/`$$` farkları doğrulanmadı | Hemen GRBL gibi hareket açmak |
| C3 bütçesi `min(rx,128)` ve yalnız GRBL | C3 davranışı korunur; diğer ailelerin RX'i doğrulanmadı | grblHAL 1024'ü doğrudan kullanmak |
| `[MSG:` kanıta girmez | GRBL açılış kilidi mesajı ve FluidNC bilgi satırları kimliği bozmamalı | Tüm köşeli satırları toplamak |

## D2/D3 devir notları

- grblHAL: `Tool` durumu, `Run:n`/`Alarm:n` alt kodları, `0x87`, `RT±` anlamı, RX 1024 bütçesi,
  uyumluluk modu tanıma (`$I+` veya `[COMPATIBILITY LEVEL:]`), `[MSG:` ve ek alarm kodları.
- FluidNC: `Starting` durumu, `$Start/Message` ile değişen karşılama (reset tespiti), `[MSG:INFO:`
  satırları, OPT'de RX olmaması (bütçe kanıtı yok), `0x87-0x8A` makro baytlarının asla gönderilmemesi.
