# Implementation Plan: grblHAL seri desteği (043)

Branch: `043-grblhal-serial` | 2026-10-04 | [spec](spec.md) | [research](research.md)
Taban: `origin/042-firmware-identification` (`164da247`, PR #44). Birleştirme #44'ten sonra.

## Summary

D1 yetenek kaydındaki grblHAL profili hareketi açar; `_grblhal()` sınıflandırması kartın kendi `$I`
kanıtına göre (eksen=3, AXS `3:XYZ`, `RT+`, `LATHE` yok) hareketi kapatabilir ve C3 bütçesini
`min(rx,128)` yapar. Controller grblHAL tanındığında iki şey yapar: durum raporunu `parse_status(…,
grblhal=True)` ile ayrıştırır ve diğer satırları wire log'dan sonra tek bir lehçe fonksiyonundan
(`grblhal.normalize_query_line`) geçirir; manual/iş/probe/konsol mevcut sıkı GRBL ayrıştırıcılarını
değiştirmeden kullanır. Alarm/hata anlamları aileye göre tabloda tutulur ve panel durum ipucunda
gösterilir. FakeGRBL grblHAL biçimlerini üretir; C1/adversarial testlerinin seçili kümesi grblHAL
varsayılanıyla yeniden koşulur. Ayrı commit: C3 OPT `0`/`+` hotfix'i.

## Technical Context

CPython 3.13, mevcut bağımlılıklar; yeni bağımlılık yok. Gerçek seri port açılmaz. Yeni sorgu veya
yazma komutu yok (GRBL komut kümesi aynı). Bellek/zaman sınırları D1 ile aynı.

## Constitution Check

1. **Evet.** Mantık `mikrocam/machine/` (yalnız stdlib); UI `mikrocam/ui/machine_panel.py` yalnız ipucu
   metni gösterir. `machine` PyQt6/legacy import etmez.
2. **Evet.** Legacy değişikliği 0 satır.
3. **Evet.** Yeni soyut sınıf/Protocol/registry/flag yok. grblHAL farkı: bir profil girdisi, bir
   ayrıştırıcı anahtar sözcüğü ve bir saf lehçe fonksiyonu (somut tek kullanım; soyutlama değil).
   Kod tablosu iki somut ailenin (GRBL, grblHAL) verisidir. Yeni bağımlılık yok.
4. **Evet.** Hareket ve bütçe yalnız yetenek kaydından; birimler mevcut `$13` yolundan. Kalıcı format yok.
5. **Evet.** Saf, controller, Fake ve UI testleri uygulamadan önce (RED validation.md'de). Donanımsız,
   offscreen.
6. **Evet.** Tehlike analizi spec'te; durum makinesi değişmez (D1 `IdentificationPhase` + mevcut
   `MachineState`); stop/abort/cancel/disconnect yolu grblHAL'e karşı fault-matrix koşusuyla test edilir.
7. **Evet.** Dış kod/metin kopyalanmadı; kaynaklar yalnız commit/satır olarak anıldı.
   `THIRD_PARTY_CHANGES.md` kaydı gerekmez.
8. **Evet.** 3 user story, 30 görev.

## Project Structure

```text
mikrocam/machine/job_stream.py        # (hotfix) OPT harfleri 0/+; grblHAL ek OPT alanları
mikrocam/machine/firmware.py          # _PROFILES[GRBLHAL] hareket; _grblhal() kanıt kapısı; bütçe
mikrocam/machine/grblhal.py           # YENİ: normalize_query_line ($G/$#/$$ lehçesi)
mikrocam/machine/firmware_codes.py    # YENİ: alarm/hata anlam tabloları (GRBL 1.1, grblHAL)
mikrocam/machine/grbl.py              # parse_status(grblhal=...)
mikrocam/machine/controller.py        # lehçe kancası + parse_status bayrağı
mikrocam/machine/job_control.py       # iş başı VER+OPT eşleşmesi
mikrocam/machine/fake_firmware.py     # grblHAL durum/$G/$#/$$ biçimleri
mikrocam/machine/fake.py              # profil biçimlerini kullan; varsayılan profil değişkeni
mikrocam/ui/machine_panel.py          # durum ipucunda kod anlamı
tests/test_grblhal_*.py               # yeni testler; tests/hardware/test_readonly_grbl.py genişletme
```

## Shared-file notu (D3 044 paralel)

`firmware._PROFILES`, `_streaming_budget`, `fake_firmware.PROFILES`, `grbl.parse_status` ve
`test_firmware_controller.py` D3 ile ortak. Değişiklikler yalnız grblHAL satırlarıyla sınırlıdır:
`parse_status`'a anahtar sözcüklü bir bayrak, `PROFILES`'a dokunmadan ayrı grblHAL biçim fonksiyonları.

## Sequence

hotfix (test→fix→commit) → spec/research/plan/tasks → RED testleri → firmware profili → parse_status →
lehçe → controller → iş başı OPT → Fake → kod tablosu + UI → mevcut testlerin “grblHAL kapalı”
varsayımları → H2 aracı + belgeler → odaklı + mimari + pip check + tam paket + smoke → commit/push/PR → CI.

## Complexity Tracking

| İhlal | Neden gerekli | Reddedilen basit alternatif |
| --- | --- | --- |
| Yok | — | — |

Not: D1'in “grblHAL hareketi kapalı” varsayan test/smoke/belge satırları bilerek güncellenir
(UA-2'nin D2 tarafından kaldırılması); GRBL 1.1 altın izleri değişmez.
