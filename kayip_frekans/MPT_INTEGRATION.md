# KAYIP FREKANS_ × MoneyPrinterTurbo (deneysel, güvenli geçiş)

Bu dosyalar eski `cloud_v5.py` botunu silmez veya varsayılan anlatıcıyı değiştirmez. `mpt_bridge.py`, [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) projesinin MIT lisanslı, **633dbb0cf6866e817a023f30c5ac20c6cf3f76de** commit'indeki CLI arayüzünü kullanacak şekilde hazırlanmıştır. Upstream kaynak kodu yalnızca video üretimi açıkça istenirse GitHub runner'ına çekilir; LICENSE dosyası upstream içerisinde korunur.

## Anlatıcı kim olacak?

MoneyPrinterTurbo'ya `--custom-audio-file narration.wav` ve `--voice-name no-voice` verilir: **MoneyPrinterTurbo TTS üretmez; kullanıcı tarafından dinlenip onaylanmış WAV dosyasını kullanır.** Bu adapter kendi başına ses klonlamaz, Serkan'a benzerlik ölçmez ve elinizdeki 44,5 saniyelik referansı otomatik olarak uzun videoya dönüştürmez. Eski Ahmet+OpenVoice çıktısına otomatik geri dönme YOKTUR.

Onay verilmiş ses bulunmadıkça video üretimi durur. Orijinal referans kaydını, özel ses secret'larını veya kilit dosyalarını bu herkese açık repoya eklemeyin. Public GitHub Actions artifact'larının erişim koşullarını dikkate alın: oluşturulan video sesinizi içerebilir. Özel ses kaydı güvenliği önemliyse video üretimini özel depoya taşıyın.

## Girdi artifact'ı

`KAYIP-FREKANS-MPT-INPUT` adlı **önceden oluşturulmuş** GitHub Actions artifact'ı şu dosyaları kök dizininde içermelidir:

```
story.txt                 # Eksiksiz Türkçe hikâye
narration.wav             # Dinleyip ONAYLADIĞINIZ tam anlatım
approval.json             # Sadece onaydan SONRA düzenleyin
scenes.json               # Her sahnesi izlenip onaylanmış görsel planı
assets/scene001.jpg       # Haklarına sahip olduğunuz gerçek görüntüler
assets/scene002.mp4
...
```

`approval.json` örneği (gerçek SHA256'yı onaylanan WAV dosyasından alın):

```json
{
  "approved_by_user": true,
  "voice_label": "Serkan Demirci",
  "audio_sha256": "ONAYLANMIS_NARRATION_WAV_DOSYASININ_SHA256_DEGERI"
}
```

`scenes.json` örneği; başlangıç/bitiş saniyeleri **tüm ses süresini** aralıksız kapsamalıdır:

```json
[
  {"start": 0, "end": 10, "kind": "corridor", "description": "Gece karanlık, boş köy evi koridoru", "asset": "assets/scene001.jpg", "approved_by_user": true},
  {"start": 10, "end": 20, "kind": "room", "description": "Mutfaktaki ahşap dolabın kapağı", "asset": "assets/scene002.mp4", "approved_by_user": true}
]
```

Bu JSON yalnızca yapıyı gösterir; 20 saniyelik örneği gerçek 15–20 dakikalık girdi sanmayın. Görseller asgari 1280×720 olmalı; 3–25 saniyelik sahneler birbirini takip etmeli, aynı dosya içeriği iki defadan fazla kullanılmamalı ve uzun videoda aynı kategori sahnelerin %45'ini geçmemelidir. Her sahne için `approved_by_user: true` yalnızca **gerçekten bakıp onayladıysanız** girilmelidir. Bu kontroller semantik anlamda kusursuz görüntü veya karakter sürekliliğini kanıtlamaz.

**Bugün için önemli eksik:** Bu tam onaylı girdi artifact'ını oluşturan ses/medya üretim hattı henüz mevcut değil. Daha önceki 17:15 sesini yanlış anlatıcı olduğu için bu pakete onaylı olarak koymayın. V6 kısa ses denemesi, onaylanmış uzun ses yerine geçmez.

## Bulut iş akışı

[MoneyPrinterTurbo deneme workflow'u](https://github.com/averelliq/averelliq.github.io/actions/workflows/kayip-frekans-mpt.yml) → `Run workflow` → girdi artifact'ını içeren `source_run_id`, `artifact_name`, `mode` (`preview` = 20–90 saniye veya `full` = 900–1200 saniye). Önce `run_video=false` kullanın: yalnızca ön kontrolleri çalıştırır. Tam ve onaylı paket hazırsa, render için `run_video=true` seçilebilir. Hiçbir adım YouTube'a otomatik yayın yapmaz.

Bağımlılıklar yalnızca GitHub runner'ına kurulur, sizin bilgisayarınıza değil. Upstream indirmesi, paket kurulumu, GitHub Actions kotası, video süresi ve kaynak hizmetleri nedeniyle **sıfır maliyet/sınırsız kullanım veya başarılı 20 dakikalık render garantisi yoktur**. Yerel dosya modu ve hazır ses kullanımı ücretli görsel/TTS API çağrılarını devre dışı bırakır.

## Teknik sınırlar

- Bu bir **gerçek CLI köprüsüdür**, upstream botun bütün dosyalarının fork edilmesi değildir. Yeni iş akışı ancak eksiksiz/onaylı ses ve görsel paketi sunulursa upstream CLI'yi çalıştırır.
- Sıralı yerel görseller MPT'ye verilir; sahne planının **kare hassasiyetinde** anlatımla eşleştiği henüz doğrulanmadı. MP4 mutlaka izlenmelidir.
- Bu ilk deneyde MPT otomatik altyazısı kasıtlı olarak kapalıdır: yanlış Türkçe transkripsiyonları yayımlamamak için altyazı doğrulaması sonraki entegrasyona bırakıldı.
- İlk aşamada gerçek MP4, uzun-form ses benzerliği, görsel tutarlılığı ve tam altyazılı üretim test edilmiş değildir. Önce kısa ses örneği kullanıcı tarafından dinlenip onaylanmalıdır.
- `approval.json` içindeki etiket yalnızca kullanıcı onayı kaydıdır, biyometrik eşleşme kanıtı değildir.
