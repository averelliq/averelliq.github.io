# Restoration Shorts Bot — review-first prototype

A browser-only GitHub Actions project for finding Pexels restoration footage, writing English narration and rendering vertical Shorts. It does **not** automatically publish publicly. No restoration video has yet been produced or uploaded.

## Reusing your existing GitHub connections

This bot is in the **same** `averelliq/averelliq.github.io` repository, on the isolated `restoration-shorts-bot-v1` branch. After the proposed change is merged to `main`, the workflows at `.github/workflows/restoration-discover.yml` and `.github/workflows/restoration-render.yml` will be visible in Actions. Existing workflows and `main` remain untouched until that happens.

The existing KAYIP FREKANS workflow already references `secrets.PEXELS_API_KEY`. Restoration discovery reuses that exact secret name. This proves the old workflow *references* the name, not that a working secret is currently present: this GitHub connection cannot inspect the secret store.

The rendering workflow references same-repository `secrets.YT_CLIENT_ID`, `secrets.YT_CLIENT_SECRET`, and `secrets.YT_REFRESH_TOKEN`. We cannot verify their presence, names, OAuth scope, or whether they point to the intended global Shorts channel. A credential configured only in another repository is not automatically shared. The existing Shorts workflow has an intentionally disabled YouTube publish step, so it is **not** evidence that OAuth is ready. No secrets have been copied, modified, printed or exposed.

## Workflow

1. Open **Actions → Restoration Shorts - Discover footage → Run workflow** (after merging to `main`). The workflow also searches once a day. It stores proposed 40–90-second Pexels footage in a `restoration-review-candidates` artifact.
2. Watch each candidate and confirm that the visuals show an actual restoration with before-and-after, clean source footage without embedded captions or watermarks, and acceptable reuse rights. Pexels metadata alone cannot verify these.
3. Add a truthful manifest inside `restoration-shorts-bot/approved/`, using `restoration-shorts-bot/examples/manifest.example.json` as a guide. Fill in a *real* video ID, observed English restoration steps, and required review flags. The example ID is deliberately invalid.
4. Run **Actions → Restoration Shorts - Render reviewed footage → Run workflow** with input `approved/my-restoration.json`. The MP4, narration script and source information appear in the `restoration-preview` artifact. The output target is 1080×1920, 40–50 seconds.
5. If same-repository YouTube OAuth credentials are confirmed to be valid for the *intended* channel, manually opt into `upload_private=true` to upload a **private** review video. The bot does not publish publicly.

The renderer removes original audio and separate subtitle streams by remapping only the selected video stream and new narration. It cannot reliably erase burned-in subtitles, nor autonomously verify the actions depicted. Edge TTS availability may change. English narration does not automatically make someone else's footage original for YouTube monetization.

Local optional tests: `cd restoration-shorts-bot && python -m unittest discover -s tests -v`.

Useful references: https://www.pexels.com/api/documentation/ · https://www.pexels.com/license/ · https://support.google.com/youtube/answer/1311392 · https://developers.google.com/youtube/v3/docs/videos/insert
