"""V14: offline, permitted Serkan-reference voice cloning; zero ElevenLabs credits.

No user reference audio is committed to the public repo. The reference is supplied
as a GitHub secret and deleted after the runner terminates. The voice-cloning
model is Chatterbox Multilingual V3, not Serkan's ElevenLabs-hosted voice.
"""
import json
import re
import wave

import cloud_v13 as v13
import cloud_v11 as v11
import cloud_v3 as v3
import clone_voice

OUT = v3.OUT


def _segments(parts, cap=245):
    if not parts or not parts[0].strip():
        raise ValueError('Giriş metni yok.')
    result = []
    for part in parts:
        sentences = v3.bot.sentences(part.replace('\n', ' '))
        group = ''
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) > cap:
                # Split oversize clauses without discarding or paraphrasing any text.
                clauses = re.findall(r'.{1,' + str(cap) + r'}(?:\s|$)', sentence)
                if not clauses:
                    clauses = [sentence[i:i+cap] for i in range(0, len(sentence), cap)]
            else:
                clauses = [sentence]
            for clause in clauses:
                clause = clause.strip()
                if group and len(group) + 1 + len(clause) > cap:
                    result.append(group)
                    group = ''
                group = (group + ' ' + clause).strip()
        if group:
            result.append(group)
    return result


def approximate_boundaries(text, duration):
    """Estimated timings ONLY; never claim these are speech-to-text alignments."""
    words = list(re.finditer(r'\S+', text))
    if not words or duration <= .25:
        raise ValueError('Kelime süresi veya ses uzunluğu geçersiz.')
    weights = [max(1.4, len(w.group().strip('.,!?…“”\'')) ** .65) for w in words]
    available = duration * .94
    scale = available / sum(weights)
    cursor = duration * .03
    result = []
    for token, weight in zip(words, weights):
        step = weight * scale
        result.append({'text': token.group(), 'offset': round(cursor * 10_000_000),
                       'duration': round(step * .96 * 10_000_000)})
        cursor += step
    return result


def narrate_clone(parts):
    OUT.mkdir(parents=True, exist_ok=True)
    secret, reference = clone_voice.require_reference()  # Fail before loading a large model.
    try:
        model = clone_voice.load_model()
        passages = _segments(parts)
        if not passages:
            raise ValueError('Seslendirilecek hikâye yok.')
        import torchaudio
        frames, cues, segments = [], [], []
        total = 0.0
        for index, text in enumerate(passages):
            pcm = OUT / f'narration-{index:03}.wav'
            audio = clone_voice.synthesize(model, text, reference)
            # Save as 24k mono s16 WAV to match the unchanged downstream renderer.
            torchaudio.save(str(pcm), audio.cpu(), model.sr)
            converted = OUT / f'narration-{index:03}-24k.wav'
            v3.bot.run('ffmpeg', '-v', 'error', '-y', '-i', pcm,
                       '-ac', '1', '-ar', '24000', '-c:a', 'pcm_s16le', converted)
            with wave.open(str(converted), 'rb') as reader:
                duration = reader.getnframes() / reader.getframerate()
                if duration <= .3 or duration > 65:
                    raise ValueError('Üretilen ses parçası beklenmeyen uzunlukta.')
                frames.append(reader.readframes(reader.getnframes()))
            words = approximate_boundaries(text, duration)
            cues.extend(v11.compact_caption_cues(words, total, text))
            segments.append({'start': total, 'end': total + duration,
                             'text': text, 'kind': v3.category(text)})
            total += duration
            print(f'Yerel seslendirme {index + 1}/{len(passages)} tamamlandı.', flush=True)
        with wave.open(str(OUT / 'narration.wav'), 'wb') as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(24000)
            writer.writeframes(b''.join(frames))
        v3.save('captions.srt', '\n\n'.join(
            f'{i+1}\n{v3.bot.stamp(a)} --> {v3.bot.stamp(b)}\n{content}'
            for i, (a, b, content) in enumerate(cues)) + '\n')
        v3.save('scene_plan.json', segments)
        v3.save('voice_report.json', {
            'voice_provider': 'self-hosted Chatterbox', 'voice_name': 'Serkan izinli referansından klon',
            'voice_model': clone_voice.MODEL_NAME, 'voice_model_license': clone_voice.MODEL_LICENSE,
            'voice_language': 'tr', 'elevenlabs_api_used': False,
            'elevenlabs_credits_used': 0, 'voice_fallback_used': False,
            'sample_voice_cloned': True,
            'caption_timing': 'approximate: proportional to actual clip durations; human review required',
        })
        return total, segments, cues
    finally:
        secret.cleanup()


def render_v14(title, total, segments, report):
    # Reuse V13's logo, palette and visual filtering, but correct its old voice labels.
    v13.render_v13(title, total, segments, report)
    info = json.loads((OUT / 'voice_report.json').read_text(encoding='utf-8'))
    current = json.loads((OUT / 'quality_report.json').read_text(encoding='utf-8'))
    current.update(info)
    current.update({'version': 14, 'captions_need_manual_alignment_review': True})
    current.pop('voice_id', None)
    v3.save('quality_report.json', current)
    v3.save('validation.json', current)
    metadata = json.loads((OUT / 'metadata.json').read_text(encoding='utf-8'))
    metadata.update({'narrator': 'Serkan referansı — Chatterbox Multilingual V3',
                     'narrator_sample_cloned': True,
                     'narrator_provider': 'self-hosted Chatterbox'})
    metadata.pop('narrator_voice_id', None)
    v3.save('metadata.json', metadata)


v3.narrate = narrate_clone
v3.render = render_v14
if __name__ == '__main__':
    v3.main()
