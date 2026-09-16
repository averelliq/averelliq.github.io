# Enable original Shorts topic discovery (fix 403)

The existing `YT_REFRESH_TOKEN` is an **upload credential**. It uploaded Shorts successfully, but the public YouTube `search.list` request returned **HTTP 403**. `GEMINI_API_KEY` was also tested and returned **HTTP 401** on the YouTube endpoint. They are not interchangeable with a dedicated YouTube Data API key. No credential is stored in repository code.

**One-time setup (Google account owner):**

1. Open https://console.cloud.google.com/apis/library/youtube.googleapis.com and select the Google Cloud project you want to use for the YouTube Data API. Click **Enable** if the API is not enabled.
2. Open https://console.cloud.google.com/apis/credentials and select **Create credentials > API key**, or use an existing key for that project. Restrict the key's **API restrictions** to **YouTube Data API v3**. A rotating GitHub-hosted runner generally cannot use a fixed IP-address restriction; don't select a browser HTTP-referrer restriction for this server-side bot. Consult Google Cloud's security guidance before deploying in production.
3. Open https://github.com/averelliq/averelliq.github.io/settings/secrets/actions and choose **New repository secret**. Name it **`YT_DATA_API_KEY`** (exact spelling); paste the key as the secret **value** and save. **Never** paste this key in a chat, issue, commit, workflow file, or screenshot.
4. To verify, open https://github.com/averelliq/averelliq.github.io/actions/workflows/global-shorts.yml and run **Run workflow**, with **smoke_test = true**. This generates a draft but does **not** upload it to YouTube. The log should include `TREND TOPIC:` when an eligible reference is found; `TREND: no suitable short-form topic` is also possible when the API works but no candidate passes filters. The `plan.json` artifact includes `trend_reference` only when the topic actually came from a public video.

The bot now uses **only** `YT_DATA_API_KEY` for public metadata discovery and always uses `YT_REFRESH_TOKEN` only for uploading its **original** video. When the key is absent or rejected, it logs a clear reason and retains the previous evergreen topic; it does not falsely claim trend inspiration or bypass the API.

A valid key does not guarantee any video will go viral. Our current metadata search looks for recent short-form videos (12–60 s), not a definitive Shorts classification. YouTube search is quota-limited; monitor https://console.cloud.google.com/apis/dashboard and follow https://developers.google.com/youtube/v3/docs/errors for reason-specific errors such as `quotaExceeded` and `accessNotConfigured`.
