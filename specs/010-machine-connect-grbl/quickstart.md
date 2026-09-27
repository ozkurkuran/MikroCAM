# Salt okunur GRBL: geliştirici quickstart

Feature checkout kökünde mevcut sabitlenmiş CPython 3.13 geliştirme ortamını kullanın.
Yeni bağımlılık veya fiziksel seri cihaz gerekmez. `tests/conftest.py` Qt ayarlarını ve
APPDATA'yı geçici alana yönlendirir; seri-adaptör testleri gerçek port açmaz.

## Otomatik testler

PowerShell örneği; ortam yolunu kendi mevcut geliştirme ortamınıza göre değiştirin:

```powershell
$python = 'E:/VSCode/Flatcam/MikroCAM/.venv/repro-a/Scripts/python.exe'
$env:QT_API = 'pyqt6'
$env:QT_QPA_PLATFORM = 'offscreen'
& $python -m pytest tests/test_machine_grbl.py tests/test_machine_controller.py tests/test_machine_fake.py tests/test_machine_serial.py -q
& $python -m pytest tests/test_machine_ui.py tests/test_machine_shutdown.py -q
$machineTests = (Get-ChildItem tests/test_machine_*.py).FullName
& $python -m pytest @machineTests tests/architecture -q
& $python -m pytest -q
```

İlk grup parser/controller/FakeGRBL ve mocked pyserial davranışlarını denetler. Qt grubu
worker sahipliği, GUI thread sınırı, hatalar, gecikmiş snapshot'lar, tekrar açma ve on
bağlanma/kesme döngüsünü kapsar. Açma/okuma/yazma/kapatma hataları görünür olmalı;
kaydedilen TX yalnızca `{b'?', b'$$\n'}` kümesinden gelmelidir. Mimari/growth denetimleri
ve eski CAM testleri de geçmelidir. Sonuçları ve sınırlamaları `validation.md` içine kaydedin;
bu quickstart henüz çalıştırılmamış sonuçları başarı olarak ilan etmez.

## Donanımsız panel enjeksiyonu

UI testleri ve masaüstü smoke gerçek seri factory yerine fake factory **ve** metadata
sağlayıcısı kullanır. `controller_factory(port)` iletişim worker'ında çağrılır; port açma
GUI thread'ında yapılmaz. Paneli oluşturmak bağlantı başlatmaz:

```python
from mikrocam.bridge.serial_transport import PortInfo
from mikrocam.machine.controller import MachineController
from mikrocam.machine.fake import FakeGRBL
from mikrocam.ui.machine_panel import MachinePanel

panel = MachinePanel(
    window,
    controller_factory=lambda _port: MachineController(
        FakeGRBL(status=b'<Idle|MPos:3,4,5|WCO:1,2,3>\n')
    ),
    ports_provider=lambda: (PortInfo('COM17', 'FakeGRBL — fiziksel cihaz değil'),),
)
```

Örnek çalışan QApplication ve QMainWindow olan `window` varsayar; `COM17` burada yalnızca
fake metadata'dır. Testte `panel.connect_machine()` sonrasında GUI event loop'u ile snapshot
bekleyin: makine `(3,4,5)`, iş `(2,2,2)` mm olmalı. Disconnect/close ardından worker gerçekten
bitmeli; eski session snapshot'ı göstergeleri doldurmamalıdır. Kapanışta `panel.shutdown()`
sonucunu denetleyin; canlı QThread'ı yok etmeyin. Deterministik zaman aşımı/reset senaryoları
için fake ve enjekte edilen saatli controller testlerini kullanın.

## Gerçek masaüstü smoke

```powershell
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
& $python tests/smoke_app.py
```

Bu çalışma Windows masaüstü oturumu ister. Machine kapsamı yukarıdaki fake enjeksiyonuyla
çalıştırılmalı; hiçbir gerçek port açılmamalıdır. Gerber/Excellon, isolation/CNC, proje
save/reopen ve mevcut lazer akışları da korunmalıdır. Log/screenshot'ları ignored `.venv`
alanında saklayın; normal listener/worker/pool temizliğini ve Machine worker kapanışını
ayrıca doğrulayın. Menü yolunu gözlemlemek tek başına Machine bağlantı testi değildir.

İleride yapılacak gerçek GRBL 1.1 kontrolünde port açılması donanımsal reset oluşturabilir.
Read-only Disconnect iletişimi kapatır; hareketi veya harici denetimi durdurmaz, E-stop
yerine geçmez. Bu otomatik testler gerçek donanım başarısı iddiası taşımaz.
Operatör açıklaması: [MACHINE_CONTROL.md](../../docs/MACHINE_CONTROL.md).
