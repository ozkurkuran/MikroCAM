# Data model: Firmware tanıma (042)

Hepsi `mikrocam/machine/firmware.py` içinde, Qt ve legacy import'u olmadan tanımlıdır. Kalıcı
format yoktur; şema sürümü gerekmez.

## FirmwareFamily (Enum)

`GRBL='grbl'`, `GRBLHAL='grblhal'`, `FLUIDNC='fluidnc'`, `UNKNOWN='unknown'`.

## IdentificationPhase (Enum)

`NONE` (bağlı değil/oturum sıfırlandı), `PENDING` (`$I` gönderildi, `ok` bekleniyor),
`IDENTIFIED` (aile tanındı), `FAILED` (kanıt yok/çelişkili/hata/zaman aşımı → aile UNKNOWN).

## FirmwareCapabilities (frozen dataclass) — yetenek kaydı

| Alan | Tip | Anlam |
| --- | --- | --- |
| `family` | `FirmwareFamily` | Tanınan aile |
| `version` | `str` | Firmware sürümü: `1.1h`, `1.1f`, `4.1.1`; bilinmeyende görülen sürüm belirteci olabilir |
| `build` | `str` | `YYYYMMDD` (GRBL/grblHAL) veya boş |
| `protocol` | `str` | Grbl protokol belirteci: GRBL/grblHAL `1.1x`, FluidNC `4.1` |
| `build_info` | `str` | VER içindeki ilk `:`'dan sonraki kullanıcı/OEM metni |
| `options` | `str` | OPT harfleri |
| `extended_options` | `tuple[str, ...]` | grblHAL NEWOPT öğeleri |
| `planner_blocks` | `int \| None` | Bildirilen planner blok sayısı |
| `rx_buffer_bytes` | `int \| None` | Bildirilen RX tamponu (kanıtlanmış bütçe değildir) |
| `streaming_rx_budget` | `int \| None` | C3 karakter sayımı için kanıtlanmış bütçe; `None` → mod reddedilir |
| `extra_states` | `tuple[str, ...]` | GRBL 1.1 dışındaki durum sözcükleri (grblHAL `Tool`, FluidNC `Starting`) |
| `realtime_commands` | `tuple[tuple[int, str], ...]` | Ailenin belgelediği tek bayt komutlar ve adları |
| `status_fields` | `tuple[str, ...]` | Ailenin belgelediği durum raporu alanları |
| `motion_supported` | `bool` | Profil hareket için doğrulandı mı |
| `note` | `str` (≤256) | Hareket kapalıysa veya kimlik bilinmiyorsa gerekçe |

Doğrulama: tipler tam, sayılar `1..65535`, metinler ≤256 karakter yazdırılabilir ASCII, bütçe
yalnız `rx_buffer_bytes` varsa ve ondan büyük değilse, `motion_supported` yalnız GRBL/GRBLHAL/FLUIDNC
için. `capabilities_for(family)` statik aile profilini verir (D2/D3 tek değişim noktası).

## FirmwareObservation (frozen dataclass) — snapshot alanı

`phase`, `capabilities`, `banner` (son reset karşılaması, ≤256), `evidence` (kimliği oluşturan
köşeli `$I` satırları, ≤32), `diagnostic` (≤256). Özellik `motion_allowed` =
`phase is IDENTIFIED and capabilities.motion_supported`.

## Saf fonksiyonlar

- `is_reset_banner(line) -> bool`: `Grbl ` veya `GrblHAL ` öneki.
- `parse_banner(line) -> tuple[str, str] | None`: (`Grbl`/`GrblHAL`, sürüm belirteci).
- `identify(banner, lines) -> FirmwareCapabilities`: sınıflandırma ([research](research.md) kuralları).
- `banner_consistent(capabilities, banner) -> bool`: reset sonrası yeniden tanıma kararı.

## FirmwareIdentification (`mikrocam/machine/firmware_control.py`)

Controller'ın sahip olduğu tek sorgu koordinatörü (Console/Job desenindeki gibi somut sınıf).
`start()` `$I\n` yazar; `consume(line)` köşeli satırları ve terminal `ok`/`error:` tüketir;
`expire(now)` zaman aşımını işler; `on_banner(line)` yeniden tanıma gerekip gerekmediğini döndürür.

## Mevcut modellere eklenenler

- `MachineSnapshot.firmware: FirmwareObservation = FirmwareObservation()`.
- `FakeGRBL(firmware='grbl'|'grblhal'|'fluidnc'|'unknown')`; `banner` ve `build_reply` öznitelikleri
  profil baytlarını taşır, testler değiştirebilir. Varsayılan `grbl` profilinin baytları mevcut
  FakeGRBL ile aynıdır.
