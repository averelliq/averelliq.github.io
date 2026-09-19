"""Recover from occasional malformed Gemini JSON without accepting invalid scripts.

Only malformed structured-output responses are retried. Model rejection,
credentials, quota, and factual/visual quality gates remain authoritative.
"""
from __future__ import annotations

import time

import quality_entry
import upgrade


class MalformedModelJSON(Exception):
    pass


_installed = False


def install() -> None:
    global _installed
    if _installed:
        return
    previous_model = quality_entry._original_model_json

    def model_with_json_retry(prompt: str):
        last_error = ""
        for attempt in range(3):
            previous_die = upgrade.bot.die

            def intercept_die(message: str, code: int = 1):
                if isinstance(message, str) and message.startswith(
                    "Gemini produced invalid structured output:"
                ):
                    raise MalformedModelJSON(message)
                return previous_die(message, code)

            upgrade.bot.die = intercept_die
            try:
                instruction = "" if attempt == 0 else (
                    "\nJSON FORMAT RETRY: The preceding response was not parseable. "
                    "Generate the entire answer afresh as ONE compact valid JSON "
                    "object, with all required fields and 7-9 scenes. Use short, "
                    "plain English values, properly escaped quotation marks, "
                    "no markdown, no trailing commas, and finish all brackets. "
                    "Never relax script, factual or visual requirements."
                )
                return previous_model(prompt + instruction)
            except MalformedModelJSON as exc:
                last_error = str(exc)[:220]
                print(
                    f"Malformed Gemini JSON; safe regeneration {attempt + 1}/3. "
                    "No video will be uploaded from an invalid response.",
                    flush=True,
                )
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
            finally:
                upgrade.bot.die = previous_die
        # During the existing five-draft editorial loop this specific message
        # becomes a rejected draft, NOT a successful or silently skipped review.
        upgrade.bot.die(
            "Two generated plans failed structural quality checks: "
            "Gemini returned invalid JSON after three regenerations; " + last_error
        )
        raise AssertionError("unreachable")

    quality_entry._original_model_json = model_with_json_retry
    upgrade.model_json = model_with_json_retry
    _installed = True
