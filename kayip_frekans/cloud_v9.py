"""V9 documentary-horror profile for KAYIP FREKANS_.

Uses the structural strengths observed in the reference channel without copying
its story, wording or assets: grounded first-person realism, slow-burn escalation,
environment-heavy B-roll, delayed paranormal confirmation, sparse atmosphere and
longer moving shots.
"""
import json
import math
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

import cloud_v8 as v8
import cloud_v7 as v7
import cloud_v6 as v6
import cloud_v5 as v5
import cloud_v4 as v4
import cloud_v3 as v3
from quality import clean_title, intro_text

OUT = v3.OUT
FPS = v3.FPS

# Reference-derived STYLE only. Never copy a competitor story or wording.
v3.SYSTEM += (
    ' Belgesel gerçekçiliğinde, sade ve inandırıcı bir korku anlatımı kullan. '
    'İlk saniyelerde açıklanmayan somut bir tuhaflık göster fakat doğaüstünün adını hemen koyma. '
    'Önce gündelik hayatı, karakter ilişkilerini ve mekânı gerçekçi biçimde kur; '
    'ilk kesin doğaüstü kanıt toplam anlatının yüzde otuz ile kırk beşi arasında gelsin. '
    'Korkuyu küçük sesler, davranışlar, koku, sıcaklık, kapı, koridor, pencere ve çevre ayrıntılarıyla büyüt. '
    'Kısa ve doğal cümlelerle vurgu yap. Her yaklaşık kırk beş-doksan saniyede yeni soru, ipucu veya risk doğsun. '
    'Finalde önceden bırakılan ipuçlarının anlamı ortaya çıksın. Gereksiz bağırma, şiirsel süs ve aşırı açıklama yapma.'
)


def _review_blocks(parts):
    """Review the whole long story in context-sized blocks instead of only its tail."""
    reviews = []
    for start in range(0, len(parts), 3):
        block = '\n\n'.join(parts[start:start+3])
        review = v4.editor_review(block, False)
        reviews.append({'chapters': [start+1, min(start+3, len(parts))], 'review': review})
        if review.get('pass') is not True or review.get('issues'):
            raise ValueError(
                f'Belgesel hikâye editörü {start+1}-{min(start+3,len(parts))}. bölümlerde hata buldu: '
                + json.dumps(review.get('issues') or [], ensure_ascii=False)
            )
    return reviews


