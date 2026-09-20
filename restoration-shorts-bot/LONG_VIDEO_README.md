# Long restoration video → 60-second Short

**GitHub Actions workflow:** [Restoration Shorts - Full video to 60 seconds](../../actions/workflows/restoration-long-to-short.yml). It lives alongside the existing restoration code and does not replace other workflows. You need a video you are allowed to use; this tool does not grant reuse rights.

## Browser-only use (no PC installation)

1. Open the repo's **Releases → Draft a new release**: https://github.com/averelliq/averelliq.github.io/releases/new . Make a NEW tag whose name starts with `restoration-input-`, e.g. `restoration-input-001`; target the `main` branch.
2. Attach **one MP4 source video** to the release (drag/drop under *Attach binaries*). Wait for the upload to finish **before** pressing **Publish release**. An MP4 release asset must be less than 2 GiB. Do not commit a huge video to Git.
3. Publishing a release with that tag prefix starts the workflow automatically. Open [Actions](https://github.com/averelliq/averelliq.github.io/actions/workflows/restoration-long-to-short.yml), click its run and expand the numbered steps to see exactly which step passed or failed.
4. After a successful run, open **Artifacts → restoration-short-RUN_ID**. Download the ZIP; it contains `restoration_short.mp4` and `report.json` with original duration, speed factor, stage history and final dimensions. Artifacts are retained for **7 days**, so save the MP4 promptly.
5. For **an exact English script or an MP4 source with another extension**, run the workflow manually using **Actions → Restoration Shorts - Full video to 60 seconds → Run workflow**. Enter the existing `release_tag`, optionally an exact `video_asset` filename, a short **truthful** English narration, and an optional `subtitle_box`.

**IMPORTANT PRIVACY:** This is a PUBLIC GitHub repository. Uploaded release assets and workflow artifacts are visible to people who can read the repository. Do not upload confidential, personal, or otherwise non-public footage here. A private repo with a runner is needed for private footage; its GitHub Actions allowance is plan-dependent.

## Exactly what the bot does

- Probes duration/resolution first and rejects invalid files.
- Applies **one continuous speed-up from original start to original finish**: 600 seconds becomes **59.9 seconds** (about 10.02×). No shuffled stages, sampled still frames or stitched highlights. Accelerating necessarily drops some original frames.
- Creates a 1080×1920 MP4 at 30 fps. The original FULL picture fits in front of a blurred-fill background, preserving the subject without central cropping.
- Drops **all original audio** and separate subtitle streams (therefore source speech, music and even source tool noises are gone). It does NOT yet extract clean tool noises from overlapping speech. It does not create false tool noises.
- Synthesizes a general English narration using `edge-tts` (`en-US-AndrewNeural`) and a separate spoken like/subscribe reminder. This speech service is network-dependent and can occasionally fail; the bot reports failure instead of silently delivering a voiceless video. Its cost/access terms can change.
- Displays `LIKE + SUBSCRIBE` over the final seconds, mixes English narration/CTA, encodes and validates duration, audio and dimensions. Does **not** upload to YouTube automatically.

**Important about text already drawn into the picture:** FFmpeg can remove separate subtitle tracks, but burned-in subtitles/logos are video pixels. By default, the bot preserves the entire picture and **does not claim to remove those pixels**. If they stay in a fixed rectangle throughout the footage, provide `subtitle_box` in **original input pixels**, e.g. `120:940:840:90` for a 1080-wide source; the `delogo` approximation may visibly smear that area. If text moves, overlaps the object, or appears in multiple places, manual masking or a more capable inpainting model is necessary. Do not claim a pristine text-free output without watching the MP4.

**Narration scope:** The built-in English narration is deliberately generic because the workflow does not understand what object or repair is shown. For a factual step-by-step English explanation, supply a script based on actually watching your video in the manual workflow form. Keep it short enough to leave room for the final spoken CTA. Do not expect the bot to identify repair steps automatically.

## Tests and limits

`python -m unittest discover -s restoration-shorts-bot/tests -p 'test_long_to_short.py' -v`

A local synthetic-video smoke test exercised image processing and output validation with stand-in audio; it did **not** test live English speech synthesis or a real 10-minute input. The live GitHub run needs a source release asset and the voice service to be reachable. GitHub's standard hosted runners are free for **public** repositories, subject to GitHub's service limits; private repository quotas differ. Releases have an under-2-GiB per-asset limit. 

Official background: https://docs.github.com/en/actions/reference/runners/github-hosted-runners · https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
