"""V10: documentary B-roll source discipline.

V9 established the reference-inspired pacing. V10 fixes the first real smoke
failure by refusing to recycle a photo anywhere in the current story until the
provider pool has been exhausted, and broadens literal rural-house searches.
Production also rejects procedural artwork in story B-roll.
"""
import json

import cloud_v9 as v9
import cloud_v8 as v8
import cloud_v6 as v6
import cloud_v3 as v3

# Broader literal queries, still constrained by V8/V7 semantic rejection rules.
v8.SEARCHES.update({
    'house': [
        'old farmhouse exterior', 'old cottage exterior', 'rural house exterior',
        'wooden village house', 'old country house exterior',
    ],
    'room': [
        'old living room interior', 'old house room interior', 'empty cottage room',
        'rustic room interior',
    ],
    'corridor': [
        'old house hallway', 'empty old hallway', 'wooden house corridor',
        'abandoned residential hallway',
    ],
    'door': [
        'old wooden house door', 'rustic cottage doorway', 'old farmhouse door',
        'weathered house entrance',
    ],
})


def unique_asset_with_retry(assets, kind, recent):
    """Prefer a never-before-used real photo for the whole current video."""
    order = v6.ALTERNATES.get(kind, [kind, 'room', 'corridor', 'door', 'window'])
    last_error = None
    for candidate in order[:4]:
        # Calling get repeatedly advances provider offsets, so we inspect more than
        # the first image rather than accepting a duplicate returned later in the film.
        for _ in range(4):
            try:
                source = assets.get(candidate)
            except Exception as exc:
                last_error = exc
                break
            if source.name not in recent:
                return source, candidate
    if hasattr(assets, '_procedural_get'):
        # Smoke tests may need this when public image search is temporarily sparse.
        # The production wrapper below rejects procedural story B-roll.
        return assets._procedural_get(kind), kind
    if last_error:
        raise last_error
    raise ValueError(f'{kind} için tekrar etmeyen uygun görsel bulunamadı')


def render_v10(title, total, segments, report):
    v9.documentary_render(title, total, segments, report)
    sources_path = v3.OUT / 'visual_sources.json'
    shots_path = v3.OUT / 'shots.json'
    sources = json.loads(sources_path.read_text(encoding='utf-8')) if sources_path.exists() else []
    shots = json.loads(shots_path.read_text(encoding='utf-8')) if shots_path.exists() else []
    by_id = {str(item.get('id')): item for item in sources}
    story = [shot for shot in shots if not shot.get('intro')]
    generated = []
    for shot in story:
        source_id = shot.get('source', '').rsplit('.', 1)[0]
        item = by_id.get(source_id)
        if item and item.get('provider') == 'Generated':
            generated.append(shot.get('source'))
    if not report.get('preview') and generated:
        raise ValueError(
            'V10 prodüksiyon kalite kapısı: gerçek fotoğraf yerine programatik çizim kullanıldı: '
            + ', '.join(sorted(set(generated))[:8])
        )
    current = json.loads((v3.OUT/'quality_report.json').read_text(encoding='utf-8'))
    current.update({
        'version': 10,
        'global_photo_reuse_avoidance': True,
        'production_generated_broll_allowed': False,
        'generated_story_shots': len(generated),
    })
    v3.save('quality_report.json', current)
    v3.save('validation.json', current)


v6._asset_with_retry = unique_asset_with_retry
v3.create_story = v9.documentary_story
v3.Assets = v8.DiverseAssets
v3.framed_photo = v8.darker_frame
v3.narrate = v9.v7.narrate_v7
v3.render = render_v10

if __name__ == '__main__':
    v3.main()
