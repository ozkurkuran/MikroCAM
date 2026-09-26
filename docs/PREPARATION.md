# MikroCAM hazırlık kaydı

Tarih: 2026-09-26.

## Repolar ve değişmez referanslar

| Amaç | Repo / tag | Commit |
| --- | --- | --- |
| 8.994 Python 3.13 altın referansı | [flatcam-8.994-py313](https://github.com/ozkurkuran/flatcam-8.994-py313), `baseline-8.994-py313` | `6ba378bc` |
| İlk, değiştirilmemiş mekatrol fork'u | [MikroCAM](https://github.com/ozkurkuran/MikroCAM), `upstream-evo-baseline` | `d0a86cf4f1ac41a206b20f316d4a29f28a93bbff` |
| Seçilen, değiştirilmemiş Beta_1.0 tabanı | MikroCAM, `upstream-evo-beta1-baseline` | `e046a2a33926003765f83d6402b96fe6c5c3bcf7` |

MikroCAM GitHub'da herkese açık bir `mekatrol/flatcam` fork'udur. Altın referans da herkese
açıktır. Port commit'i `849e4ef2`; anayasa/spec-kit commit'i `6ba378bc`'dir. Anayasanın
geçici HTML yorum bloğu commit öncesinde kaldırılmıştır.

## Upstream karşılaştırması ve seçim

`git ls-remote` ve tam git geçmişi üzerinden 26.09.2026 tarihinde kontrol edildi:

| Kaynak dal | Commit | İlk fork'a göre fark (fork / kaynak) |
| --- | --- | --- |
| mekatrol `main` | `d0a86cf4f1ac41a206b20f316d4a29f28a93bbff` | 0 / 0 |
| Bitbucket `Beta_8.995` | `8464bb6025fb49f684e23fae5d83079213bec2f8` | 0 / 26 |
| Bitbucket `Beta_1.0` | `e046a2a33926003765f83d6402b96fe6c5c3bcf7` | 0 / 61 |
| Bitbucket varsayılan `Beta` | `5117ba499f787dabd1219b4ae8ea693ef0daedcf` | 1137 / 9 |

Bitbucket'ın varsayılan dalı güncel Evo hattı değildir. Kullanıcının son seçimi
**Beta_1.0** olmuştur. `main`, bu dala `git merge --ff-only bitbucket-evo/Beta_1.0`
ile ilerletildi; upstream commit'leri aynen korundu ve bu adımda uygulama kodu değiştirilmedi.
Güncelleme sonrasında `git rev-list --left-right --count HEAD...bitbucket-evo/Beta_1.0`
sonucu `0 0` idi. Kaynak: [Bitbucket](https://bitbucket.org/marius_stanciu/flatcam_beta/src/Beta_1.0/).

Beta_1.0 mevcut updater kodunu ve testlerini içerir. Bu aktarım, MikroCAM için bir updater
geliştirme veya yayınlama işini ilk dilime eklemez. İlk dilim yalnızca çalışma tabanını doğrular.

## Remote'lar

Git remote ayarları klonlara otomatik taşınmadığından yeniden kurulum listesi burada tutulur.

| Remote | URL |
| --- | --- |
| origin | https://github.com/ozkurkuran/MikroCAM.git |
| evo | https://github.com/mekatrol/flatcam.git |
| bitbucket-evo | https://bitbucket.org/marius_stanciu/flatcam_beta.git |
| kpkrisnop | https://github.com/kpkrisnop/flatcam.git |
| neo | https://github.com/ProgLuis/FlatCAM9NeoS2.git |
| dwrobel | https://github.com/dwrobel/flatcam.git |
| legacy8994 | https://github.com/ozkurkuran/flatcam-8.994-py313.git |

Eksik remote için `git remote add <ad> <URL>` kullanılır. FlatCAM-Plus eklenmemiştir.
Neo kaynağı [projenin README'sinden](https://github.com/ProgLuis/FlatCAM9NeoS2) doğrulanmıştır.
kpkrisnop, neo ve dwrobel yalnızca kaynak remote'larıdır; kodları birleştirilmemiştir.

## Taşınan dosyalar

`.specify/`, `.claude/skills/`, MikroCAM `CLAUDE.md` rehberi ve `docs/ROADMAP.md` altın
referanstan aktarıldı. Beta_1.0'ın mevcut `docs/` dosyaları korundu. Kök `CLAUDE.md`
MikroCAM kuralları ve seçilen taban için güncellendi; eski upstream rehberi tag'de korunur.
`.gitignore` ortak skill dosyalarını dahil eder, `.claude/settings.local.json` dosyasını dışlar.
Altın referanstaki kaynak kopyalar tarihsel kaydı korumak için bırakılmıştır.

## Doğrulama

8.994 altın referansının mevcut Python 3.13 sanal ortamında:

- `python -m pip check`: temiz.
- `python -m pytest -q`: 8 geçti; 3 SWIG deprecation uyarısı.
- `python tests/smoke_app.py`: başarılı; Gerber/Excellon yükleme, isolation, G-code,
  proje kaydetme/açma ve render tamamlandı.

Bu sonuçlar Evo için geçerli değildir. Evo'nun temiz kurulumu ve testleri
`001-evo-py313-baseline` diliminin uygulama aşamasında doğrulanacaktır.

## Eksik kaynak belge

Orijinal “MikroCAM Geliştirme ve Repo Birleştirme Yol Haritası” araştırma belgesi çalışma
dizininde ve ilgili yedek/aktarım dizinlerinde bulunamadı. Kullanıcıdan kaynak yolu/bağlantısı
istendi. Geldiğinde `docs/research/mikrocam-yol-haritasi.md` olarak eklenecek; mevcut roadmap
orijinal belgeymiş gibi kopyalanmadı. Bu eksik, açıkça tanımlanmış ilk dilimin spec'ini engellemez.
