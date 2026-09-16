import unittest

import cloud_v6 as v6


class VisualPlanTests(unittest.TestCase):
    def test_sentence_context_changes_categories(self):
        text = ('Kapı kilitliydi. Pencerenin önündeki perde kıpırdadı. '
                'Koridora çıktım. Salon duvarından üç kez ses geldi.')
        kinds = v6.choose_visual_kinds(text, 8, 'door')
        self.assertGreaterEqual(len(set(kinds)), 3)
        self.assertIn('window', kinds)
        self.assertTrue(any(k in kinds for k in ('corridor', 'room')))

    def test_single_door_subject_is_not_repeated_forever(self):
        kinds = v6.choose_visual_kinds('Kapı kilitliydi ve kapının ardından ses geliyordu.', 7, 'door')
        self.assertGreaterEqual(len(set(kinds)), 2)
        self.assertFalse(all(k == 'door' for k in kinds))

    def test_rich_category_prefers_local_scene(self):
        self.assertEqual(v6.rich_category('Perde pencerenin önünde hafifçe kıpırdadı.'), 'window')
        self.assertEqual(v6.rich_category('Koridora çıktım ve adım sesi duydum.'), 'corridor')
        self.assertEqual(v6.rich_category('Salon duvarında üç çizik vardı.'), 'room')


if __name__ == '__main__':
    unittest.main()
