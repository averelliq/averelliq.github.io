"""V5 test harness for KAYIP FREKANS_.

Production keeps V4's strict AI-story editorial rejection. Automated push smoke
tests intentionally use a human-reviewed short story so narration/subtitles/
visuals/render can be reviewed quickly and independently from LLM quality.
"""
import json
import os

import cloud_v4 as v4
import cloud_v3 as v3
from quality import intro_text

STRICT_CREATE = v4.reviewed_create_story

SAFE_SMOKE_STORY = """Gece yarısını biraz geçmişti. Köy evinin salonunda tek başıma otururken dış kapının ardından kardeşim Emre’nin sesi geldi: “Kapıyı aç, benim.” Elimdeki bardak masaya çarptı. Emre bir hafta önce trafik kazasında hayatını kaybetmişti ve o evde benden başka kimse yoktu.

Kapıya yaklaşmadım. Kilidin hâlâ kapalı olduğunu uzaktan görebiliyordum. Birkaç saniye sessizlik oldu. Sonra aynı ses, bu kez daha alçak bir tonla, çocukken bana söylediği lakabı kullanarak adımı fısıldadı. Bunu ailem dışında kimse bilmezdi. Telefonumu aldım ama ekranda şebeke yoktu. Pencerenin önündeki perde hafifçe kıpırdıyordu; dışarıdaysa rüzgâr bile yoktu.

Koridora çıktığım anda dışarıdaki ses kesildi. Rahatladığımı sandım. Tam geri dönecekken salon duvarının içinden üç kez tıklama geldi. Ardından Emre’nin sesi kulağımın dibindeymiş gibi, “Kapıyı açma,” dedi. Donup kaldım. Çünkü dış kapının öteki tarafından aynı anda başka bir ses, yine Emre’nin sesiyle, “Ben geldim,” diye fısıldıyordu.

Sabaha kadar hiçbir kapıyı açmadım. Gün ışığında duvarı kontrol ettiğimde sıvanın üzerinde içeriden dışarı doğru çizilmiş üç uzun iz vardı. Kilit yerindeydi, pencere kapalıydı ve odalarda ayak izi yoktu. O günden sonra o eve bir daha yalnız gitmedim. Hâlâ en çok düşündüğüm şey şu: Dışarıdaki ses beni içeri çağırmıyordu. İçerideki bir şey, dışarı çıkmak için benim kapıyı açmamı bekliyordu."""


def technical_smoke_story(minutes):
    title = 'Kapının Ardındaki Ses'
    story = v4.strict_check_passage(SAFE_SMOKE_STORY, 180, 280)
    intro = intro_text(title)
    report = {
        'version': 5,
        'preview': True,
        'human_review_required': True,
        'technical_smoke_story': True,
        'story_source': 'human-reviewed fixed CI story',
        'story_words': len(story.split()),
        'target_minutes': minutes,
        'youtube_uploaded': False,
        'note': 'Bu kısa CI testi AI hikâye kalitesini ölçmez; ses, altyazı, görsel ve montaj hattını test eder.',
    }
    v3.save('story_only.txt', story)
    v3.save('intro.txt', intro)
    v3.save('quality_report.json', report)
    print('Hızlı teknik smoke hikâyesi hazır; AI hikâye üretimi bu testte bilinçli olarak atlandı.', flush=True)
    return title, [intro, story], report


def create_story(topic, minutes, preview):
    if preview and os.getenv('FAST_VISUAL_SMOKE', '0') == '1':
        return technical_smoke_story(minutes)
    # Manual smoke tests can still exercise the AI/editor path; full production
    # can never fall back to the fixed test story.
    return STRICT_CREATE(topic, minutes, preview)


v3.create_story = create_story

if __name__ == '__main__':
    v3.main()
