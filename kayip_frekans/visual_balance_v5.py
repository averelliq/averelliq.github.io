"""Grounded scene categorization: never invent a forest, person, candle or object.

A single keyword such as 'kapı' in a long paragraph must not turn the entire
video into door images. Preserve the narrated location; avoid consecutive near-
duplicates only where ANOTHER location or object is explicitly in the text.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

CUES = {
    'room': ('dolap', 'yatak', 'mutfak', 'masa', 'telefon', 'sandık', 'odam', 'odanın', 'oda '),
    'window': ('pencere', 'perde', 'camdan', 'camın', 'dışarı baktım'),
    'house': ('bahçe', 'avlu', 'evin önü', 'köy yolu', 'çamur', 'dışarıda'),
    'corridor': ('koridor', 'holün', 'holde', 'duvar', 'fısıltı', 'adım sesi'),
    'door': ('kapıyı', 'kapının', 'kapıdan', 'kapıya', 'kapı ', 'kilit', 'tokmak', 'eşik'),
    'stairs': ('merdiven', 'basamak', 'bodrum'),
    'forest': ('orman', 'ağaç', 'patika'),
    'candle': ('mum', 'alev', 'kibrit'),
}


def evidence(text):
    text = text.casefold()
    # A final concrete event is usually the most relevant image for a passage.
    last = re.split(r'[.!?…]\s+', text)[-2:]
    focus = ' '.join(last)[-350:]
    scores = {}
    for kind, terms in CUES.items():
        overall = sum(1 for word in terms if word in text)
        recent = sum(2 for word in terms if word in focus)
        if overall:
            scores[kind] = overall + recent
    return scores


def balance(segments):
    """Mutate 'kind' only from concrete supported cues; return distribution."""
    counts = Counter()
    previous = []
    for segment in segments:
        scores = evidence(str(segment.get('text', '')))
        if not scores:
            # Ambiguous internal scene: plain empty room, never random forest/candle.
            scores = {'room': 1, 'corridor': 1}
        n = len(previous)
        def rank(kind):
            # Repetition penalties matter only when the text supports alternatives.
            consecutive = (previous[-1] == kind) if previous else False
            repeated = len(previous) >= 2 and previous[-2:] == [kind, kind]
            ratio = counts[kind] / max(1, n)
            penalty = 1.5 * consecutive + 4 * repeated + (2 if ratio > .40 else 0)
            return (scores[kind] - penalty, -counts[kind], kind)
        kind = max(scores, key=rank)
        segment['kind'] = kind
        segment['visual_evidence'] = sorted(scores)
        previous.append(kind)
        counts[kind] += 1
    return dict(counts)


def validate(segments):
    if not segments:
        raise ValueError('Scene plan is empty')
    counts = Counter()
    for i, scene in enumerate(segments):
        kind = scene.get('kind')
        if kind not in CUES:
            raise ValueError(f'Unknown scene category at {i}: {kind}')
        scores = evidence(str(scene.get('text', '')))
        if scores and kind not in scores:
            raise ValueError(f'Scene {i}: unsupported image subject {kind}; evidence={list(scores)}')
        if float(scene.get('end', 0)) <= float(scene.get('start', 0)):
            raise ValueError(f'Scene {i}: invalid duration')
        counts[kind] += 1
    # If narration contains only one evidenced setting, do NOT hallucinate
    # additional ones just to satisfy a diversity quota. Surface the issue.
    return {'scene_count': len(segments), 'categories': dict(counts),
            'dominant_share': round(max(counts.values()) / len(segments), 3),
            'visual_repetition_warning': max(counts.values()) / len(segments) > .45}


if __name__ == '__main__':
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('output')
    statefile = directory / 'state.json'
    state = json.loads(statefile.read_text(encoding='utf-8'))
    balance(state['segments'])
    result = validate(state['segments'])
    (directory / 'scene_plan.json').write_text(
        json.dumps(state['segments'], ensure_ascii=False, indent=2), encoding='utf-8')
    (directory / 'visual_quality_v6.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    statefile.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Scene evidence audit:', json.dumps(result, ensure_ascii=False), flush=True)
