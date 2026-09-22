import unittest
from test_open_gen import config, find_video_url

class SafetyTests(unittest.TestCase):
    def test_preview_requires_no_key(self):
        config('preview', False, 0, '')

    def test_ai_requires_explicit_opt_in(self):
        for allow,cap,key in [(False,1,'key'),(True,0,'key'),(True,1,'')]:
            with self.subTest(allow=allow,cap=cap,key=bool(key)):
                with self.assertRaises(ValueError):
                    config('ai',allow,cap,key)

    def test_video_url_shapes(self):
        self.assertEqual(find_video_url({'outputs':['https://example.com/v.mp4']}),'https://example.com/v.mp4')
        self.assertEqual(find_video_url({'outputs':[{'url':'https://example.com/v.mp4'}]}),'https://example.com/v.mp4')

if __name__ == '__main__':
    unittest.main()
