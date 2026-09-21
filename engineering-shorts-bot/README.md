# Engineering Shorts Bot V1 — GitHub Actions + Remotion

**Status:** code prototype. No render has been confirmed on GitHub yet. No YouTube upload is configured.

This project lives at `engineering-shorts-bot/` in the existing GitHub repository. Its workflow lives at the repository-root `.github/workflows/engineering-shorts.yml`. Existing website files and bots are untouched.

## Start from GitHub (computer can be off)
1. Merge the prepared branch into the repository's default branch after review; GitHub requires `workflow_dispatch` workflows to be on the default branch.
2. Open **Actions → Engineering Shorts - Render MP4 → Run workflow**.
3. Select `jet`, `tunnel`, `space`, `submarine`, `crane`, `recorder`, or `auto` (rotates over six curated topics by UTC date).
4. When the run finishes, download the `engineering-short-...` artifact ZIP, review the MP4, and publish manually only if acceptable.

## What is really implemented
- Six fact-oriented, human-curated English scripts; **not** live AI research or generative footage.
- Offline Piper English narration, six narrated sections, dynamic motion-graphics diagrams.
- 1080×1920 / 30fps Remotion video; English animated captions; MP4 with voice audio.
- A technical QA step validates dimensions, audio presence, and 30–95-second duration. It does **not** prove mechanical accuracy, naturalness, copyright clearance, or retention.
- No copyrighted stock footage, external videos, auto YouTube posting, or secret keys are needed.

**Important:** The output is an animated, illustrative engineering explainer—not photorealistic video, a 3D simulation, or guaranteed human-sounding audio. The Piper Ryan voice may not meet your desired naturalness; listen before publishing. Piper voice model is downloaded at runtime, never committed. Check model card and license before commercial use.

## Local usage (optional)
Requires Node.js 22+, Python 3.11, ffmpeg, `pip install piper-tts==1.3.0`; download `en_US-ryan-medium.onnx` and corresponding `.json` from rhasspy/piper-voices v1.0.0 into `voices/`.

```bash
npm install
python scripts/voice.py --topic jet
npm run render
npm run check
```

## Publishing and cost guardrails
Runs are manually triggered only, with `contents: read`; no YouTube credentials or automated publication. Public repo standard GitHub-hosted runner time is normally free subject to GitHub usage rules, but artifact storage and platform changes can matter. The workflow keeps output for 7 days.
