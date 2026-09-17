# KAYIP FREKANS_ — MoneyPrinterTurbo ana video motoru

**Durum:** MoneyPrinterTurbo, uzun video MONTAJI için tercih edilen ana motor; eski V5 yalnızca yedek ve açıkça işaretlenmiş `legacy_voice_approved` seçeneğiyle çalışır. Bu belge veya başarılı bir birim testi, 15–30 dakika uçtan uca video üretiminin gerçekleştiğini göstermez. YouTube otomatik yayını kapalıdır.

## Eski bottan taşınan gerçek kurallar

`mpt_profile.py` eski `cloud_v3.py` hikâye yönergesini / `quality.py` metin denetimlerini MoneyPrinterTurbo üretim girdisi için kullanır: Türkçe birinci şahıs cin/paranormal anlatımı; ilk 15–20 saniyede doğrudan olay, ilk 2 dakika hızlı tempo, 45–90 saniyede yeni merak; sabit karakter/mekân/eşya ve ekilen ipuçları; Türkçe doğal saatler, eksiksiz son, eski Gece Arşivi / Final Story ibarelerinin reddi. `mpt_bridge.py` yalnızca önceden incelenmiş 16:9 yerel materyalleri sırayla kullanır; yanlış, düşük çözünürlüklü veya tekrarlı görsellere yönelik mekanik kontrolleri vardır. Bunlar görselin hikâyeyi gerçekten doğru resmettiğini **otomatik kanıtlamaz**.

## Ses tercihi

Kullanıcı, `serkan-v6-2-tok` adlı **kısa ses karakterini** onayladı. Kimlik ve orijinal kısa deneme SHA-256'sı `approved_voice.json` içinde tutuluyor. Bu onay 20–30 dakikalık ilerideki her yeni ses dosyasının dinlenip onaylandığı anlamına gelmez. Yeni uzun anlatım, bu tok referansa dayalı olarak ayrı hazırlanmalı, baştan sona dinlenmeli ve yalnızca sonra `approval.json` ile paketlenmelidir. `mpt_profile.py` başka ses, Ahmet/OpenVoice veya TTS fallback seçimine izin vermez. MoneyPrinterTurbo'nun `custom_audio_file` seçeneği onaylı WAV'ı doğrudan kullanır; kendi TTS'si devre dışı kalır. 44,5 saniyelik özel referansı veya API anahtarlarını **bu herkese açık depoya yüklemeyin**.

## Ana iş akışı

[ANA BOT Actions](https://github.com/averelliq/averelliq.github.io/actions/workflows/kayip-frekans-mpt.yml) → **Run workflow**.

- `brief`: konuyu ve hedef dakikayı girince hikâye yazım kurallarını içeren JSON verir; **hikâyeyi veya videoyu üretmez** ve ücretli API çağırmaz.
- `preview`: 20–90 saniyelik onaylanmış hikâye/ses/görsel paketi gerektirir; `source_run_id` ve `artifact_name` ile Actions artifact'ından alır.
- `full`: 15–20 dakikalık ayrı onaylanmış paket gerektirir; 30 dakikalık üretim henüz doğrulanmadığı için açılmadı.
- `run_video=false`: yalnızca sözleşme, ses SHA-256, sahne çizelgesi ve metin kontrollerini çalıştırır. `run_video=true`: kontroller geçerse sabitlenmiş [MoneyPrinterTurbo MIT commit'ini](https://github.com/harry0703/MoneyPrinterTurbo/commit/633dbb0cf6866e817a023f30c5ac20c6cf3f76de) geçici GitHub sunucusunda kurar ve yalnızca `custom_audio_file` ile montajı dener. Başarıyla video ürettiğini söylemek için ayrıca gerçek MP4 ve ses-görsel eşlemesi incelenmelidir.

### Girdi artifact klasör yapısı

```text
story.txt                  # Onaylanmış tam Türkçe metin; ham saat yazımı yok
narration.wav              # Bu metnin tamamının onaylanmış TOK seslendirmesi
approval.json              # İki ayrı onay ve WAV dosyasının SHA-256'sı
scenes.json                # Başlangıç/bitiş, açıklama, tür ve onaylı görsel yolları
assets/
  scene001.png
  scene002.jpg
  ...
```

`approval.json` örneği (HASH alanlarını **gerçek dosyaya göre** hesaplayın; örnekteki yer tutucu geçersizdir):

```json
{
  "approved_by_user": true,
  "full_narration_approved": true,
  "voice_id": "serkan-v6-2-tok",
  "voice_label": "Serkan Demirci",
  "source_audition_sha256": "586244cd639faf5fd5995d1f4a9e74c4bceb7a88852075eee8d046274ea9528b",
  "audio_sha256": "FULL_WAV_SHA256_HERE",
  "fallback_tts_allowed": false
}
```

`scenes.json` biçimi: `[ { "start": 0, "end": 8, "kind": "door", "description": "Hikâyede anlatılan kilitli ahşap kapı", "asset": "assets/scene001.png", "approved_by_user": true }, ... ]`. Zaman çizelgesi tüm WAV süresini yaklaşık karşılamalı; her sahne 3–25 saniye; minimum 1280×720; aynı görsel ikiden fazla kullanılmamalı. Görseller kullanıcı tarafından gerçekten incelenmeden `approved_by_user=true` yazılmamalı. **Short testteki yazı kartları onaylı gerçek sahneler sayılmaz.**

Kaynak run ID, video veya özel ses yükleme çözümü değildir: ayrı bir GitHub Actions run'ının içindeki gerçek girdi artifact'ına işaret eder. Mevcut 23 saniyelik ses denemesi artifact'ı, tam uzunlukta paket yerine geçmez. Public repo üzerindeki Actions artifact'ları için erişim/gizlilik beklentilerini ayrıca kontrol edin; yayınlamak istemediğiniz ham referans sesini eklemeyin.

## Dürüst sınırlar ve maliyet

Kod ve iş akışı GitHub sunucusunda çalışır, kullanıcının bilgisayarına MoneyPrinterTurbo kurulmaz. Ücretsiz açık kaynak yazılım kullanılsa bile GitHub Actions kota/limitleri ve stok medya API kotaları geçerlidir; sınırsız ücretsiz bulut veya tek tuşla 30 dakikalık video **garanti edilmez**. Yeni sesin 15–30 dakika üretimi, görsellerin bulunması, kaynakların gerçek hikâyeye uyumu ve üretim sonrası izleme hâlen ayrı aşamalardır. Eski bot dosyalarını testler tamamlanmadan silmeyin.
