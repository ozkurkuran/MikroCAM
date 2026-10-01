# Probe grid ve yükseklik haritası

Machine panelindeki Probe grid penceresi düzenli bir G54 çalışma koordinatı ızgarasını ölçer.
Yazılım FakeGRBL ile doğrulanmıştır; fiziksel probe, kablolama, clamp/stock açıklığı ve acil
durdurma kullanıcı tarafından doğrulanmalıdır. Yazılım kontrolleri fiziksel interlock yerine geçmez.

1. Açıkça seçtiğiniz makineye bağlanın. G54, duruş ve koordinatlar doğrulanana kadar bekleyin.
2. X/Y sınırlarını, her eksendeki nokta sayısını, güvenli çalışma Z ve en düşük probe Z'yi girin.
   Probe/travel feed, zaman aşımı ve makinenin her eksendeki min/max sınırları da zorunludur.
   Tüm uzunluklar mm, feed değerleri mm/dakikadır. Güvenli Z ilk hareketin yukarı olmasını sağlamalıdır.
3. Review grid ile noktaları inceleyin, sonra açıkça Start probing kullanın. Girdi veya canlı
   konum/ofset değişirse yeniden inceleme gerekir. Pencereyi açmak veya harita yüklemek hareket başlatmaz.

Her nokta öncesinde güvenli Z'ye çıkılır, XY hareketi yapılır, aşağı G38.2 ile temas aranır ve
Z geri çekilir. Tek iletişim sahibi temas raporu, komut onayı ve yeni Idle konum raporunu birlikte
doğrular. Aynı anda jog, sıfırlama, iş çalıştırma veya konsol sorgusu kabul edilmez. G54 dışı mod,
sıfır olmayan geçici/takım ofseti, lazer modu ve dolu startup blokları hareketten önce reddedilir.

Stop probing veya Disconnect, devam eden ölçümü durdurur ve doğrulanmış noktaları korur.
Hata, alarm, zaman aşımı veya iletişim kaybında otomatik devam edilmez. Fiziksel duruşun
doğrulanamadığı açıkça gösterilir; yeniden bağlantı yeni bir ölçümü kendiliğinden başlatmaz.
Eksik noktalar sıfır sayılmaz. Son temas alınmış olsa bile son geri çekilme başarısızsa harita
tamamlanmış işaretlenmez.

Tabloda her noktanın G54 X/Y ve ölçülmüş çalışma Z değeri, yükseklik rengi ve min/max Z görünür.
Harita; ızgara, G54 ofseti, ölçüm/simülasyon kaynağı ve complete/incomplete/failed/aborted sonucuyla
şema 1 JSON olarak kaydedilir. Kaydetme atomik, yükleme sınırlı ve makineden bağımsızdır. Tarihsel
harita görüntülenirken değişmemiş canlı durum kayıtları onu değiştirmez.

Sınırlar: eksen başına 2..64 nokta, toplam en fazla 1024 nokta; güvenli Z ile en düşük probe Z
arası en fazla 100 mm; feed 0,01..10000 mm/dakika; zaman aşımı 3..300 s; dosya en fazla 1 MiB.
Bu dilim Z telafisi yapmaz; telafi ve yay segmentasyonu 026 numaralı dilimdedir.
