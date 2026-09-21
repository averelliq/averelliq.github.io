import {readFileSync, existsSync} from 'node:fs';
import {execFileSync, spawnSync} from 'node:child_process';
const topics = JSON.parse(readFileSync('src/topics.json', 'utf8'));
if (topics.length !== 6 || new Set(topics.map(t => t.id)).size !== 6) throw Error('Expected 6 unique topics');
for (const topic of topics) {
  if (!topic.title || !Array.isArray(topic.scenes) || topic.scenes.length < 5 || topic.scenes.some(s => !s.line || !s.part || !s.label)) throw Error(`Incomplete topic: ${topic.id}`);
}
console.log('Topic bank OK: six distinct topics with narrated scenes.');
const path = 'out/engineering-short.mp4';
if (existsSync(path)) {
  const data = JSON.parse(execFileSync('ffprobe', ['-v','error','-show_entries','stream=codec_type,width,height','-show_entries','format=duration','-of','json',path], {encoding:'utf8'}));
  const video = data.streams.find(s => s.codec_type === 'video');
  const audio = data.streams.find(s => s.codec_type === 'audio');
  const duration = Number(data.format.duration);
  console.log(`MP4 properties: ${video?.width || '?'}x${video?.height || '?'}, audio=${Boolean(audio)}, duration=${duration.toFixed(2)}s`);
  if (video?.width !== 1080 || video?.height !== 1920 || !audio || duration < 40 || duration > 95) throw Error('Render QA failed: require 1080x1920, audio and 40-95 seconds.');
  // Detect even a single completely dark frame, including one at a scene boundary.
  // This scan is technical QA; it cannot judge narration, visuals or physics.
  const scan = spawnSync('ffmpeg', ['-hide_banner','-nostats','-loglevel','info','-i',path,'-vf','scale=90:160,blackdetect=d=0:pix_th=0.12:pic_th=0.96','-an','-f','null','-'], {encoding:'utf8', maxBuffer:4*1024*1024});
  if (scan.status !== 0) throw Error(`Black-frame scan failed: ${(scan.stderr||'').slice(-1200)}`);
  const black = [...(scan.stderr||'').matchAll(/black_start:([0-9.]+)/g)].map(x=>Number(x[1]));
  if (black.length) throw Error(`Render QA failed: dark frames near ${black.slice(0,12).map(x=>x.toFixed(2)).join(', ')}s`);
  console.log(`Render technical QA OK: audio, 1080x1920, ${duration.toFixed(1)}s, no detected black frames. Visual quality and factual accuracy require review.`);
} else {
  console.log('No MP4 found: video-level QA not yet performed.');
}
