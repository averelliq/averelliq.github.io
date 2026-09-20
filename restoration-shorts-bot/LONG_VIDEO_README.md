# Restoration Shorts — long video to 60-second Short

**Installed GitHub Actions workflow:** [Full video to 60 seconds](../../actions/workflows/restoration-long-to-short.yml). The [setup self-test](../../actions/workflows/restoration-self-test.yml) checks source compilation, timeline logic and FFmpeg. This workflow does **not** publish videos to YouTube.

## Minimal-effort handoff

Give the assistant a **directly downloadable, public HTTPS MP4 URL** and permission to use that footage. The assistant can create a GitHub Issue on your behalf titled `RESTORATION VIDEO: <description>` with a line `VIDEO_URL=https://...`; an owner-created Issue automatically starts the workflow. A normal YouTube watch link or a Drive webpage is NOT a direct MP4 URL. The user need not open Actions or create a release for the direct-URL route. GitHub Issues, run logs and artifacts in this repository are public: **do not use private, confidential or unlicensed footage or private/tokenized URLs.** The assistant's available GitHub connector cannot upload an MP4 attachment or create a GitHub Release asset directly. Receiving a video in chat does not automatically put it on GitHub; do not claim otherwise.

## Alternative: upload in the browser

On [Releases](https://github.com/averelliq/averelliq.github.io/releases/new), create a release with a tag beginning `restoration-input-`, attach one source MP4, then publish. This starts the same workflow. A Release asset must be under 2 GiB. To use an exact narration or subtitle box, manually run [the workflow](../../actions/workflows/restoration-long-to-short.yml) using either `source_url` (direct HTTPS video) or `release_tag`, not both. MP4 and `report.json` are saved to the Actions run's artifact for seven days.

## What is actually implemented

1. Validate the input video's streams, duration and requested optional text rectangle.
2. Speed up the **entire source from beginning to end**, preserving chronological order; a 600-second source becomes about 59.9 seconds. Frame dropping is unavoidable when accelerating.
3. Produce 1080 × 1920, 30-fps MP4 with the whole frame fitted over a blurred background.
4. Remove all source audio (including speech, music AND original tool sounds) and separate subtitle tracks. There is currently **no clean separation of tool sounds from overlapping speech**.
5. Generate English narration with network-dependent free `edge-tts` and add spoken and visual LIKE + SUBSCRIBE. The default narration is generic; it cannot recognize and accurately narrate specific repair steps without a video-specific script.
6. Verify final duration, streams and resolution and save a JSON report showing each stage.

**Burned-in text** cannot be automatically and perfectly removed. The optional `subtitle_box` applies approximate `delogo` to a fixed source-pixel rectangle; this can smear the image. Moving text, logos or text covering the restored object require careful manual editing. Free hosted runners and the voice service are subject to their providers' terms and availability. Source licensing is the user's responsibility, and a different edit/voice does not itself grant reuse rights.

## Testing

`python -m unittest discover -s restoration-shorts-bot/tests -p 'test_long_to_short.py' -v`

Synthetic rendering previously passed with stand-in audio, but a **real 10-minute video plus live English TTS has not yet been verified end to end**. The GitHub setup self-test is separate from a real video render.
