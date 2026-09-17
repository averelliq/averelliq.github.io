import unittest
import tempfile
from pathlib import Path
import numpy as np
import audio_quality_v5 as aq
from visual_balance_v5 import balance


class AudioQualityV5Tests(unittest.TestCase):
    def test_pause_timeline_and_speech_integrity(self):
        sr=24000
        t=np.arange(int(.5*sr))/sr
        spoken=np.rint(8000*np.sin(2*np.pi*160*t)).astype(np.int16)
        audio=np.r_[spoken,np.zeros(int(1.55*sr),np.int16),spoken]
        cuts,pauses=aq.detect(audio,sr,max_pause=.9,threshold=.003)
        self.assertEqual(len(cuts),1)
        fixed=aq.splice(audio,cuts,sr)
        mapping=aq.Timeline(cuts,sr)
        self.assertAlmostEqual(mapping.map(len(audio)/sr),len(fixed)/sr,places=4)
        self.assertGreater(len(audio)-len(fixed),.5*sr)
        self.assertTrue(np.array_equal(fixed[:int(.48*sr)],audio[:int(.48*sr)]))
        self.assertTrue(np.array_equal(fixed[-int(.48*sr):],audio[-int(.48*sr):]))

    def test_exact_subtitle_retiming(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'captions.srt'
            file.write_text('1\n00:00:00,100 --> 00:00:00,400\nMerhaba\n\n2\n00:00:02,050 --> 00:00:02,350\nDünya\n',encoding='utf-8')
            mapping=aq.Timeline([(24000,36000)],24000)
            self.assertEqual(aq.retime_srt(file,mapping,3),2)
            self.assertIn('00:00:01,550 --> 00:00:01,850',file.read_text(encoding='utf-8'))

    def test_visual_repetition_control(self):
        scenes=[{'text':'Kapıyı açtım. Koridordaki ses beni yatağın yanına götürdü. Kapıya dönüp pencereden baktım.','kind':'door'} for _ in range(20)]
        counts=balance(scenes)
        self.assertLessEqual(counts.get('door',0),10)
        self.assertEqual(sum(counts.values()),20)


if __name__=='__main__':
    unittest.main()
