# LightBurn Image proje uyumluluğu

2026-10-02. **Doğrulanmış native profil yok.** Standart Program Files kurulumları,
çalışan süreç ve Windows uninstall kayıtlarında LightBurn bulunmadı. Kullanıcıdan
sürüm, cihaz türü ve program/örnek `.lbrn2` yerel yolu istendi; yanıt bekleniyor.

| Özellik | check-status | Kanıt / kalan koşul |
| --- | --- | --- |
| Tam boyutlu tamamlayıcı1-bit PNG | PASS | Python piksel/codec/ZIP birleşim testleri;508DPI600×360 |
| MikroCAM JSON/proje kaydı | PASS | Gerçek CAM kaynak silme +save/reopen; hash aynı |
| Native `.lbrn2` yazımı | NOT_RUN | G02 gerçek saved fixture yok; XML alanı tahmin edilmedi |
| Image layer/placement/Pass-Through/scan angle | WAITING | Sürüm/device profili ve gerçek Open→Save→Open→Preview |
| Boş satırın hareketsiz atlanması | WAITING | Görüntü maskesi bunu kanıtlamaz; profile özgü test |
| Kaynak r paritesine göre bidirectional yön | WAITING | Core helper doğru; gerçek hareket LightBurn davranışı |
| R*N katman kapasitesi ve tam tur sırası | WAITING | En az8katman ve2tur native Preview kabulü |
| Geçişler arası native ms bekleme | WAITING | Gerçek laser-off dwell desteği/alanı kanıtlanmalı |
| Fiziksel lazer/makine | NOT_RUN | Bu dosya üretimi işinin kapsamı dışında |

[Kesin sözleşme ve G02 prosedürü](design/visual-interlace/lightburn-contract.md).
Native button doğrulanmış profil yokken kapalıdır. PNG ZIP'te
`native_lightburn_settings_applied=false` yazılır. PNG/JSON başarıları `.lbrn2` teslimi
sayılmaz; toplam ürün hedefi henüz tamamlanmadı.

G02 sonrası küçük özgün fixtures `tests/reference/lightburn/<profile_id>/` altında
version/device/fixture digest, en az8katman, pixel-center/placement, bitmap encoding,
order, blank-row skip ve capability manifest'iyle saklanır. License/token/device
seri numarası test reposuna girmez. File→Open kullanılmalı; Import proje ayarlarının
korunduğunu kanıtlamaz. Gerçek makine başlatma bu kabul prosedürünün parçası değildir.

## 2026-10-03 — saved-project discovery

A read-only search found two original user projects outside the repository. Neither
project was modified or copied into the repository. They establish historical saved-file
metadata only; they do not identify the currently installed version or a supported device.

| Original filename | Saved AppVersion | FormatVersion | Shapes | Image layers | SHA256 |
| --- | --- | --- | --- | --- | --- |
| AutoSave_393c.lbrn2 | 1.7.06 | 1 | 1 Rect | 0 | ef9fed03e853a786ba5cda4359509c721ced8dbca55813f98cd7919e73309dc3 |
| tubitak lazer.lbrn2 | 1.1.03 | 1 | 4 Ellipse | 0 | 99fcab7d8b7b06f39519463708aac4e4e96e016e8b1aa519f53739cd6691ff12 |

Both roots are LightBurnProject with XForm geometry and CutSetting type Cut.
There is no Image shape, embedded bitmap payload, Image CutSetting, or native
round-trip evidence. A Thumbnail is a preview and does not establish an engraving
Image payload. No renderer/export schema was inferred from these vector-only files.

The current executable, device family and a project containing an actual Image layer
remain required for G02. The standard install/process/registry and targeted portable
location/shortcut checks found no executable. C01–C08 and native V4 remain NOT_RUN;
source PNG/JSON success is unchanged.
