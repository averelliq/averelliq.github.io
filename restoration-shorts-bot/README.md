# Restoration Shorts — rusty-iron example style (v2)

The target is the **user-supplied rusty iron restoration example**: show the old/rusted object immediately, moving close-up footage of real rust removal and hands-on repair, and a clear final reveal of the SAME object (preferably in use). Merely wiping metal, fixing a clock, a workshop scene, unrelated B-roll or a photo slideshow are **not** suitable.

## GitHub/browser workflow

The runnable files are at repository root `.github/workflows/restoration-discover.yml` and `.github/workflows/restoration-render.yml`. This folder adds `style_bot.py`; the legacy `bot.py` is left intact for compatibility. Existing KAYIP FREKANS and global Shorts workflows are unchanged. The new workflow uses the existing same-repository `PEXELS_API_KEY` *name*; it does not access or print the key.

1. In GitHub **Actions → Restoration Shorts - Example-style discovery**, run the workflow (it also searches daily). Download the `restoration-example-style-candidates` artifact: `review_gallery.html` is a clickable preview gallery; `candidates.json` has original Pexels links and IDs; `review_report.json` states counts and uncertainty.
2. Search terms focus on rusty tools, antique irons, axes, knives and restoration. An API result is retained only when its URL metadata **also** contains a restoration-related word and a worn-object/object word; generic metal grinding, workshop and clock-repair results without restoration metadata are excluded. The source may be 45–240 seconds to preserve the final reveal while editing a 40–50-second Short. **Metadata cannot confirm the video really matches the example. If there are zero candidates, the report honestly says zero.**
3. Watch the ENTIRE source video and check: worn/rusty starting object; moving hands-on restoration; SAME object in the final reveal; clean footage; permitted reuse and credits. No automated computer-vision confirmation is claimed. Pexels footage is not automatically suitable for monetization merely because narration is replaced.
4. Copy `examples/manifest.example.json` to `approved/my-restoration.json`, replace the intentionally invalid video ID `0` with a real approved Pexels ID, write only truly observed English steps, and enter verified chronological `segments`: 2–8s `before`, one or more `process` clips, 3–12s `after`. Their lengths must total the target (40–50s), must not overlap, and must fit the source footage. Only set the review flags true after checking.
5. In **Actions → Restoration Shorts - Render reviewed example-style footage**, use manifest `approved/my-restoration.json`, leaving `upload_private=false` to inspect `restoration-example-style-preview`. The renderer joins the verified beginning, process and final in 1080×1920, removes separate source audio/subtitle streams, generates fresh English voiceover and checks duration/audio. It cannot remove text burned into video or guarantee ideal cropping on every object.
6. An optional `upload_private=true` uploads **PRIVATE** via existing same-repository `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`, if present and authorized for the intended channel. No automatic public posting. The GitHub connector cannot inspect OAuth secrets, permissions or target channel; no credentials have been copied. The user should review the private video before publishing.

This project searches licensed Pexels footage rather than downloading and reuploading random YouTube videos. Real rights review remains necessary. These rules were unit-tested with mocked API results; a successful Pexels or YouTube production run must be checked separately.

Tests: `cd restoration-shorts-bot && python -m unittest discover -s tests -v`.

References: https://www.pexels.com/api/documentation/ · https://www.pexels.com/license/ · https://support.google.com/youtube/answer/1311392
