"""Find suitable real-camera stock without bypassing any scene-review gate.

Search more pages for each of the plan's approved queries. Permit genuine
Full HD source files up to 80 MiB (the earlier 35 MiB threshold excluded some
otherwise eligible originals); verify duration and review every candidate.
"""
from __future__ import annotations

from pathlib import Path

import requests

import quality_entry
import selection_guard
import upgrade
import visual_guard


class FootageExhausted(Exception):
    pass


_installed = False


def download_hd_original(link: str, target: Path) -> None:
    """Download a bounded Pexels original, still rejecting corrupt media."""
    if not isinstance(link, str) or not link.startswith("https://"):
        raise ValueError("Stock source URL must be HTTPS")
    with requests.get(link, stream=True, timeout=90) as response:
        response.raise_for_status()
        content_length = int(response.headers.get("Content-Length") or 0)
        limit = 80 * 1024 * 1024
        if content_length > limit:
            raise ValueError("Full HD stock source exceeds 80 MiB")
        total = 0
        with target.open("wb") as handle:
            for block in response.iter_content(chunk_size=1024 * 1024):
                if block:
                    total += len(block)
                    if total > limit:
                        raise ValueError("Full HD stock source exceeds 80 MiB")
                    handle.write(block)
    visual_guard._duration(target)


def install() -> None:
    global _installed
    if _installed:
        return
    original_choose = selection_guard.choose
    original_get = requests.get
    selection_guard._download = download_hd_original

    def choose_with_more_pages(scene, index):
        failures = []
        max_page = 5
        for page in range(1, max_page + 1):
            prior_die = upgrade.bot.die
            prior_get = requests.get

            def intercept_die(message: str, code: int = 1):
                if isinstance(message, str) and message.startswith(
                    f"No matching footage for scene {index + 1} after "
                ):
                    raise FootageExhausted(message)
                return prior_die(message, code)

            def page_search(url, *args, **kwargs):
                if url == "https://api.pexels.com/v1/videos/search":
                    params = dict(kwargs.get("params") or {})
                    params["page"] = page
                    kwargs["params"] = params
                return original_get(url, *args, **kwargs)

            upgrade.bot.die = intercept_die
            requests.get = page_search
            try:
                result = original_choose(scene, index)
                if page != 1:
                    print(
                        f"Recovered matching HD footage for scene {index + 1} "
                        f"from Pexels results page {page}", flush=True
                    )
                return result
            except FootageExhausted as exc:
                failures.append(str(exc)[:480])
                if page < max_page:
                    print(
                        f"Scene {index + 1}: no approved HD clip on results page "
                        f"{page}; checking page {page + 1}", flush=True
                    )
            finally:
                requests.get = prior_get
                upgrade.bot.die = prior_die
        upgrade.bot.die(
            f"Scene {index + 1}: no genuinely matching Full HD camera footage "
            f"after {max_page} stock result pages; upload cancelled. "
            + " | ".join(failures[-2:])[:980]
        )
        raise AssertionError("unreachable")

    quality_entry.upgrade.matched_pexels_video = choose_with_more_pages
    _installed = True
