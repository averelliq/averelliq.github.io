"""Dependency-free checks of the new MoneyPrinterTurbo channel profile."""
import unittest

import mpt_profile as profile

STORY = (
    'Kapıyı açtığımda içeride kimse yoktu. Ama kardeşimin sesini duydum. '
    'Koridorun sonundaki karanlığa baktım ve o gece evden çıkmadım. '
) * 4


class MptProfileTests(unittest.TestCase):
    def test_brief_transfers_kayip_frekans_requirements(self):
        text = profile.story_brief('Köy evindeki cin', 20)
        for token in ('birinci tekil', '15-20', '45-90', 'Türkçe', 'cin', 'KAYIP FREKANS_'):
            self.assertIn(token, text)

    def test_no_legacy_fallback_in_profile(self):
        self.assertFalse(profile.RULES['voice']['tts_fallback_allowed'])
        self.assertFalse(profile.RULES['voice']['ahmet_openvoice_allowed'])
        self.assertFalse(profile.RULES['quality_gates']['no_youtube_autopublish'] is False)

    def test_preview_story_is_valid(self):
        report = profile.check_story(STORY, 1, preview=True)
        self.assertTrue(report['editorial_mechanical_checks_passed'])
        self.assertFalse(report['voice_similarity_verified'])

    def test_bad_time_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Clock notation'):
            profile.check_story(STORY + ' Saat 03:15.', 1, preview=True)

    def test_old_channel_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Legacy'):
            profile.check_story(STORY + ' Gece Arşivi.', 1, preview=True)

    def test_greeting_before_hook_rejected(self):
        with self.assertRaisesRegex(ValueError, 'story hook'):
            profile.check_story('Merhaba Kayıp Frekans dinleyicileri. ' + STORY, 1, preview=True)

    def test_short_story_rejected(self):
        with self.assertRaisesRegex(ValueError, 'too short'):
            profile.check_story('Kapıyı açtım.', 20)

    def test_short_sample_is_not_full_narration_approval(self):
        approval = dict(
            voice_id=profile.VOICE_ID,
            source_audition_sha256=profile.AUDITION_SHA256,
            approved_by_user=True,
            full_narration_approved=False,
            fallback_tts_allowed=False,
        )
        with self.assertRaisesRegex(ValueError, 'short sample'):
            profile.check_approved_voice(approval)
        approval['full_narration_approved'] = True
        profile.check_approved_voice(approval)
        approval['voice_id'] = 'tr-TR-AhmetNeural'
        with self.assertRaisesRegex(ValueError, 'tok narrator'):
            profile.check_approved_voice(approval)


if __name__ == '__main__':
    unittest.main()
