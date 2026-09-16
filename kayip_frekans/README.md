# KAYIP FREKANS_ — GitHub üzerinde video botu

Bilgisayara kurulum veya ücretli API anahtarı gerekmez. GitHub Actions → **KAYIP FREKANS - Ucretsiz Video Botu** → **Run workflow**. Konu ve hedef süreyi girin. Tam üretim CPU üzerinde uzun sürebilir. Çalışma sonunda `KAYIP-FREKANS-…` çıktısını indirin; çıktılar bir gün saklanır.

Bot: Qwen2.5 7B ile Türkçe cinli hikâye; Piper Fettah ile Türkçe ses; kendi çizdiği ev/koridor/orman illüstrasyonları; kamera hareketi; hafif özgün uğultu; Türkçe altyazı; 1280×720 MP4, kapak ve metadata. Gerçekçi AI görsel/video veya profesyonel oyunculuk kalitesi vaat edilmez. Görseller atmosfer illüstrasyonlarıdır. Altyazılar cümle sesine göre, cümle içinde yaklaşık hizalanır. Hedef süre kelime sayısıyla yönlendirilir; gerçek süre metadata içinde ölçülür. Paylaşmadan önce öykü tutarlılığını ve Türkçesini dinleyip kontrol edin.

Her kod güncellemesi kısa uçtan uca üretim testi çalıştırır. Uzun video manuel başlatılır. Kanalın Shorts botu değiştirilmez. YouTube'a yükleme yapılmaz; bu kanala ait ayrı OAuth yetkilendirmesi gerekir.

Ücretli servis çağrısı yoktur. Yalnızca public depoda standart ücretsiz GitHub runner çalışır; özel depoda iş çalışmaz. GitHub kotaları, kullanım koşulları ve artifact depolama sınırları geçerlidir; sınırsız/sürekli ücretsiz hizmet garantisi yoktur. Bir günlük saklama depolamayı azaltır. Ücretli runner, API veya abonelik açılmaz.

Kaynaklar:
- https://docs.github.com/en/actions/concepts/billing-and-usage
- https://ollama.com/library/qwen2.5
- https://github.com/OHF-Voice/piper1-gpl
- https://huggingface.co/rhasspy/piper-voices/tree/main/tr/tr_TR/fettah/medium

Ses modelinin MODEL_CARD lisansını yayın kullanımı öncesi inceleyin. Model bağımlılıkları üçüncü taraf kaynaklardan GitHub sunucusuna indirilir.
