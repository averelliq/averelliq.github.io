"""V5 smoke harness for KAYIP FREKANS_.

Production keeps V4's strict editorial rejection. Only automated short smoke tests
may fall back to a human-reviewed canonical story so the TTS/render pipeline can
still be exercised when the small local model fails editorial QA.
"""
import json

import cloud_v4 as v4
import cloud_v3 as v3
from quality import intro_text

STRICT_CREATE = v4.reviewed_create_story

SAFE_SMOKE_STORY = """Gece yarısını biraz geçmişti. Köy evinin salonunda tek başıma otururken dış kapının ardından kardeşim Emre’nin sesi geldi: “Kapıyı aç, benim.” Elimdeki bardak masaya çarptı. Emre bir hafta önce trafik kazasında hayatını kaybetmişti ve o evde benden başka kimse yoktu.

Kapıya yaklaşmadım. Kilidin hâlâ kapalı olduğunu uzaktan görebiliyordum. Birkaç saniye sessizlik oldu. Sonra aynı ses, bu kez daha alçak bir tonla, çocukken bana söylediği lakabı kullanarak adımı fısıldadı. Bunu ailem dışında kimse bilmezdi. Telefonumu aldım ama ekranda şebeke yoktu. Pencerenin önündeki perde hafifçe kıpırdıyordu; dışarıdaysa rüzgâr bile yoktu.

Koridora çıktığım anda dışarıdaki ses kesildi. Rahatladığımı sandım. Tam geri dönecekken salon duvarının içinden üç kez tıklama geldi. Ardından Emre’nin sesi kulağımın dibindeymiş gibi, “Kapıyı açma,” dedi. Donup kaldım. Çünkü dış kapının öteki tarafından aynı anda başka bir ses, yine Emre’nin sesiyle, “Ben geldim,” diye fısıldıyordu.

Sabaha kadar hiçbir kapıyı açmadım. Gün ışığında duvarı kontrol ettiğimde sıvanın üzerinde içeriden dışarı doğru çizilmiş üç uzun iz vardı. Kilit yerindeydi, pencere kapalıydı ve odalarda ayak izi yoktu. O günden sonra o eve bir daha yalnız gitmedim. Hâlâ en çok düşündüğüm şey şu: Dışarıdaki ses beni içeri çağırmıyordu. İçerideki bir şey, dışarı çıkmak için benim kapıyı açmamı bekliyordu."""


def smoke_resilient_create_story(topic, minutes, preview):
    if not preview:
        # Never bypass editorial QA for a real/long production.
        return STRICT_CREATE(topic, minutes, preview)
    try:
        return STRICT_CREATE(topic, minutes, preview)
    except ValueError as exc:
        # Preserve the failed-model QA report for diagnosis, then use a reviewed
        # story ONLY to exercise narration, subtitles and visuals in CI.
        report_path = v3.OUT / 'quality_report.json'
        previous = {}
        if report_path.exists():
            try:
                previous = json.loads(report_path.read_text(encoding='utf-8'))
            except Exception:
                previous = {}
        title = 'Kapının Ardındaki Ses'
        story = v4.strict_check_passage(SAFE_SMOKE_STORY, 180, 280)
        review = v4.editor_review(story, True)
        if review.get('pass') is not True or review.get('issues'):
            raise ValueError('Güvenli smoke hikâyesi editör kontrolünden geçmedi: ' + str(review)) from exc
        report = {
            **previous,
            'version': 5,
            'preview': True,
            'human_review_required': True,
            'smoke_story_fallback': True,
            'model_story_rejected_reason': str(exc),
            'fallback_editor_review': review,
            'story_words': len(story.split()),
            'target_minutes': minutes,
            'youtube_uploaded': False,
        }
        intro = intro_text(title)
        v3.save('story_only.txt', story)
        v3.save('intro.txt', intro)
        v3.save('quality_report.json', report)
        print('Model hikâyesi QA tarafından reddedildi; yalnızca teknik smoke testi için denetlenmiş hikâye kullanılıyor.', flush=True)
        return title, [intro, story], report


v3.create_story = smoke_resilient_create_story

if __name__ == '__main__':
    v3.main()