def documentary_story(topic, minutes, preview):
    # Keep the deterministic smoke story for cheap CI checks. Manual/production runs use V9.
    if preview and os.getenv('FAST_VISUAL_SMOKE', '0') == '1':
        return v5.create_story(topic, minutes, preview)
    if preview:
        return v5.STRICT_CREATE(topic, minutes, preview)

    chapter_count = max(10, round(minutes / 1.4))
    reveal_low = max(3, math.ceil(chapter_count * .30))
    reveal_high = max(reveal_low, math.floor(chapter_count * .45))
    report = {
        'version': 9,
        'preview': False,
        'human_review_required': True,
        'reference_style': 'documentary slow-burn horror; structure only, no copied story',
        'target_minutes': minutes,
        'planned_chapters': chapter_count,
        'paranormal_confirmation_window': [reveal_low, reveal_high],
        'youtube_uploaded': False,
    }

    plan = None
    for _ in range(3):
        candidate = v3.ask(
            'Konu: ' + topic + f'. Tam {chapter_count} bölümlük özgün bir Türkçe korku hikâyesi planı oluştur. '
            'Hedef, yaşanmış olay anlatısı gibi sade ve belgesel gerçekçiliğinde bir slow-burn yapı. '
            f'İlk kesin ve tartışmasız doğaüstü kanıt {reveal_low}. ile {reveal_high}. bölüm arasında gelmeli. '
            'Bundan önce tuhaflıklar olsun ama karakter bunlara makul açıklamalar arayabilsin. '
            'İlk bölümün ilk iki cümlesinde somut, ürpertici ve henüz açıklanmayan bir olay olsun. '
            'Sonra günlük hayat, karakter ilişkileri ve tek ana mekânı inandırıcı kur. '
            'Her bölüm yeni bir ipucu, soru, davranış değişikliği veya risk eklesin; tekrar etmesin. '
            'Koku, sıcaklık, tahta sesi, kapı, pencere, koridor, hayvan davranışı, telefon veya çevre sesi gibi '
            'duyusal ayrıntıları olayla anlamlı bağla. Final bütün ana ipuçlarını geri ödesin. '
            'Cin/varlık gibi açıklamaları erkenden kesin gerçek olarak söyleme. '
            'JSON şeması: {"title":"kısa merak uyandıran başlık","characters":"kişiler ve değişmez ilişkiler",'
            '"setting":"ana mekân, dönem ve fiziksel kurallar","timeline":"zaman akışı",'
            '"paranormal_rules":"finale kadar bozulmayacak kurallar","clues":["önceden ekilecek ipucu ve final karşılığı"],'
            '"reveal_chapter":0,"chapters":[{"beat":"olay","question":"bölüm sonunda açık kalan merak",'
            '"sensory":"sahneye özgü duyusal ayrıntı","visuals":["çevre B-roll fikirleri"]}]}. '
            'Ana karakterin yüzünü tarif etmeye odaklanma; çevre ve mekân görsel olarak daha önemlidir.',
            True,
        )
        chapters = candidate.get('chapters') if isinstance(candidate, dict) else None
        reveal = candidate.get('reveal_chapter') if isinstance(candidate, dict) else None
        if (isinstance(chapters, list) and len(chapters) == chapter_count and
                isinstance(reveal, int) and reveal_low <= reveal <= reveal_high):
            plan = candidate
            break
    if plan is None:
        raise ValueError('V9 belgesel slow-burn planı kurallara uygun üretilemedi.')

    v3.save('plan.json', plan)
    title = clean_title(plan.get('title') or topic)
    target_words = max(165, round(minutes * 132 / chapter_count))
    parts = []
    for i, chapter in enumerate(plan['chapters']):
        before_reveal = i + 1 < plan['reveal_chapter']
        previous = parts[-1] if parts else 'Henüz yok; doğrudan ilk tuhaf olayla başla.'
        prompt = (
            'Aşağıdaki sabit hikâye planına göre yalnızca sıradaki bölümü yaz.\n'
            f'PLAN: {json.dumps(plan, ensure_ascii=False)}\n'
            f'ÖNCEKİ BÖLÜM: {previous}\n'
            f'ŞİMDİKİ BÖLÜM {i+1}/{chapter_count}: {json.dumps(chapter, ensure_ascii=False)}\n'
            'Birinci tekil şahıs kullan. Yaşanmış olay anlatır gibi sade, ölçülü ve doğal Türkiye Türkçesi yaz. '
            'Sadece olayda gerçekten hissedilebilecek duyusal ayrıntıları kullan. '
            'Karakter, mekân, eşya ve zaman çizgisini değiştirme. Önceki bölümü özetleme. '
            'Her paragraf olay ilerletsin; yapay korku sıfatlarını üst üste dizme. '
            + ('Bu aşamada doğaüstü açıklamayı kesinleştirme; anlatıcı hâlâ makul açıklama arayabilsin. '
               if before_reveal else 'Bu aşamada kanıtlar güçlenebilir; yine de anlatıcı gereksiz açıklama yapmasın. ')
            + ('İlk iki cümlede doğrudan planlanan tekinsiz olayı göster. ' if i == 0 else '')
            + ('Finalde plandaki ana ipuçlarını geri öde ve ana soruyu cevapla; ucuz bir rüya/halüsinasyon kaçışı yapma.'
               if i == chapter_count - 1 else 'Bölümün sonunda bir sonraki bölüme doğal bir merak boşluğu bırak.')
        )
        part = v3.write_passage(prompt, round(target_words * .90), round(target_words * 1.12))
        v4.strict_check_passage(part, round(target_words * .90), round(target_words * 1.12))
        parts.append(part)
        v3.save('story_only.txt', '\n\n'.join(parts))
        print(f'Belgesel hikâye {i+1}/{chapter_count}', flush=True)

    report['block_editor_reviews'] = _review_blocks(parts)
    report['story_words'] = sum(len(p.split()) for p in parts)
    report['reveal_chapter'] = plan['reveal_chapter']
    report['slow_burn_gate_passed'] = reveal_low <= plan['reveal_chapter'] <= reveal_high
    v3.save('story_only.txt', '\n\n'.join(parts))
    v3.save('intro.txt', intro_text(title))
    v3.save('quality_report.json', report)
    return title, [intro_text(title)] + parts, report


