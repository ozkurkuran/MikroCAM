# Implementation Plan: FluidNC seri (USB) desteği (044)

Branch: `044-fluidnc-serial` | 2026-10-04 | [spec](spec.md) | [research](research.md)
Base: `origin/042-firmware-identification` (PR #44, D1). Bu PR #44'ten **sonra** birleştirilir.

## Summary

D1 yetenek kaydında FluidNC 3.x/4.x profili hareketi açar. FluidNC'nin farklı olduğu yerlerde
kanıt FluidNC'nin kendi salt okunur biçimlerinden türetilir: başlangıç blokları yerine üç YAML
makrosu ve `$RI` (yeni `StartupEvidence`, manuel/iş/probe ortak), `$$` vekil ayarları (`$13/$30/$32`),
v4 vektör TLO. Reset tespiti karşılama metnine güvenmez: ESP32 ROM/FluidNC boot satırları ve
tanınmış FluidNC oturumunda serbest metin yeniden başlama sayılır; kart hazır olunca (2 s sessizlik +
`Starting` olmayan durum) `$I`+`$$` yeniden okunur. Konsola salt okunur `$CD` eklenir. FakeGRBL iki
FluidNC profili ve boot simülasyonu kazanır. GRBL 1.1 baytları değişmez.

## Technical Context

CPython 3.13; yeni bağımlılık yok; PyQt6 yalnız UI. Gerçek seri port açılmaz; taşıma ve DTR/RTS
değişmez. Ek bellek yok (makro değerleri ≤512 bayt satırlar). Zamanlama: yeniden başlama sessizlik
süresi 2 s (`fluidnc.RESTART_QUIET_SECONDS`), diğer zaman aşımları mevcut değerler.

## Constitution Check

1. **Evet.** Mantık `mikrocam/machine/` içinde: yeni `fluidnc.py` (saf), `startup_evidence.py`,
   `fake_fluidnc.py`; mevcut `controller/firmware/firmware_control/manual_control/job_control/
   probe_control/console_control/manual_protocol/fake/fake_firmware` küçük bağlantılar. `machine`
   yalnız `core` ve stdlib import eder. UI değişikliği tek satır (`console_controls.py` liste).
2. **Evet.** Legacy değişikliği 0 satır.
3. **Evet.** Yeni soyut sınıf/Protocol/registry yok. `StartupEvidence` somut sınıftır ve üç somut
   kullanımı vardır (manuel, iş, probe); aile dallanması iki somut aile (GRBL `$N`, FluidNC makro).
   Ayrı controller sınıfı yok (yol haritası notu). Yeni bağımlılık yok.
4. **Evet.** Yetenek kaydı tek kaynak (hareket kapısı, bütçe); birim yalnız `$13`'ten; kalıcı format yok.
5. **Evet.** Saf, controller, hata matrisi (C1 altı paketinin FluidNC ile yeniden toplanması), altın
   iz yolculukları ve H2 koruma testleri uygulamadan önce yazıldı; RED `validation.md`'de.
   Testler donanımsız, Qt'siz (konsol UI testi offscreen).
6. **Evet.** Tehlike analizi spec'te; durum makinesi değişmedi, kimlik fazına `restarting` bekleme
   durumu eklendi; stop/abort/cancel/disconnect yolları FluidNC profilinde testli; `0x87`–`0x8A`
   doğrulayıcı testli.
7. **Evet.** FluidNC (GPLv3) kodu kopyalanmadı; kaynak yalnız biçim kanıtı, commit+satır ile
   research'te. `THIRD_PARTY_CHANGES.md` kaydı gerekmez.
8. **Evet.** 3 user story, 30 görev.

## Project Structure

```text
mikrocam/machine/fluidnc.py           # saf: boot/serbest metin, makro+$RI kanıtı, $$ vekil doğrulaması, sürüm kapısı
mikrocam/machine/startup_evidence.py  # StartupEvidence: GRBL $N | FluidNC makro×3 + $RI (manuel/iş/probe)
mikrocam/machine/fake_fluidnc.py      # FakeGRBL FluidNC davranışı + boot simülasyonu
mikrocam/machine/firmware.py          # _PROFILES[FLUIDNC] hareket açık; _fluidnc sürüm kapısı
mikrocam/machine/firmware_control.py  # restarting / chatter / settled
mikrocam/machine/controller.py        # boot işareti, serbest metin, _restart, hazır olunca $I+$$
mikrocam/machine/{manual,job,probe}_control.py  # startup adımı StartupEvidence; iş $$ FluidNC doğrulaması
mikrocam/machine/console_{models,control}.py    # $CD (yalnız FluidNC), FluidNC'de $N reddi, $130 hotfix
mikrocam/machine/manual_protocol.py   # izin listesine 5 salt okunur FluidNC sorgusu; v4 TLO vektörü
mikrocam/machine/fake.py, fake_firmware.py      # fluidnc (v4.1.1) / fluidnc3 (v3.9.9) profilleri
mikrocam/ui/console_controls.py       # konsol listesine $CD
tests/test_fluidnc_protocol.py, test_fluidnc_controller.py, test_fluidnc_fault_matrix.py,
tests/test_fluidnc_wire_journeys.py, test_hardware_readonly_guard.py (+FluidNC), hardware/test_readonly_grbl.py
```

## D2 (grblHAL, spec 043) ile çakışma riski

Paylaşılan dosyalarda düzenlemeler FluidNC girdilerine sınırlı tutuldu:
`firmware.py` (`_PROFILES[FLUIDNC]`, `_fluidnc()`, bir import), `fake_firmware.py` (`fluidnc`
girdisi, yeni `fluidnc3`, `FLUIDNC_VERSIONS`), `fake.py` (3 kanca), `controller.py` (`_consume`
dalları, `_restart`, `_consume_status` sonu, poll zaman aşımı satırı), `firmware_control.py` (yeni
metotlar), `manual_protocol.py` (izin listesi, TLO), `test_firmware_controller.py` (fluidnc
parametresi), `test_firmware_identification.py` (bir assert). D2 aynı satırlara dokunursa birleştirme
elle yapılır; davranışlar bağımsızdır.

## Sequence

spec/research/plan/tasks → RED testler (saf, controller, matris, yolculuk, H2 koruma) → saf modül →
StartupEvidence + sahipler → konsol → firmware profili/kapı → yeniden başlama → FakeGRBL FluidNC →
H2 envanter → belgeler (MACHINE_CONTROL, GRBL_VALIDATION H044, FAULT_MATRIX, STREAMING, CONSOLE) →
odaklı + mimari + pip check + tam paket + masaüstü smoke → commit/push/PR → son-head Windows CI.

## Complexity Tracking

| İhlal | Neden gerekli | Reddedilen basit alternatif |
| --- | --- | --- |
| Yok | — | — |

Not: D1'in iki testi (`fluidnc` hareket kapalı beklentisi) D3'ün açık sonucu olarak güncellendi;
D1 GRBL altın izleri değişmeden geçer. Konsol `$130` düzeltmesi davranışı daraltmaz; yalnız
`$13` önekli başka ayar satırlarının yanlış birim kanıtı sayılmasını önler.
