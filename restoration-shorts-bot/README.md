# Restoration Shorts Bot — review-first prototype

A browser-driven GitHub Actions workflow to discover licensed restoration footage, create English narration and render vertical Shorts. **No automatic public uploads.** This bot is staged in a separate folder on an isolated branch; the existing `main` branch is unchanged.

**Important:** Workflows inside this folder are staged source files, NOT active GitHub Actions in the existing website repository. To run them, create a NEW GitHub repository and upload the CONTENTS of `restoration-shorts-bot` to the root of that new repository (or use the ZIP provided in chat). The new repository's default branch must include `.github/workflows/*.yml` at its ROOT. No video has been made or uploaded yet.

## Browser-only setup

1. Get a free Pexels API key at https://www.pexels.com/api/ and save it at new repository **Settings → Secrets and variables → Actions** as `PEXELS_API_KEY`.
2. Run **Actions → Discover licensed footage → Run workflow**. Download `review-candidates`, watch the proposed clips and verify actual restoration, visible before/after, the Pexels source and NO burned-in captions/watermark.
3. Copy `examples/manifest.example.json` to `approved/my-restoration.json` in your new repository. Replace the intentionally invalid ID `0` with a REAL Pexels video ID, describe 3–6 visible steps accurately in English, and truthfully set all the review flags.
4. Run **Render approved restoration Short** with manifest `approved/my-restoration.json`. Leave `upload_private` off to review the exported 1080×1920, 40–50-second MP4, script and source attribution first.
5. To upload privately, configure Google Cloud YouTube Data API v3 OAuth and add `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` as encrypted GitHub Actions secrets. Run with `upload_private=true`. This uploads **private**, not public. Never share or commit tokens.

The voice uses Edge TTS; service availability can change. Pexels search results are not guaranteed to show actual before/after restoration. No autonomous visual verification or reliable embedded-caption removal exists in this prototype. Original audio and separate subtitle streams ARE excluded. Adding English narration alone does not guarantee monetization. Unverified new YouTube API projects may have private-only upload restrictions.

Local optional tests: `python -m unittest discover -s tests -v`.

Sources: https://www.pexels.com/api/documentation/ · https://www.pexels.com/license/ · https://support.google.com/youtube/answer/1311392 · https://developers.google.com/youtube/v3/docs/videos/insert
