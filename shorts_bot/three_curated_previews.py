"""Rerender ONLY source-reviewed real glassblowing and classic typewriter shorts.

Do not fabricate missing grape-juicing footage: that subject stays blocked until
appropriate pressing footage is licensed and actually reviewed.
"""
from __future__ import annotations

import os
import pottery_preview_entry as source
import three_offline_previews as batch

IDS = {
    'glass': (7520876, 7519301, 7519297, 7519299, 7519303, 7520868, 7518822),
    'typewriter': (6037662, 8869774, 6037656, 6143906, 9568961, 27378936, 7888283),
}

GLASS_LINES = (
    'Watch how glassblowers shape glowing, hot glass.',
    'A worker heats the glass so that it stays soft enough to shape.',
    'Careful movements change its shape while the glass is hot.',
    'The maker turns the piece while working with the glowing material.',
    'Heat and careful tools help control the form of the glass.',
    'The glassblower keeps the work hot and turns it carefully.',
    'Shaping glass takes repeated, controlled movements and plenty of heat.',
)


def main():
    name = os.environ.get('SHORTS_BATCH_TOPIC', '')
    if name not in IDS:
        raise ValueError('No independently vetted complete video sequence for topic')
    if os.environ.get('SHORTS_SKIP_UPLOAD') != '1':
        raise ValueError('Curated previews must never upload directly')
    original_collect = source.collect
    def selected():
        pool = original_collect()
        by_id = {item['id']: item for item in pool}
        absent = [i for i in IDS[name] if i not in by_id]
        if absent:
            raise ValueError(f'Approved source unavailable; no replacements allowed: {absent}')
        return [by_id[i] for i in IDS[name]]
    source.collect = selected
    if name == 'glass':
        batch.CONFIG['glass']['speech'] = list(GLASS_LINES)
        batch.CONFIG['glass']['captions'] = ['Hot glass', 'Careful heating', 'Glass changes shape', 'Turning the piece', 'Heat and tools', 'Keeping it hot', 'Glassblowing']
    batch.main()


if __name__ == '__main__':
    main()