def documentary_render(title, total, segments, report):
    """Reference-like pacing: longer B-roll shots with continuous subtle movement."""
    assets = v8.DiverseAssets()
    shots, recent = [], []
    timeline = 0.0
    index = 0
    intro_shots = 0
    story_target = float(os.getenv('DOCUMENTARY_SHOT_SECONDS', '23'))
    story_target = min(28.0, max(18.0, story_target))

    for seg_index, seg in enumerate(segments):
        duration = seg['end'] - seg['start']
        is_intro = seg_index == 0 and 'merhaba kayıp frekans' in seg['text'].casefold()
        target = 7.5 if is_intro else story_target
        count = max(1, math.ceil(duration / target))
        kinds = v8.better_visual_kinds(seg['text'], count, seg.get('kind', 'corridor'))
        per_shot = duration / count

        if is_intro:
            intro = v6.make_intro_frame(title)
            for _ in range(count):
                clip, actual = v6._render_still(intro, index, per_shot)
                shots.append({'path': clip.name, 'source': intro.name, 'start': timeline,
                              'duration': actual, 'category': 'intro', 'intro': True})
                timeline += actual; index += 1; intro_shots += 1
            continue

        for kind in kinds:
            source, used_kind = v6._asset_with_retry(assets, kind, recent)
            recent.append(source.name)
            photo = v8.darker_frame(source, index)
            clip, actual = v6._render_still(photo, index, per_shot)
            shots.append({'path': clip.name, 'source': source.name, 'start': timeline,
                          'duration': actual, 'category': used_kind, 'intro': False})
            timeline += actual; index += 1

    story_shots = [s for s in shots if not s['intro']]
    min_story_shots = 4 if report.get('preview') else max(45, round(total / 32))
    if len(story_shots) < min_story_shots:
        raise ValueError(f'V9 belgesel sahne sayısı yetersiz: {len(story_shots)} < {min_story_shots}.')
    source_counts = {}
    for shot in story_shots:
        source_counts[shot['source']] = source_counts.get(shot['source'], 0) + 1
    unique_sources = len(source_counts)
    required_unique = 3 if report.get('preview') else min(30, max(12, math.ceil(len(story_shots) * .20)))
    if unique_sources < required_unique:
        raise ValueError(f'V9 görsel çeşitlilik yetersiz: {unique_sources} < {required_unique}.')
    if source_counts and max(source_counts.values()) / len(story_shots) > .20:
        raise ValueError('V9 aynı fotoğraf hikâyenin yüzde yirmisinden fazlasında tekrar ediyor.')
    categories = {s['category'] for s in story_shots}
    if len(categories) < (3 if report.get('preview') else 5):
        raise ValueError(f'V9 çevre B-roll çeşitliliği yetersiz: {sorted(categories)}')

    v3.save('shots.json', shots)
    v3.save('concat.txt', ''.join(f"file '{s['path']}'\n" for s in shots))
    v3.bot.run('ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0',
               '-i', OUT/'concat.txt', '-c', 'copy', OUT/'visuals.mp4')

    full_srt = (OUT/'captions.srt').read_text(encoding='utf-8')
    story_start = segments[1]['start'] if len(segments) > 1 else 0
    burn = v7.story_only_srt(full_srt, story_start)
    v3.save('captions_burned.srt', burn)

    # Quieter/sparser than the previous mix: the narrator is the focus.
    drone = f"aevalsrc=0.012*sin(2*PI*55*t)+0.004*sin(2*PI*82.41*t):s=24000:d={total}"
    filters = (
        "[0:v]tpad=stop_mode=clone:stop_duration=1,"
        "subtitles=output/captions_burned.srt:force_style='FontName=DejaVu Sans,FontSize=44,"
        "Outline=3,Shadow=1,MarginV=58,Alignment=2'[v];"
        "[1:a]highpass=f=65,lowpass=f=11500,alimiter=limit=0.90:level=false,asplit=2[voice][side];"
        "[2:a]afade=t=in:d=3,volume=0.42[drone];"
        "[3:a]highpass=f=70,lowpass=f=900,volume=0.005[roomtone];"
        "[drone][roomtone]amix=inputs=2:duration=longest:normalize=0[amb];"
        "[amb][side]sidechaincompress=threshold=0.010:ratio=9:attack=18:release=650[bed];"
        "[voice][bed]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=false[a]"
    )
    v3.bot.run('ffmpeg', '-v', 'error', '-y', '-i', OUT/'visuals.mp4',
               '-i', OUT/'narration.wav', '-f', 'lavfi', '-i', drone,
               '-f', 'lavfi', '-i', f'anoisesrc=color=brown:amplitude=0.08:sample_rate=24000:d={total}',
               '-filter_complex', filters, '-map', '[v]', '-map', '[a]', '-t', f'{total:.5f}',
               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', OUT/'final.mp4')

    normalized = OUT/'final-normalized.mp4'
    v3.bot.run('ffmpeg', '-v', 'error', '-y', '-i', OUT/'final.mp4',
               '-map', '0:v:0', '-map', '0:a:0', '-c:v', 'copy',
               '-af', 'loudnorm=I=-16:TP=-1.5:LRA=7', '-ar', '48000', '-ac', '2',
               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', normalized)
    os.replace(normalized, OUT/'final.mp4')

    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(OUT/'final.mp4')
    ]))
    measured = float(probe['format']['duration'])
    streams = {s['codec_type']: s for s in probe['streams']}
    if abs(measured-total) > .25 or set(streams) != {'video', 'audio'}:
        raise ValueError('V9 final ses/görüntü doğrulaması başarısız.')
    if int(streams['video'].get('width', 0)) != v3.W or int(streams['video'].get('height', 0)) != v3.H:
        raise ValueError('V9 final video 1920x1080 değil.')

    first_story = intro_shots
    cover_path = OUT / f'shot-{first_story:04}.jpg'
    cover = Image.open(cover_path).convert('RGB')
    draw = ImageDraw.Draw(cover)
    thumb = 'KAPININ ARDINDA\nKİM VAR?' if report.get('preview') else title[:58]
    y = 650
    for line in thumb.split('\n'):
        draw.text((105, y), line, font=ImageFont.truetype(v3.bot.FONT, 94), fill='white',
                  stroke_width=6, stroke_fill='black')
        y += 120
    cover.save(OUT/'thumbnail.jpg', quality=95)

    sources = json.loads((OUT/'visual_sources.json').read_text(encoding='utf-8')) if (OUT/'visual_sources.json').exists() else []
    unique_records = {str(p.get('id')): p for p in sources}.values()
    credit_lines, providers = [], set()
    for p in unique_records:
        provider = p.get('provider', 'Pexels'); providers.add(provider)
        if provider == 'Generated':
            credit_lines.append('KAYIP FREKANS_ / özgün programatik atmosfer çizimi')
        else:
            line = f"{p.get('photographer','Bilinmeyen')} / {provider} / {p.get('license','')}"
            if p.get('url'): line += f" / {p['url']}"
            credit_lines.append(line)
    credits = '\n'.join(credit_lines)
    v3.save('credits.txt', credits)
    v3.save('metadata.json', {
        'title': title, 'channel': 'KAYIP FREKANS_', 'duration_seconds': measured,
        'test_video': bool(report.get('preview')),
        'description': f'{title}\n\nKurmaca paranormal korku hikâyesi. Belgesel anlatım tarzı; özgün hikâye. '
                       'Atmosfer görüntüleri temsili serbest lisanslı çevre görselleridir.\n\nGörsel kaynakları:\n' + credits,
        'tags': ['korku hikayeleri', 'paranormal hikayeler', 'cinli hikayeler', 'KAYIP FREKANS_'],
        'audio': 'AAC 48 kHz stereo; -16 LUFS / -1.5 dBTP hedefi',
        'visual_providers': sorted(providers),
    })

    current = json.loads((OUT/'quality_report.json').read_text(encoding='utf-8'))
    current.update({
        'version': 9,
        'documentary_reference_profile': True,
        'story_shot_target_seconds': story_target,
        'story_shots': len(story_shots),
        'unique_story_sources': unique_sources,
        'environment_broll_categories': sorted(categories),
        'max_single_source_share': round(max(source_counts.values())/max(1,len(story_shots)), 3),
        'intro_captions_burned': False,
        'caption_punctuation_preserved': True,
        'people_in_stock_images_allowed': False,
        'audio_target_lufs': -16,
        'audio_true_peak_target_db': -1.5,
        'audio_sample_rate': 48000,
        'audio_channels': 2,
        'mechanical_checks_passed': True,
        'youtube_uploaded': False,
    })
    v3.save('quality_report.json', current); v3.save('validation.json', current)


v3.create_story = documentary_story
v3.Assets = v8.DiverseAssets
v3.framed_photo = v8.darker_frame
v3.narrate = v7.narrate_v7
v3.render = documentary_render

if __name__ == '__main__':
    v3.main()
