# Engineering Shorts Bot V1 — GitHub Actions + Remotion

**Status:** GitHub Actions proof-of-concept successfully rendered and technically checked a jet-engine MP4 on 21 September 2026 (PR run 35581453237). No YouTube upload is configured; the video has not been manually reviewed for visual quality or voice naturalness.

This bot lives only in `engineering-shorts-bot/` and `.github/workflows/engineering-shorts.yml` in the existing repository. Other site content and existing bots are unchanged.

## Start from GitHub — no computer installation needed
1. Open the repository **Actions** tab, then select **Engineering Shorts - Render MP4**.
2. Click **Run workflow**, choose a topic (`jet`, `tunnel`, `space`, `submarine`, `crane`, `recorder`, or `auto`) and click the green Run workflow button.
3. Open the completed run. Under **Artifacts**, download `engineering-short-...`; unzip and open `engineering-short.mp4`.
4. Inspect the video and voice. Publish manually only after you approve the actual content.

`auto` rotates across the six fixed topics using UTC date; it does **not** discover new topics on the internet. A test also runs automatically when this bot is updated by a pull request or merged to main. Routine video production is started manually. No YouTube account permissions, API keys or secrets are required.

## Implemented features and limits
- Six carefully written, predefined English explanatory topics and a basic `auto` topic rotation.
- Piper's locally executed en_US-ryan-medium English synthetic narration (downloaded by the GitHub runner), with narrated scenes and animated English text.
- Remotion vector diagrams with some rotating/moving schematic parts, at 1080 × 1920, 30 FPS, encoded as H.264 MP4 with voice audio.
- Technical validation of dimensions, an audio stream, and a 40–95-second duration. Video files are saved as a GitHub Artifact even if technical QA fails, where possible. Artifacts expire after 7 days.
- GitHub-hosted rendering with no need to keep your Windows computer switched on.

**Not implemented:** real stock-footage discovery, AI-generated photorealistic footage, complex accurate 3D mechanical simulation, live AI topic discovery, automatic YouTube publishing, or guaranteed natural humanlike voice. These are schematic animated explanations, not real manufacturing footage. Technical QA does not verify the appearance, factual accuracy, music, perceived quality, or audience retention. Watch each output before publishing. Check the Piper voice model license/card before commercial use.

## Optional local development
Requires Node.js 22+, Python 3.11, FFmpeg, `pip install piper-tts==1.3.0`, plus `en_US-ryan-medium.onnx` and its `.json` voice config from the `rhasspy/piper-voices` v1.0.0 repository placed in `voices/`.

```bash
cd engineering-shorts-bot
npm install
python scripts/voice.py --topic jet
npm run render
npm run check
```

## Cost and safety
The workflow uses no paid AI APIs and never uploads to YouTube. GitHub usage/storage limits and future pricing changes may apply. The GitHub workflow uses read-only repository permissions and retains video artifacts for 7 days. No secrets are stored in this repository.
