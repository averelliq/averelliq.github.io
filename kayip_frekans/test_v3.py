import unittest
from cloud_v3 import check_passage, duration_gate, caption_cues, category

class V3RegressionTests(unittest.TestCase):
    def test_original_failed_preview_is_rejected(self):
        with self.assertRaises(ValueError):
            check_passage('Yanlış kapıyı açtım. Babamın köy evinin kapısından gelen, ölümlü bir sesi duydum.',180,280)
        with self.assertRaises(ValueError):duration_gate(8.375,30,True)
    def test_long_video_cannot_be_a_short_clip(self):
        with self.assertRaises(ValueError):duration_gate(120,30,False)
        duration_gate(1790,30,False)
    def test_captions_use_actual_word_timing_with_passage_offset(self):
        b=[{'text':'Kapıyı','offset':5000000,'duration':2500000},
           {'text':'açmadım.','offset':12000000,'duration':4000000}]
        self.assertEqual(caption_cues(b,15),[(15.5,16.6,'Kapıyı açmadım.')])
    def test_empty_or_truncated_story_rejected(self):
        for t in ['', 'Kapının dışında biri vardı ama']:
            with self.assertRaises(ValueError):check_passage(t,1,100)
    def test_specific_objects_take_priority_over_generic_house(self):
        self.assertEqual(category('Köy evindeki kapının kilidine baktım.'),'door')
        self.assertEqual(category('Ormandaki patikaya girdim.'),'forest')

if __name__=='__main__':unittest.main()
