"""Expand the stock search *without* bypassing real-footage or relevance QC.

A scene that fails on page one gets two more result pages with the same
approved scene-specific searches. Every candidate still passes original source
resolution, frame-by-frame relevance, real-camera, and uniqueness checks.
"""
from __future__ import annotations

import requests

import quality_entry
import selection_guard
import upgrade


class FootageExhausted(Exception):
    pass


_installed = False


def install() -> None:
    global _installed
    if _installed:
        return
    original_choose = selection_guard.choose
    original_get = requests.get

    def choose_with_more_pages(scene, index):
        failures = []
        for page in (1, 2, 3):
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
                    print(f"Recovered matching HD footage for scene {index + 1} from Pexels results page {page}", flush=True)
                return result
            except FootageExhausted as exc:
                failures.append(str(exc)[:480])
                if page != 3:
                    print(f"Scene {index + 1}: no approved HD clip on results page {page}; checking page {page + 1}", flush=True)
            finally:
                requests.get = prior_get
                upgrade.bot.die = prior_die
        upgrade.bot.die(
            f"Scene {index + 1}: no genuinely matching HD camera footage after "
            "three stock result pages; upload cancelled. " + " | ".join(failures[-2:])[:980]
        )
        raise AssertionError("unreachable")

    # quality_entry installs the selection function into this slot at import.
    # Replace only that slot, retaining every other validation and upload gate.
    quality_entry.upgrade.matched_pexels_video = choose_with_more_pages
    _installed = True
