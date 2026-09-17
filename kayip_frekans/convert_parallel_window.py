from __future__ import annotations
import argparse
from pathlib import Path
import torch
import openvoice_cli
from openvoice_cli.api import ToneColorConverter, OpenVoiceBaseClass
from openvoice_cli.downloader import download_checkpoint
import cloud_v3 as v3
import cloud_v4 as v4

parser = argparse.ArgumentParser()
parser.add_argument('--index', type=int, required=True)
parser.add_argument('--count', type=int, default=6)
parser.add_argument('--overlap', type=float, default=0.4)
args = parser.parse_args()

OUT = Path('output')
source = OUT / 'narration-source.wav'
target = OUT / 'serkan-reference.mp3'
total = v4.seconds(source)
base = total / args.count
half = args.overlap / 2
start = max(0.0, args.index * base - (half if args.index > 0 else 0.0))
end = min(total, (args.index + 1) * base + (half if args.index < args.count - 1 else 0.0))
duration = end - start
chunk_src = OUT / f'window-source-{args.index}.wav'
chunk_out = OUT / f'conv-{args.index}.wav'
v3.bot.run('ffmpeg','-v','error','-y','-ss',f'{start:.6f}','-t',f'{duration:.6f}','-i',source,'-ac','1','-ar','24000',chunk_src)

pkg = Path(openvoice_cli.__file__).resolve().parent
checkpoint_dir = pkg / 'checkpoints' / 'converter'
checkpoint_dir.mkdir(parents=True, exist_ok=True)
config = checkpoint_dir / 'config.json'
checkpoint = checkpoint_dir / 'checkpoint.pth'
if not config.exists() or not checkpoint.exists():
    download_checkpoint(str(checkpoint_dir))

# Aynı kaynak speaker embedding bütün pencerelerde kullanılır; ton değişimi önlenir.
source_seed = OUT / 'source-speaker-seed.wav'
target_seed = OUT / 'serkan-speaker-seed.wav'
v3.bot.run('ffmpeg','-v','error','-y','-i',source,'-t','20','-ac','1',source_seed)
v3.bot.run('ffmpeg','-v','error','-y','-i',target,'-ac','1',target_seed)

torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
converter = ToneColorConverter.__new__(ToneColorConverter)
OpenVoiceBaseClass.__init__(converter, str(config), device='cpu')
converter.watermark_model = None
converter.version = getattr(converter.hps, '_version_', 'v1')
converter.load_ckpt(str(checkpoint))
src_se = converter.extract_se(str(source_seed))
tgt_se = converter.extract_se(str(target_seed))
converter.convert(audio_src_path=str(chunk_src), src_se=src_se, tgt_se=tgt_se,
                  output_path=str(chunk_out), tau=0.3, message='KAYIPF')
if not chunk_out.exists() or chunk_out.stat().st_size < 100000:
    raise ValueError(f'Dönüşüm penceresi {args.index} oluşmadı.')
print(f'Pencere {args.index+1}/{args.count}: {start:.2f}-{end:.2f}s -> {v4.seconds(chunk_out):.2f}s')
