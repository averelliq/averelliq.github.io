# Restoration Shorts Bot — review-first prototype

A browser-driven GitHub Actions workflow to discover licensed restoration footage, create English narration and render vertical Shorts. **No automatic public uploads.** This bot lives in a separate folder on an isolated branch; the existing `main` branch is unchanged.

## How it works

1. Get a free Pexels API key at https://www.pexels.com/api/ and store it in GitHub Actions secrets as `PEXELS_API_KEY`.
2. Run `Discover licensed footage` to generate a `candidates.json` artifact. Watch candidate clips and check that they show genuine restoration, a before/after, and clean footage with no burned-in text/watermarks.
3. Copy `examples/manifest.example.json` to `approved/my-restoration.json` and fill in the REAL video ID and 3–6 observed English steps; set the review flags truthfully. The supplied example deliberately cannot be rendered without editing.
4. Run `Render approved restoration Short`, entering `approved/my-restoration.json` as the manifest input. The MP4, script and source attribution appear in the `restoration-preview` artifact. It is 1080×1920 and 40–50 seconds, with original sound and separate subtitle tracks excluded.
5. You can optionally upload **privately** after configuring OAuth GitHub secrets `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, and `YT_REFRESH_TOKEN`, and checking `upload_private`. This requires YouTube Data API v3 OAuth authorization, not an API key. Do not share or commit tokens.

The voice uses Edge TTS; service availability can change. Pexels discovery does not itself verify video relevance, embedded captions or before/after. This version therefore **does not autonomously verify footage, remove hardcoded captions, or upload publicly**. Adding English narration alone does not guarantee monetization. Unverified new YouTube API projects may have private-only upload restrictions.

## Local tests (optional)

`python -m unittest discover -s tests -v`

## Reference policies and API

- https://www.pexels.com/api/documentation/
- https://www.pexels.com/license/
- https://support.google.com/youtube/answer/1311392
- https://developers.google.com/youtube/v3/docs/videos/insert
