"""Offline Piper narration after downloading the openly published model; fail closed if unavailable."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import wave

ROOT = Path(__file__).resolve().parents[1]
FPS = 30


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default='auto')
    args = parser.parse_args()
    topics = json.loads((ROOT / 'src/topics.json').read_text(encoding='utf-8'))
    ids = [item['id'] for item in topics]
    import datetime
    topic_id = ids[datetime.datetime.now(datetime.timezone.utc).date().toordinal() % len(ids)] if args.topic == 'auto' else args.topic
    if topic_id not in ids:
        parser.error('Unknown topic: ' + topic_id)
    topic = next(item for item in topics if item['id'] == topic_id)
    model = ROOT / 'voices/en_US-ryan-medium.onnx'
    if not model.is_file() or not (ROOT / 'voices/en_US-ryan-medium.onnx.json').is_file():
        raise SystemExit('Piper model missing: see README voice model setup.')
    out = ROOT / 'public/audio'
    out.mkdir(parents=True, exist_ok=True)
    frame = 0
    scenes = []
    for i, scene in enumerate(topic['scenes']):
        wav = out / f'{i:02d}.wav'
        subprocess.run(['piper', '--model', str(model), '--output_file', str(wav)], input=scene['line'], text=True, check=True)
        with wave.open(str(wav), 'rb') as handle:
            secs = handle.getnframes() / handle.getframerate()
        if not 1 <= secs <= 35:
            raise RuntimeError(f'Invalid narration length for scene {i}: {secs}')
        duration = round(secs * FPS) + 10
        scenes.append({**scene, 'fromFrame': frame, 'durationInFrames': duration, 'audio': f'audio/{i:02d}.wav'})
        frame += duration
    plan = {'id': topic_id, 'title': topic['title'], 'hook': topic['hook'], 'fps': FPS, 'totalFrames': frame, 'scenes': scenes}
    (ROOT / 'public/plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    (ROOT / 'out').mkdir(exist_ok=True)
    (ROOT / 'out/metadata.json').write_text(json.dumps({'title': topic['title'], 'description': 'An illustrated engineering explainer. Verify technical claims and visuals before publishing. #Engineering #HowItWorks #Shorts', 'topic': topic_id}, indent=2), encoding='utf-8')
    print(f'Prepared {topic_id}: {frame / FPS:.1f}s; {len(scenes)} voiced scenes')

if __name__ == '__main__':
    main()
