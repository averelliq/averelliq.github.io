# What If AI — cloud-only GitHub test (review only)

This **separate bot module** is for the English global science / What If Shorts channel. It does not touch existing shorts, fox, engineering, restoration or Kayıp Frekans workflows. Nothing runs on a user's PC; GitHub Actions runs it on a cloud-hosted standard CPU runner. No n8n and no YouTube upload.

## Browser-only test

Open the repo's **Actions → What If AI - cloud test (review only) → Run workflow** and leave defaults (`mode=preview`, `allow_credit_use=false`, `max_usd=0`). After a green run, open **Artifacts → whatif-ai-5s-review** for `test_5s.mp4`, `report.json` and `prompt.txt`. This free preview is a *moving 2D illustration made with Pillow + FFmpeg*, **not** an Open Generative AI / AI-video result. It only tests GitHub cloud rendering and 9:16 output. The initial workflow file addition also triggers one preview run via a narrowly path-scoped push trigger.

## Real Open Generative AI backend test (NOT automatically free)

The open-source Open Generative AI project routes its cloud video models through MuAPI. The 5-second test uses its documented `wan2.2-text-to-video` endpoint at 9:16 and 720p (no fake 1080p-native claims). MuAPI deducts credits for generation, including trial credits. To use it, add your own `MUAPI_API_KEY` as a **GitHub Actions repository secret**, never in code, and manually run with `mode=ai`, `allow_credit_use=true` and an estimated cost cap greater than zero (for example, `0.50`). The bot requests the official cost estimate and **refuses to submit** if the estimate is unavailable or exceeds the cap. This cap only controls this one job, not provider/account spending outside the job. Provider prices and credits may change; the bot cannot promise a zero-cost AI clip. If you want strictly free forever, use `preview` and do not opt in to `ai`.

The source is a test harness for Open Generative AI's documented provider API, **not a full local fork of its application**; no hosted GPU is included. The desktop's Wan2GP server is a separate GPU process and is not available on the standard GitHub Actions runner. Real AI output is not guaranteed to meet art direction; check the resulting MP4 manually. A finished 45-second episode, narration, automatic topic selection, YouTube authentication and publishing are deliberately not implemented in this test stage.

## Safety and video QC

Preview on scoped push, otherwise manual trigger only; `permissions: contents: read`; no channel upload, no billing top-up; GitHub artifact retention 3 days. It verifies a real MP4 video stream, 9:16 aspect ratio and minimum file size. Upscaling the free CPU preview to 1080×1920 does not add source detail. The AI model produces up to its requested 720p; quality depends on its output. Follow media/model license and platform policies before eventual publishing.

Sources: https://github.com/Anil-matcha/Open-Generative-AI ; https://muapi.ai/docs/pricing ; https://muapi.ai/playground/wan2.2-text-to-video/api ; https://docs.github.com/en/actions/reference/runners/github-hosted-runners
