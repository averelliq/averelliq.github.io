"""KAYIP FREKANS_ editorial contract for the MoneyPrinterTurbo main engine.

This supplies a story-generation brief AND mechanically checks supplied stories.
It never pretends that mechanical checks verify voice similarity or image semantics.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from quality import normalize_for_speech

CHANNEL = 'KAYIP FREKANS_'
VOICE_ID = 'serkan-v6-2-tok'
AUDITION_SHA256 = '586244cd639faf5fd5995d1f4a9e74c4bceb7a88852075eee8d046274ea9528b'

RULES = {
    'channel': CHANNEL,
    'language': 'tr-TR',
    'format': '16:9 landscape; long-form paranormal/cin horror',
    'narrative_person': 'first-person eyewitness; stable, named characters',
    'hook': 'Start with a concrete frightening event in the first 15-20 seconds; no channel greeting first.',
    'rhythm': 'Introduce a meaningful new question/clue/escalation approximately every 45-90 seconds.',
    'opening': 'Keep the first 2 minutes fast and necessary; do not over-explain backstory.',
    'causality': 'Plant clues before payoff; maintain geography, chronology, objects and supernatural rules.',
    'ending': 'Resolve the main question with earned payoff; no accidental cut-off or duplicate chapters.',
    'turkish': 'Natural, idiomatic Turkish; read clocks as spoken Turkish, never English digits.',
    'avoid_phrases': ['Final Story', 'Gece Arşivi', 'ışık izi oluştu', 'çatlak sesi'],
    'voice': {
        'id': VOICE_ID,
        'user_approved_sample_sha256': AUDITION_SHA256,
        'tts_fallback_allowed': False,
        'ahmet_openvoice_allowed': False,
        'complete_narration_requires_separate_approval': True,
    },
    'visuals': {
        'story_matched_assets_only': True,
        'stable_character_appearances': True,
        'no_random_abstract_fallback': True,
        'no_repeated_blurry_or_black_frames': True,
        'human_review_required': True,
    },
    'quality_gates': {
        'no_youtube_autopublish': True,
        'verify_full_audio_and_its_sha256': True,
        'check_duration_and_scene_timeline': True,
        'watch_final_video_before_publication': True,
    },
}


def story_brief(topic: str, minutes: int) -> str:
    """Reusable brief; pass to a chosen text model, never to MPT default prompts."""
    topic = str(topic).strip()
    if not topic or len(topic) > 500 or not 5 <= minutes <= 35:
        raise ValueError('A topic and a 5-35 minute target are required')
    return (
        f'Kanal: {CHANNEL}. Konu: {topic}. Hedef süre: yaklaşık {minutes} dakika.\n'
        'Türkçe, birinci tekil şahıs ağzından yaşanmış gibi ama kurmaca, cin/paranormal korku öyküsü yaz. '
        'İlk 15-20 saniyede doğrudan tehlikeli somut olayla başla; kanal adı, selamlama ve abonelik çağrısı ile başlama. '
        'İlk iki dakika hızlı aksın. Her 45-90 saniyede yeni ipucu, soru ya da tehlike yarat. '
        'Kişilerin adlarını ve görünüşünü, mekânların konumunu, zaman çizgisini, nesneleri ve cinin kurallarını değiştirme. '
        'İpuçlarını finalden önce ek; ana soruyu tutarlı biçimde yanıtla. '
        'Türkçede doğal olmayan kalıplardan, tekrar eden cümlelerden, açıklamasız sahne geçişlerinden kaçın. '
        'Saatleri Türkçe sözcüklerle yaz: 03:15 yerine gece üç on beş; 22:30 yerine gece on buçuk. '
        'Yalnızca okunacak hikâye metnini üret; Final Story, Gece Arşivi veya bölüm işaretleri yazma. '
        'Metni özetleme ya da yarıda bitirme. Her karakter ve mekân için sahne planında tutarlı görsel açıklaması hazırla.\n'
        'ÖNEMLİ: Bu talimat yalnızca senaryo içindir. Tok anlatıcı sesini oluşturduğunu veya görselleri onayladığını iddia etme.'
    )


def check_story(text: str, minutes: int, preview: bool = False) -> dict:
    text = str(text).strip()
    if not 1 <= minutes <= 35 or not text:
        raise ValueError('A nonempty story and valid minutes are required')
    if text != normalize_for_speech(text):
        raise ValueError('Clock notation must be converted to natural spoken Turkish before narration')
    words = text.split()
    minimum = 30 if preview else int(minutes * 120 * .6)
    if len(words) < minimum:
        raise ValueError(f'Story too short: {len(words)} words; minimum {minimum}')
    if re.search(r'(?i)\bfinal story\b|gece arşivi|ışık izi oluştu|çatlak sesi', text):
        raise ValueError('Legacy channel marker or disallowed unnatural expression in story')
    first = ' '.join(words[:45]).casefold()
    if first.startswith(('merhaba', 'selam', 'kanalıma hoş geldiniz', 'kanalımıza hoş geldiniz')):
        raise ValueError('Video must open with the story hook, not a channel introduction')
    if not re.search(r'[.!?…][\s”"\']*$', text):
        raise ValueError('Story ends in an incomplete sentence')
    paragraphs = [p.strip().casefold() for p in re.split(r'\n\s*\n', text) if p.strip()]
    if any(count > 1 and len(part.split()) > 12 for part, count in Counter(paragraphs).items()):
        raise ValueError('A long story paragraph was duplicated')
    if not re.search('[çğıöşüÇĞİÖŞÜ]', text):
        raise ValueError('Turkish characters missing; check UTF-8 corruption')
    return {
        'channel': CHANNEL,
        'story_words': len(words),
        'target_minutes': minutes,
        'preview': bool(preview),
        'editorial_mechanical_checks_passed': True,
        'character_continuity_verified': False,
        'voice_similarity_verified': False,
        'visual_story_match_verified': False,
        'human_review_required': True,
    }


def check_approved_voice(approval: dict) -> None:
    """User approved the tok AUDITION, not arbitrary future long narration."""
    if approval.get('voice_id') != VOICE_ID:
        raise ValueError('Only the user-selected tok narrator is permitted')
    if approval.get('source_audition_sha256') != AUDITION_SHA256:
        raise ValueError('Narrator must trace to the approved tok audition sample')
    if approval.get('approved_by_user') is not True:
        raise ValueError('Full narration has not been approved by the user')
    if approval.get('full_narration_approved') is not True:
        raise ValueError('Approval of the short sample is NOT approval of the full narration')
    if approval.get('fallback_tts_allowed') is not False:
        raise ValueError('TTS fallback must be explicitly disabled')


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--topic', default='')
    p.add_argument('--minutes', type=int, default=20)
    p.add_argument('--story', type=Path)
    p.add_argument('--approval', type=Path)
    p.add_argument('--preview', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args(argv)
    if args.story:
        report = check_story(args.story.read_text(encoding='utf-8-sig'), args.minutes, args.preview)
        if not args.approval:
            raise ValueError('An explicit narration approval JSON is required')
        check_approved_voice(json.loads(args.approval.read_text(encoding='utf-8')))
        output = {'rules': RULES, 'story_check': report}
    else:
        output = {'rules': RULES, 'prompt': story_brief(args.topic, args.minutes)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'profile_written': str(args.output), 'full_video_ready': False}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
