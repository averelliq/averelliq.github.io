"""Quality-gated daily Shorts: original trend-inspired topic, safe visuals and sound."""
from __future__ import annotations

import os
import re

import upgrade
import visual_guard
import selection_guard
import trend_ideas

_original_run = upgrade.bot.run
_original_build = upgrade.aligned_build_video
_original_choose_topic = upgrade.choose_topic
_original_generate_plan = upgrade.generate_plan
_original_validate_plan = upgrade.validate_plan
_original_model_json = upgrade.model_json
_original_die = upgrade.bot.die


class DraftRejected(Exception):
    """Rejected factual or malformed draft, preserving actionable feedback."""


# Distinctive concrete subjects from other formats/topics. A video about soap
# bubbles must not silently switch to popcorn just because both things pop.
# Keep this guard deliberately conservative: reject clear subject words only;
# the independent editorial review handles more subtle narrative drift.
SUBJECT_FAMILIES = {
    "popcorn": {"popcorn", "kernel", "kernels"},
    "bread": {"bread", "dough", "yeast"},
    "soap": {"soap", "soapy", "suds", "bubble", "bubbles"},
    "banana": {"banana", "bananas"},
    "onion": {"onion", "onions"},
    "zipper": {"zipper", "zippers"},
    "penguin": {"penguin", "penguins"},
    "octopus": {"octopus", "octopuses", "octopi"},
    "bat": {"bat", "bats", "echolocation"},
    "spider": {"spider", "spiders", "webs"},
    "compass": {"compass", "compasses", "lodestone"},
}


def checked_validate_plan(plan, theme):
    checked = _original_validate_plan(plan, theme)
    topic = str(checked.get("topic") or "").lower()
    topic_words = set(re.findall(r"[a-z]+", topic))
    relevant_families = {
        name for name, terms in SUBJECT_FAMILIES.items()
        if name in topic_words or terms.intersection(topic_words)
    }
    # The generated plan has one exact topic, not a collection of unrelated
    # examples. Catch alien named subjects even when the other queries look apt.
    for index, scene in enumerate(checked["scenes"], 1):
        content = " ".join(str(scene.get(key, "")) for key in ("voiceover", "query", "caption"))
        content += " " + " ".join(str(q) for q in scene.get("backup_queries", []))
        words = set(re.findall(r"[a-z]+", content.lower()))
        for name, terms in SUBJECT_FAMILIES.items():
            if name not in relevant_families and terms.intersection(words):
                raise ValueError(
                    f"Scene {index} switched away from topic {topic!r} to unrelated "
                    f"subject {name!r}; regenerate the entire plan and its footage queries"
                )
    return checked


def safe_render(command: list[str]) -> None:
    command = list(command)
    if "-vf" in command:
        position = command.index("-vf") + 1
        if position < len(command) and command[position].startswith("subtitles="):
            command[position] = (command[position]
                                 .replace("FontSize=22", "FontSize=12")
                                 .replace("MarginV=260", "MarginV=70"))
            if "-c:a" in command and "-af" not in command:
                command[command.index("-c:a"):command.index("-c:a")] = [
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11"
                ]
    _original_run(command)


def trend_topic(theme: str) -> str:
    test_topic = os.getenv("SHORTS_TEST_TOPIC_OVERRIDE", "").strip()
    if test_topic and os.getenv("SHORTS_SKIP_UPLOAD") == "1":
        if not 8 <= len(test_topic) <= 90 or any(c in test_topic for c in "\r\n<>#"):
            _original_die("Invalid smoke-test subject")
        print(f"SMOKE TEST: testing visually accessible topic: {test_topic}", flush=True)
        return test_topic
    return trend_ideas.pick_topic(theme, _original_choose_topic, upgrade.model_json)


def trend_plan():
    feedback = ""
    for attempt in range(5):
        def reviewed_model_json(prompt: str):
            if prompt.startswith("You are an English-language, original educational Shorts scriptwriter."):
                prompt += (
                    "\nMANDATORY STRUCTURE: 7-9 scenes, exactly 75-90 narration words total, "
                    "7-10 words in the first sentence of scene one, 8-15 spoken words "
                    "per scene. The first sentence MUST end with a period, question "
                    "mark or exclamation point after 7-10 words. "
                    "Use two specific 2-5-word backup stock queries per scene. "
                    "MANDATORY TOPIC ISOLATION: All voiceovers, captions and visual "
                    "queries must describe ONLY the assigned topic. Never introduce "
                    "other objects or subjects from previous drafts, examples or "
                    "unrelated ideas. No popcorn or kernels in soap-bubble stories. "
                    "MANDATORY VISUAL FEASIBILITY: each stock video can visibly "
                    "show the narrated subject. Avoid internal anatomy, microscopic "
                    "processes and unfilmable historical recreations. Explain unseen "
                    "mechanisms without claiming footage depicts them. "
                    "Keep every factual claim accurate."
                )
                if feedback:
                    prompt += ("\nPREVIOUS DRAFT WAS REJECTED FOR THIS SPECIFIC ISSUE: "
                               + feedback + "\nGenerate a corrected NEW full JSON plan, "
                               "especially fixing the exact rejected constraint. "
                               "Do not repeat the rejected claim or malformed structure.")
            return _original_model_json(prompt)

        def review_aware_die(message: str, code: int = 1):
            editorial = "AI editorial check rejected this Short: "
            structural = "Two generated plans failed structural quality checks: "
            if isinstance(message, str) and message.startswith(editorial):
                raise DraftRejected(message[len(editorial):][:600])
            if isinstance(message, str) and message.startswith(structural):
                raise DraftRejected(message[len(structural):][:600])
            return _original_die(message, code)

        upgrade.model_json = reviewed_model_json
        upgrade.bot.die = review_aware_die
        try:
            plan = _original_generate_plan()
            break
        except DraftRejected as exc:
            if attempt == 4:
                _original_die("Five rejected drafts; upload cancelled. Last issues: " + str(exc))
            feedback = str(exc)
            print(f"Draft rejected {attempt + 1}/5; regenerating with targeted feedback: {feedback}", flush=True)
        finally:
            upgrade.model_json = _original_model_json
            upgrade.bot.die = _original_die
    else:
        _original_die("No editor-approved plan; upload cancelled")

    ref = trend_ideas.reference_for(plan["theme"])
    if ref:
        plan["trend_reference"] = ref
    else:
        plan["trend_reference"] = None
        plan["trend_note"] = "No accessible suitable reference or smoke-test topic override"
    return plan


def checked_build(plan, audio_path):
    video = _original_build(plan, audio_path)
    visual_guard.check(plan, upgrade.bot.WORK, video)
    return video


upgrade.bot.run = safe_render
upgrade.choose_topic = trend_topic
upgrade.validate_plan = checked_validate_plan
upgrade.generate_plan = trend_plan
upgrade.matched_pexels_video = selection_guard.choose
upgrade.aligned_build_video = checked_build

if __name__ == "__main__":
    upgrade.main()
