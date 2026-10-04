# Implementation Plan: Firmware tanıma (042)

Branch: `042-firmware-identification` | 2026-10-04 | [spec](spec.md) | [research](research.md) |
[data-model](data-model.md)

## Summary

Bağlantıda `$$\n`'den önce tek salt okunur `$I\n`; köşeli cevap satırları ve `ok` ile saf bir
sınıflandırıcı `FirmwareCapabilities` üretir. Kayıt `MachineSnapshot.firmware` olarak yayımlanır.
Tek hareket uygunluk kapısı (`ManualControl.eligible`) kaydın `motion_allowed` değerine bağlanır;
iş, kuyruk ve probe zaten bu kapıdan geçer. C3 karakter sayımı bütçesi kayıttan alınır. UI ince bir
firmware satırı gösterir. FakeGRBL dört profil kazanır.

## Technical Context

CPython 3.13, mevcut bağımlılıklar (PyQt6 yalnız UI, pytest). Yeni bağımlılık yok. Gerçek seri port
açılmaz. Bellek: kanıt en fazla 32 satır × 256 bayt. Zamanlama: kimlik zaman aşımı 3 s (ayar ile aynı).

## Constitution Check

1. **Evet.** Mantık `mikrocam/machine/firmware.py` ve `firmware_control.py` içinde; yalnız stdlib.
   UI `mikrocam/ui/machine_firmware.py` yalnız metin biçimler. `machine` PyQt6/legacy import etmez.
2. **Evet.** Legacy değişikliği 0 satır (`appMain.py`, `camlib.py`, `appPlugins/` dokunulmaz).
3. **Evet.** Yeni soyut sınıf/Protocol/registry yok. Aile profil tablosu üç somut ailenin (GRBL,
   grblHAL, FluidNC) verisidir; `FirmwareIdentification` somut tek sahip koordinatörüdür (Console/Job
   deseni). Yeni bağımlılık yok.
4. **Evet.** Yetenek kaydı tek kaynak; C3 bütçesi ve hareket kapısı oradan okunur. Kalıcı format yok.
5. **Evet.** Saf sınıflandırma, controller/FakeGRBL, altın wire ve UI testleri uygulamadan önce
   yazılır (RED kaydı validation.md'de). Testler donanımsız; UI testleri offscreen.
6. **Evet.** Tehlike analizi spec'te; durum makinesi `IdentificationPhase`; stop/abort/cancel/
   disconnect yolu kimlikten bağımsız ve testli.
7. **Evet.** Dış kod kopyalanmadı; kaynak kod yalnız biçim kanıtı olarak okundu ve research'te
   commit/satır ile anıldı. `THIRD_PARTY_CHANGES.md` kaydı gerekmez (kod alınmadı).
8. **Evet.** 3 user story, 24 görev.

## Project Structure

```text
mikrocam/machine/firmware.py          # enum + kayıt + gözlem + saf sınıflandırma + aile profilleri
mikrocam/machine/firmware_control.py  # FirmwareIdentification (tek $I sahibi)
mikrocam/machine/fake_firmware.py     # FakeGRBL profil baytları (grbl/grblhal/fluidnc/unknown)
mikrocam/machine/controller.py        # connect/reset/consume/expire bağlantısı
mikrocam/machine/models.py            # MachineSnapshot.firmware
mikrocam/machine/manual_control.py    # tek hareket kapısı
mikrocam/machine/console_control.py   # PENDING iken konsol kapalı
mikrocam/machine/job_control.py       # C3 bütçe kapısı + VER eşleşmesi
mikrocam/machine/fake.py              # profil seçimi
mikrocam/ui/machine_firmware.py       # firmware satırı metni (ince)
mikrocam/ui/machine_panel.py          # form satırı
tests/test_firmware_identification.py, tests/test_firmware_controller.py,
tests/test_firmware_wire_preservation.py (+ firmware_wire_scenarios.py, fixtures/grbl11_wire_golden.json),
tests/test_machine_firmware_ui.py
```

## D2/D3 bağlanma noktaları

- `firmware._PROFILES[FirmwareFamily.GRBLHAL|FLUIDNC]`: `motion_supported`, `extra_states`,
  `realtime_commands`, `status_fields` ve not burada değişir; ayrı controller yazılmaz.
- `firmware._streaming_budget()`: grblHAL RX bütçesi kanıtlanınca burada açılır (C3 otomatik alır).
- `grbl.parse_status`: aileye özgü durumlar için `snapshot().firmware.capabilities.extra_states`
  okunabilir (D1 parser'ı değiştirmez).
- `fake_firmware.PROFILES`: D2/D3 durum/alarm/MSG davranışlarını aynı profil adına ekler.
- `firmware_control.FirmwareIdentification.on_banner`: FluidNC özel karşılama/reset tespiti (UA-8).

## Sequence

spec/research/data-model/plan/tasks → analyze → altın izler (main `70800e5b`) → RED testler →
saf modül → controller/kapılar → FakeGRBL profilleri → C3 kapısı → UI → mevcut testlerin bağlantı
baytı varsayımları → dokümanlar/H1 → ilgili + mimari + tam paket + masaüstü smoke → commit/push/PR →
son-head Windows CI.

## Complexity Tracking

| İhlal | Neden gerekli | Reddedilen basit alternatif |
| --- | --- | --- |
| Yok | — | — |

Not: Mevcut testlerde bağlantı baytlarını sabitleyen 13 civarı assert, eklenen `$I\n` nedeniyle
güncellenir; bu bir davranış gevşetmesi değil, UA-1'in açık sonucudur ve altın izlerle sınırlandırılır.
