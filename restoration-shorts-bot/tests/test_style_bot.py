import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import style_bot

class ExampleStyleTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            'source':'pexels', 'pexels_video_id':123, 'title':'Rusty Iron Restored #Shorts',
            'item':'rusty iron', 'observed_steps':['the rust is removed carefully',
            'the metal surface is cleaned and polished', 'a new handle is shaped and fitted'],
            'human_reviewed':True, 'rights_reviewed':True,
            'burned_in_captions_or_watermark':False, 'visible_before_and_after':True,
            'rusty_or_worn_start':True, 'hands_on_restoration':True,
            'same_object_in_final':True, 'moving_footage':True,
            'target_seconds':45, 'segments':[
            {'stage':'before','start_seconds':0,'duration_seconds':4},
            {'stage':'process','start_seconds':5,'duration_seconds':34},
            {'stage':'after','start_seconds':52,'duration_seconds':7}],
        }

    def test_rejects_generic_workshop(self):
        self.assertFalse(style_bot.metadata_looks_like_restoration('https://pexels.com/video/a-man-working-in-factory-123/'))
        self.assertFalse(style_bot.metadata_looks_like_restoration('https://pexels.com/video/person-grinding-metal-123/'))
        self.assertTrue(style_bot.metadata_looks_like_restoration('https://pexels.com/video/restoring-rusty-iron-123/'))

    @patch('style_bot.bot.pexels_json')
    def test_only_relevant_candidates_with_review_gallery(self, client):
        client.return_value = {'videos':[
            {'id':1,'duration':60,'url':'https://pexels.com/video/restoring-rusty-iron-1/',
             'image':'https://images.pexels.com/x.jpg','video_files':[{'file_type':'video/mp4'}]},
            {'id':2,'duration':48,'url':'https://pexels.com/video/person-wiping-a-metal-2/',
             'video_files':[{'file_type':'video/mp4'}]},
            {'id':3,'duration':31,'url':'https://pexels.com/video/restoring-rusty-iron-3/',
             'video_files':[{'file_type':'video/mp4'}]},
        ]}
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'candidates.json'
            style_bot.discover(target)
            entries=json.loads(target.read_text())
            report=json.loads((target.parent/'review_report.json').read_text())
            gallery=(target.parent/'review_gallery.html').read_text()
        self.assertEqual([item['id'] for item in entries], [1])
        self.assertEqual(report['visually_verified'],0)
        self.assertIn('UNVERIFIED',gallery)
        self.assertEqual(client.call_count,len(style_bot.SEARCH_TERMS))

    def test_requires_same_object(self):
        self.manifest['same_object_in_final']=False
        with self.assertRaisesRegex(ValueError,'same_object_in_final'):
            style_bot.validate_manifest(self.manifest)

    def test_requires_hands_on_work(self):
        self.manifest['hands_on_restoration']=False
        with self.assertRaisesRegex(ValueError,'hands_on_restoration'):
            style_bot.validate_manifest(self.manifest)

    def test_requires_before_process_after(self):
        self.manifest['segments'][0]['stage']='process'
        with self.assertRaisesRegex(ValueError,'before -> process -> after'):
            style_bot.validate_manifest(self.manifest)

    def test_rejects_overlap(self):
        self.manifest['segments'][2]['start_seconds']=10
        with self.assertRaisesRegex(ValueError,'chronological'):
            style_bot.validate_manifest(self.manifest)

    def test_rejects_wrong_duration(self):
        self.manifest['segments'][1]['duration_seconds']=32
        with self.assertRaisesRegex(ValueError,'sum'):
            style_bot.validate_manifest(self.manifest)

    def test_montage_final_reveal(self):
        data=style_bot.validate_manifest(self.manifest)
        filter_string=style_bot.montage_filter(data['segments'])
        self.assertIn('trim=start=52:duration=7',filter_string)
        self.assertIn('concat=n=3:v=1:a=0',filter_string)
        self.assertIn('crop=1080:1920',filter_string)

if __name__=='__main__':
    unittest.main()
