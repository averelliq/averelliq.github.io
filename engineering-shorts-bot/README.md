# Engineering Shorts Bot V2 — GitHub Actions + Remotion

**Status:** V2 jet-engine test rendered on GitHub Actions on 21 September 2026 (run 35583197106). The MP4 passed resolution, audio, duration and automated black-frame checks. The engineering animation is still illustrative, not photorealistic footage or a verified CAD model. No YouTube upload is configured.

The project lives only in `engineering-shorts-bot/` and `.github/workflows/engineering-shorts.yml`; existing bots and website content are unchanged.

## Generate a Short without your computer
1. Open **Actions → Engineering Shorts - Render MP4 → Run workflow**.
2. Choose `jet`, `tunnel`, `space`, `submarine`, `crane`, `recorder`, or `auto`, then start the run.
3. When the run finishes, open its **Artifacts** section, download `engineering-short-...`, unzip it and review `engineering-short.mp4`.
4. Upload to YouTube manually **only after** you are satisfied with the image, spoken English, and technical facts.

`auto` rotates through six curated topics by UTC date. It does NOT discover new internet topics. Pull requests and main-branch code changes trigger CI tests, but routine production is manual. GitHub's included compute and artifact storage are subject to account limits and platform rules.

## What V2 improves
- Dedicated, layered, animated **2D turbofan cutaway** for the `jet` topic, with stage-specific fan, bypass/core airflow, compressor stages, combustor, turbine, connecting shaft and exhaust emphasis.
- Bigger portrait diagram, tighter spacing and larger five-word English subtitle chunks.
- Removed per-scene opacity fades that introduced a completely dark frame at cuts in an early V2 test.
- Added full-video FFmpeg screening for black frames, alongside 1080×1920, audio-track and 40–95-second duration checks.
- Retained topic-specific schematic graphics for the five other curated engineering topics and offline Piper English speech.

## Boundaries
There is NO automatic sourcing of footage, no truly photorealistic or mechanically validated 3D model, no novel AI subject research, no word-level forced subtitle alignment, no automatic YouTube upload, and no guarantee that Piper sounds like a human. The visual geometry is a teaching illustration, not engineering documentation. Black-frame checks do not establish visual quality or audience retention. Verify voice-model licensing before commercial publication.

## Optional local use
Node.js 22+, Python 3.11, FFmpeg, `pip install piper-tts==1.3.0`, and Piper `en_US-ryan-medium.onnx` plus its `.json` configuration in `voices/` are required.

```bash
cd engineering-shorts-bot
npm install
python scripts/voice.py --topic jet
npm run render
npm run check
```

Outputs are available as GitHub Actions artifacts for 7 days. No paid AI APIs, YouTube credentials or repository secrets are required by this workflow.
