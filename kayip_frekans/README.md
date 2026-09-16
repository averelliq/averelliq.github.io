# KAYIP FREKANS_ — GitHub bulut video botu (V2)

Bilgisayarınıza program kurmanız gerekmez. GitHub Actions → **KAYIP FREKANS - Ucretsiz Video Botu** → **Run workflow** yolundan konuyu, hedef süreyi (5–35 dakika) ve test seçeneğini girin. İlk denemede **test=true** kullanın. Tam üretimden sonra çalışmanın Artifacts bölümünden `KAYIP-FREKANS-…` paketini indirin; çıktı saklama süresi 1 gündür.

## V2'de eklenenler

- Aynı `tr-TR-AhmetNeural` anlatıcı tarafından hikâyeden **önce seslendirilen** sabit giriş: “Merhaba Kayıp Frekans dinleyicileri. Bugünkü hikâyemizin adı: [başlık]. Videoyu beğenip kanalımıza abone olursanız çok sevinirim. Şimdi hikâyemize geçelim.”
- `03:15` → “gece üç on beş”; `22:30` → “gece on buçuk” gibi TTS öncesi saat dönüştürme.
- Çok kısa, tekrarlı, başlıksız veya bitişi eksik metinler için mekanik kontroller. Bunlar insan değerlendirmesinin yerini tutmaz.
- Açılış için kanal isimli başlık kartı ve bodrum, hastane odası, yatak odası anahtar sözcüklerine göre ek **çizim** varyantları.
- Ayrı `intro.txt`, `story_only.txt`, `quality_report.json` dosyaları; gerçek video süresi, tahmini metin süresi ve insan kontrolü uyarısı.
- Kod değişikliklerinde ve PR'larda kısa uçtan uca üretim testi; değişiklikler önce Python birim testlerinden geçer.

## Mevcut yetenekler ve sınırlar

Qwen2.5 7B ile Türkçe kurmaca korku metni, Edge TTS ile seslendirme, CPU üzerinde programatik atmosfer illüstrasyonları, hafif kamera hareketi, uğultu, yaklaşık cümle içi hizalı Türkçe altyazı, 1280×720 MP4 ve kapak üretilir. **Fotogerçekçi AI görsel veya hareketli video üretilmez; GPU/video servisi entegrasyonu henüz yoktur.** Tok, profesyonel oyuncu sesi veya kesintisiz karakter tutarlılığı garanti değildir. Müzik ve olay bazlı ses efektleri henüz tamamlanmış değildir.

Hedef dakika kesin süre değildir: bot metin için tahmini kelime hedefi kullanır, final süreyi ölçer. Çok kısa hikâye videoya geçirilmez. Uzun video GitHub CPU kotası ve süre sınırı nedeniyle başarısız olabilir; 30 dakikalık tam uçtan uca üretim ayrıca doğrulanmalıdır. Son videoyu izleyip Türkçe anlatımı, sabit yüz/mekân tutarlılığını ve altyazıyı **yayınlamadan önce insan olarak kontrol edin**.

**YouTube'a video yüklenmez.** KAYIP FREKANS_ kanalına ait ayrı OAuth ve açık yayın onayı olmadan otomatik yayın açılmayacaktır. Global Shorts botunun dosyaları değiştirilmez.

Ücretli API veya abonelik otomatik etkinleştirilmez. GitHub runner, kota ve artifact sınırları vardır; sınırsız/7×24 ücretsiz hizmet garantisi yoktur. Edge TTS üçüncü taraf çevrimiçi hizmetine metin gönderir; hizmet veya kota değişirse işlem hata verir. Qwen modeli her GitHub runner'a indirilir. Mevcut video botu bu public deponun içinde çalışır; özel depoda workflow içindeki video işi bilinçli olarak atlanır.

Kaynak: https://docs.github.com/en/actions/concepts/billing-and-usage , https://ollama.com/library/qwen2.5 , https://github.com/rany2/edge-tts


## V3 — etkin üretim yolu

Workflow artık `cloud_v3.py` çalıştırır. Önceki V2 kaynakları korunur.

- Yalnızca ücretsiz yerel Qwen modeli kullanılır. Her bölümün kelime sınırı, tamamlanmış son cümlesi, tekrarı ve bilinen hatalı kalıpları denetlenir. Başarısız metin en çok üç kez yeniden yazdırılır. Ayrı editör çağrısı somut sorunları raporlar; bu mekanik/AI kontrol insan okuması yerine geçmez. Uzun metin editörünün kapsamı raporda belirtilir.
- Kanalın mevcut sesli giriş metni korunur. Test artık 180–280 kelimelik hikâye ve giriş içerir; 65–180 saniye dışında kalan test başarılı sayılmaz.
- Tam üretim, hedef sürenin %90–110 aralığında olmalıdır. Örneğin 30 dakika hedefinde 27–33 dakika. Ses uzatılmaz, boşlukla doldurulmaz; sınır dışı içerik hata olarak kaydedilir.
- Ücretsiz Pexels API ile yüksek çözünürlüklü fotoğraflar alınır. Mevcut `PEXELS_API_KEY` deposu secret'ı kullanılır. Fotoğraf açıklamasında konu eşleşmesi aranır; insan portreleri filtrelenir. Uygun fotoğraf yoksa çizim/rasgele fotoğrafla başarı taklidi yapılmaz. Mekân ve nesneler temsili stok görüntülerdir; anlatılan evin birebir rekonstrüksiyonu veya fotogerçekçi AI karakter sürekliliği vaat edilmez.
- 1920×1080, 24 FPS; yaklaşık 12 saniyede bir plan değişimi, yumuşak yakınlaşma/uzaklaşma ve tutarlı koyu renk düzeni. En az beş plan ve üç farklı fotoğraf gereklidir.
- Ahmet sesi artık cümle cümle koparılmadan paragraf olarak üretilir. Altyazı zamanları TTS'nin gerçek kelime sınırlarından gelir. Tek birleştirilmiş WAV kullanımı sahneler boyunca ses/al altyazı kaymasını önler.
- Konuşurken kısılan özgün düşük gerilim tonu vardır. Olay bazlı çığlık/cam kırılması efektleri veya profesyonel müzik üretimi henüz yoktur.
- `visual_sources.json`, `credits.txt`, `scene_plan.json`, `shots.json`, editör raporu ve gerçek süre çıktılara eklenir. Başarısız üretimlerde mevcut metin/raporlar teşhis için saklanır. Teknik geçiş profesyonel içerik onayı anlamına gelmez.
- PR'larda yalnızca testler çalışır; video üretimi main güncellemesi veya manuel başlatma ile olur. Yayın/yükleme otomatik açılmaz.

Pexels API: https://www.pexels.com/api/ ; lisans: https://www.pexels.com/license/ . Ücretli fallback yoktur. Ücretsiz hizmet kotaları ve GitHub depolama sınırları geçerlidir.
