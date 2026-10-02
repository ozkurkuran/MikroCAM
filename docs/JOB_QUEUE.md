# GRBL iş kuyruğu

Machine panelindeki **Job queue…** penceresi hazırlanmış CNC işlerini toplar.
Ön kontrol ve hazırlama tamamlandıktan sonra **Add prepared job** ile kaynak,
SHA-256, koordinatlar ve değişmez bloklar kuyruğa alınır. Sonraki hazırlama bu
kaydı değiştirmez. En fazla 32 iş eklenebilir; Start öncesinde sıra değiştirilebilir.

Start için tüm kuyrukta aynı mekanik spindle, bağlama ve takım düzeni açıkça
onaylanır. İlk onaydan sonra işler otomatik ilerler. İşler arasında operatör
müdahalesi gerekiyorsa ayrı kuyruklar kullanın. Bir önceki işin son koordinatı
sonrakinin gözden geçirilmiş başlangıcıyla aynı olmalıdır; otomatik taşıma üretilmez.

Her iş için startup/settings, çıkış kapatma, modal/G54 ve taze başlangıç yeniden
kontrol edilir. Son blok ACK'si bitiş değildir: çıkışların kapalı olduğu, taze Idle
ve son koordinat doğrulanmadan sonraki işe geçilmez. İletişimin tek sahibi aynı
Machine worker'dır; kuyruğun aradaki boşluğu da başka operasyona açılamaz.

Hold/Resume/Stop aynı sahibin öncelikli komutlarıdır. Hata, alarm, reset, port kaybı,
süre aşımı veya Stop kalan işlerin onayını iptal eder. Yeniden bağlantı otomatik
başlatmaz. Sonuçlar saklanır; çalışmış veya başarısız kayıtlar açıkça yeniden Add
edilmeden gönderilmez. Gönderilmemiş işler yeni onay gerektirir.

Fake testleri fiziksel doğrulama değildir. Gerçek GRBL saha protokolü
[GRBL_VALIDATION.md](hardware/GRBL_VALIDATION.md) ve merkezi durum
[IS_TAKIP.md](IS_TAKIP.md) dosyalarındadır. Bu PR main'e henüz birleştirilmemiştir.
