"""One-shot repository maintenance: only KAYIP FREKANS editor and tests."""
from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"ABORT {path}: expected one exact replacement, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


path = "kayip_frekans/mpt_story_recovery.py"
replace_once(path, "import json\nfrom pathlib import Path", "import json\nimport re\nfrom pathlib import Path")
old = '''            if raw["pass"] is False or issues:
                raise StoryExhausted("Editör somut tutarsızlık bildirdi: " + str(issues)[:600])
            return {"pass": True, "issues": [], "status": "verified_by_local_editor", "attempts": attempt}'''
new = '''            if raw["pass"] is False or issues:
                # A supplementary model's unsupported opinion is NOT evidence.
                # Run #10 discarded four full stories on vague criticism and timed out.
                # Independently enforce the existing eight-dimension quality gate.
                confirmed = []
                for issue in issues:
                    quotes = re.findall(r'[“"«]([^”"»]{14,})[”"»]', issue)
                    grounded = [quote for quote in quotes if quote in story]
                    lower = issue.casefold()
                    swap = re.search(r"([\\wÇĞİÖŞÜçğıöşü]+)'den\\s+([\\wÇĞİÖŞÜçğıöşü]+)'ye", issue)
                    explicit_name_error = (
                        swap is not None
                        and all(name.casefold() in story.casefold() for name in swap.groups())
                        and 'ismi' in lower and 'değiş' in lower
                    )
                    if ((len(grounded) >= 2 and ('çeliş' in lower or 'tutarsız' in lower))
                            or explicit_name_error):
                        confirmed.append(issue)
                if confirmed:
                    raise StoryExhausted("Editör metinle desteklenen tutarsızlık bildirdi: " + str(confirmed)[:600])
                result = {"pass": None, "issues": issues,
                          "status": "unverified_editor_claims", "attempts": attempt,
                          "requires_independent_quality_gate": True}
                _save(draft / "editor_unverified.json", result)
                print("Editör kanıtsız yorum verdi; bölümler korunuyor; bağımsız kalite kapısı zorunlu.", flush=True)
                return result
            return {"pass": True, "issues": [], "status": "verified_by_local_editor", "attempts": attempt}'''
replace_once(path, old, new)
replace_once(
    "kayip_frekans/mpt_long_story.py",
    "research_context=research_context, max_story_attempts=2,",
    "research_context=research_context, max_story_attempts=1,",
)
replace_once(
    ".github/workflows/kayip-frekans-mpt-long-serious.yml",
    "            output/long-test/reference_style_quality.json\n\n  prepare:",
    "            output/long-test/reference_style_quality.json\n            output/long-test/recovery/**\n\n  prepare:",
)
test = '''    def test_vague_editor_opinion_preserves_completed_story(self):
        with tempfile.TemporaryDirectory() as folder:
            result = mpt_story_recovery._review_story(
                "Kardeşimin sesi geldi. Kapı tekrar çarptı, komşu kapıyı gördü.",
                lambda prompt, structured=False: {
                    "pass": False, "issues": ["Kapı çarpması sık tekrarlanıyor."]},
                Path(folder))
            self.assertIsNone(result["pass"])
            self.assertEqual(result["status"], "unverified_editor_claims")
            self.assertTrue(result["requires_independent_quality_gate"])
            self.assertTrue((Path(folder) / "editor_unverified.json").exists())

'''
replace_once(
    "kayip_frekans/test_story_recovery.py",
    "    def test_four_failed_chapter_attempts_trigger_new_outline(self):",
    test + "    def test_four_failed_chapter_attempts_trigger_new_outline(self):",
)
print("PATCH APPLIED: only KAYIP FREKANS source, recovery test and workflow")
