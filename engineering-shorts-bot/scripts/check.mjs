import {readFileSync, existsSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
const topics = JSON.parse(readFileSync('src/topics.json', 'utf8'));
if (topics.length !== 6 || new Set(topics.map(t => t.id)).size !== 6) throw Error('Expected 6 unique topics');
for (const topic of topics) {
  if (!topic.title || !Array.isArray(topic.scenes) || topic.scenes.length < 5 || topic.scenes.some(s => !s.line || !s.part || !s.label)) throw Error(`Incomplete topic: ${topic.id}`);
}
console.log('Topic bank OK: six distinct topics with narrated scenes.');
if (existsSync('out/engineering-short.mp4')) {
  const data = JSON.parse(execFileSync('ffprobe', ['-v','error','-show_entries','stream=codec_type,width,height','-show_entries','format=duration','-of','json','out/engineering-short.mp4'], {encoding:'utf8'}));
  const video = data.streams.find(s => s.codec_type === 'video');
  const audio = data.streams.find(s => s.codec_type === 'audio');
  const duration = Number(data.format.duration);
  console.log(`MP4 properties: ${video?.width || '?'}x${video?.height || '?'}, audio=${Boolean(audio)}, duration=${duration.toFixed(2)}s`);
  if (video?.width !== 1080 || video?.height !== 1920 || !audio || duration < 40 || duration > 95) throw Error('Render QA failed: require 1080x1920, audio and 40-95 seconds. Review the MP4 artifact.');
  console.log('Render technical QA OK. This does not verify visual quality or factual accuracy.');
} else {
  console.log('No MP4 found: video-level QA not yet performed.');
}
