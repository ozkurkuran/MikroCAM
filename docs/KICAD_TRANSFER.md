# KiCad → MikroCAM üretim aktarımı

Amaç: kart tasarımından üretim verilerini tek işlemle MikroCAM’e taşımak. CAM ve makine çalıştırma ayrıca yapılır.

## MikroCAM’den kullanma
Dosya → İçe aktar → **KiCad board or transfer…** ile `.kicad_pcb` veya `.mcam-transfer` seçin. Kurulu KiCad10.0.x komut satırı aracı PATH’ten veya Windows standart kurulumundan bulunur. Bakır ön/arka, Edge.Cuts ve ayrı PTH/NPTH dosyaları aynı mutlak koordinatlarla üretilir; ayna/öteleme uygulanmaz. Boş dosyalar kaydedilip atlanır. Dolu kart çevresi ve bakır gerekir.

DRC raporu her aktarımda çalışır. Temiz paket doğrudan mevcut projeye eklenir; mevcut nesneler silinmez. Hata/açık bağlantı varsa **View DRC report** üzerinden raporu inceleyin; CAM incelemesi için devam etmek isterseniz işaret kutusunu seçip **Import reviewed** kullanın. Bu işlem kartın üretime uygun olduğunu ilan etmez. İlk parser hatasında kalan dosyalar bekler, başarılı nesneler korunur.

Nesneler kaynak dosyasını ve format/katman raporunu; kart hash’i, KiCad sürümü, DRC sayıları/hash’i ve paket dosya envanterini proje içinde korur. Tam DRC raporu aktarım paketindedir.

## Komut satırı
```powershell
.\.venv\repro-a\Scripts\python.exe -m mikrocam.kicad kart.kicad_pcb --output kart.mcam-transfer
```
İsteğe bağlı `--kicad-cli "C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"` ile executable seçilir. Komut kart ve proje kopyasında çalışır; zone doldurma orijinal tasarımı değiştirmez. Paket yalnızca bütün komutlar ve bütünlük doğrulaması başarılı olursa atomik yazılır.

Paket şema1’dir: manifest.json, drc.json ve files/ altındaki hash doğrulamalı üretim dosyaları. 64 dosya, 16MiB/dosya ve 64MiB toplam sınırı vardır. Gelecek şema, traversal, symlink, çift/eksik/fazla üye ve değişmiş içerik reddedilir. Ağ veya makine bağlantısı kurulmaz.

## KiCad araç çubuğu
MikroCAM Bridge IPC eklentisi aynı aktarım hattını çağırır. `python -m mikrocam.kicad.install_plugin` ile kurulur; PCB Editor yeniden açıldığında MikroCAM µ düğmesindeki **Send to MikroCAM** eylemi canlı kartı özel kopyaya alıp gönderir. Orijinal tasarım ve açık belge korunur. [Kurulum ayrıntısı](../integrations/kicad/README.md). Kurulum/IPC/masaüstü kanıtı merkezi IS_TAKIP.md içinde ayrı kaydedilir.

Birincil API/CLI kaynakları: https://docs.kicad.org/10.0/en/cli/cli.html ve https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/ . KiCad10 IPC, açık belge kopyasını sağlar; export için resmi CLI kullanılır. KiCad uygulamanın zorunlu runtime bağımlılığı değildir.
