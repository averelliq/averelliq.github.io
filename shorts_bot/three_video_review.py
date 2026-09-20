"""Render three independent English how-it-works Shorts for review, never upload.

Each source module uses licensed, distinct Pexels clips and creates its own
scene evidence. Publication is a separate action on the *reviewed MP4 bytes*.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUEST = ROOT / 'three_video_request.json'
TOPICS = {
    'espresso': ('espresso_manual_review_entry', 'how an espresso machine brews coffee'),
    'grapes': ('grape_accurate_preview', 'how grapes become fresh juice'),
    'pottery': ('pottery_preview_entry', 'how a potter shapes a clay bowl on a wheel'),
}


def run(command):
    return subprocess.run(command, check=True, capture_output=True, text=True)


def metadata(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-show_entries',
                           'stream=codec_type,width,height:format=duration',
                           '-of', 'json', str(path)]).stdout)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in TOPICS:
        raise ValueError('Exactly one known independent topic is required')
    topic = sys.argv[1]
    request = json.loads(REQUEST.read_text(encoding='utf-8'))
    if (request != {'request_id': 'curiorush-three-reviewed-shorts-20260920-01',
                    'preview_only': True, 'topics': list(TOPICS)}
            or os.environ.get('SHORTS_SKIP_UPLOAD') != '1'
            or os.environ.get('GITHUB_REPOSITORY') != 'averelliq/averelliq.github.io'
            or os.environ.get('GITHUB_EVENT_NAME') != 'push'):
        raise RuntimeError('Preview authorization mismatch; no publication')
    if any(os.getenv(key) for key in ('YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_REFRESH_TOKEN')):
        raise RuntimeError('Preview job may not receive YouTube upload credentials')
    if not os.getenv('PEXELS_API_KEY'):
        raise RuntimeError('No real licensed footage source; refusing placeholder video')
    module_name, expected_subject = TOPICS[topic]
    print(f'RENDER PREVIEW {topic}: no YouTube credentials; no upload', flush=True)
    importlib.import_module(module_name).main()
    output = ROOT / 'output'
    mp4 = output / 'short.mp4'
    plan_file = output / 'plan.json'
    sources_file = output / 'visual_sources.json'
    if not all(item.is_file() for item in (mp4, plan_file, sources_file)):
        raise RuntimeError('MP4, plan or real-footage provenance missing')
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    sources = json.loads(sources_file.read_text(encoding='utf-8'))
    scenes = plan.get('scenes', [])
    identifiers = [item['pexels_video_id'] for item in sources]
    if (plan.get('topic') != expected_subject or not 6 <= len(scenes) <= 9
            or len(sources) != len(scenes) or len(set(identifiers)) != len(sources)
            or not all(isinstance(x, int) and x > 0 for x in identifiers)
            or not all(item.get('pexels_url', '').startswith('https://www.pexels.com/video/')
                       for item in sources)):
        raise RuntimeError('Scene topic mismatch, duplicate footage or missing provenance')
    original = metadata(mp4)
    video_streams = [s for s in original['streams'] if s.get('codec_type') == 'video']
    if (len(video_streams) != 1 or video_streams[0].get('width') != 1080
            or video_streams[0].get('height') != 1920
            or not any(s.get('codec_type') == 'audio' for s in original['streams'])):
        raise RuntimeError('Preview must have vertical full HD video and audio')
    duration = float(original['format']['duration'])
    if not 20 <= duration <= 60:
        raise RuntimeError('Unexpected Shorts duration')
    # Clearly legible silent CTA while leaving the lower subtitles and real objects uncovered.
    start = duration * 0.68
    end = start + 2.0
    draw = ("drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "text='LIKE + SUBSCRIBE':fontsize=52:fontcolor=white:"
            "borderw=3:bordercolor=black:box=1:boxcolor=black@0.72:boxborderw=14:"
            "x=(w-text_w)/2:y=h*0.13:"
            f"enable='between(t,{start:.3f},{end:.3f})'")
    temp = output / f'{topic}_cta.mp4'
    run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(mp4),
         '-map', '0:v:0', '-map', '0:a:0', '-vf', draw, '-c:v', 'libx264',
         '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
         '-c:a', 'copy', '-movflags', '+faststart', str(temp)])
    temp.replace(mp4)
    tested = metadata(mp4)
    if abs(float(tested['format']['duration']) - duration) > .2:
        raise RuntimeError('Final MP4 CTA edit shifted audio or duration')
    run(['ffmpeg', '-v', 'error', '-i', str(mp4), '-f', 'null', '-'])
    run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{start + 0.8:.3f}', '-i',
         str(mp4), '-frames:v', '1', str(output / f'{topic}_cta_proof.jpg')])
    plan['preview_only'] = True
    plan['cta'] = {'text': 'LIKE + SUBSCRIBE', 'start': round(start, 2),
                   'end': round(end, 2), 'visual_overlay': True}
    plan['final_mp4_decoded'] = True
    plan['subject_sources_count'] = len(sources)
    plan_file.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding='utf-8')
    (output / 'manual_review_required.txt').write_text(
        'Preview only. Inspect actual MP4 imagery, subtitles and spoken narration; '
        'publication of this exact MP4 requires separate approval.\n', encoding='utf-8')
    print(f'PREVIEW QC PASS: topic={topic}; {len(sources)} unique licensed clips; '
          f'{duration:.2f}s; 1080x1920; sound; CTA; full MP4 decode; NO UPLOAD', flush=True)


if __name__ == '__main__':
    main()
