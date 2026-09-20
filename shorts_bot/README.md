# 40s Manufacturing & Restoration Shorts Bot

Özgün AI sahneleri veya kullanım hakkı doğrulanmış görüntülerden 40 saniyelik, 9:16 dikey üretim/restorasyon Shorts'u hazırlar ve gerçek MP4 üzerinde kalite kontrolü yapar.

## Özellikler

- 8–12 sahneli JSON video planı
- Her sahne için süre, işlem, başlangıç/bitiş durumu ve kaynak lisansı
- FFmpeg ile 1080×1920, 30 FPS, H.264/AAC çıktı
- 34–37. saniyede zorunlu `LIKE + SUBSCRIBE` katmanı
- Süre, oran, FPS, ses, kaynak ve CTA görünürlüğü kontrolleri
- QC başarısızsa yayın için onay üretmez
- Rastgele satisfying/espresso gibi konuları engeller
- Gerçekçi AI içeriğinde AI açıklaması yoksa planı reddeder
- Robotik flite sesi yayın modunda kapalıdır; doğal İngilizce ses dosyası gerekir
- Gerçek YouTube yüklemesi varsayılan olarak kapalıdır

## Hızlı kullanım

```bash
python3 shorts_bot.py run examples/restoration_plan.json --output out
```

`english_voice_caption.py` yayın modunda `--voice natural_voice.wav` olmadan çalışmaz. `--allow-robotic-test` sadece teknik test içindir ve yayınlanmamalıdır.

Gerçek kaynak kliplerini `examples/restoration_plan.json` içindeki `source` alanlarına yaz. Kaynakların kullanım hakkını `license` alanında belirtmeden plan onaylanmaz.

Test amaçlı sentetik demo:

```bash
python3 shorts_bot.py demo --output out/demo.mp4
python3 shorts_bot.py qc out/demo.mp4
```

Demo görüntüsü gerçek üretim görüntüsü değildir ve yayınlanmamalıdır.

## Yayın politikası

Bu sürüm MP4 + QC raporu üretir; YouTube OAuth bilgisi olmadan yükleme yapmaz. `qc_report.json` içindeki `publish_ready` değeri `true` olmadan yükleme adımı çalıştırılmamalıdır.
