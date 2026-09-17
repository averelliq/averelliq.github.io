"""Fetch a verified classic horror STORY, not a web snippet or an unlicensed blog post.

Only curated Edgar Allan Poe original-language works (author died 1849) are
eligible; modern translations, illustrations and unknown-rights submissions
are excluded. An outage returns None and NEVER invents a story or license.
"""
from __future__ import annotations

from html.parser import HTMLParser
import html
import json
import re
import urllib.parse
import urllib.request

# These are full-text editions, not Wikisource disambiguation/index pages.
_SOURCES = (
    {
        "page": "The_Works_of_the_Late_Edgar_Allan_Poe_(1850)/Volume_1/The_Fall_of_the_House_of_Usher",
        "title": "The Fall of the House of Usher", "author": "Edgar Allan Poe",
        "author_death_year": 1849, "original_publication_year": 1839,
        "license": "Public domain original English work; no modern translation used",
        "themes": "ev kardeş aile eski oda kasvet kapı ses köy",
    },
    {
        "page": "Tales_(Poe)/The_Black_Cat",
        "title": "The Black Cat", "author": "Edgar Allan Poe",
        "author_death_year": 1849, "original_publication_year": 1843,
        "license": "Public domain original English work; no modern translation used",
        "themes": "kedi hayvan duvar ev suç vicdan",
    },
)


class _StoryParagraphs(HTMLParser):
    """Collect prose paragraphs; ignore navigation, page numbers and scripts."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragraph_depth = 0
        self.block_depth = 0
        self.current: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        klass = attrs.get("class", "")
        if tag in ("script", "style", "table", "nav") or (
            tag == "div" and any(x in klass for x in ("ws-header", "mw-editsection", "licenseContainer"))
        ):
            self.block_depth += 1
        elif self.block_depth:
            if tag in ("script", "style", "table", "nav", "div"):
                self.block_depth += 1
        elif tag == "p":
            self.paragraph_depth += 1
            if self.paragraph_depth == 1:
                self.current = []
        elif tag == "br" and self.paragraph_depth:
            self.current.append(" ")

    def handle_endtag(self, tag):
        if self.block_depth:
            if tag in ("script", "style", "table", "nav", "div"):
                self.block_depth -= 1
            return
        if tag == "p" and self.paragraph_depth:
            self.paragraph_depth -= 1
            if not self.paragraph_depth:
                paragraph = re.sub(r"\s+", " ", html.unescape("".join(self.current))).strip()
                if len(paragraph) >= 55:
                    self.paragraphs.append(paragraph)

    def handle_data(self, data):
        if self.paragraph_depth and not self.block_depth:
            self.current.append(data)


def _download(page: str) -> str:
    params = urllib.parse.urlencode({
        "action": "parse", "page": page.replace("_", " "), "prop": "text",
        "format": "json", "redirects": "1", "formatversion": "2",
    })
    request = urllib.request.Request(
        "https://en.wikisource.org/w/api.php?" + params,
        headers={"User-Agent": "KayipFrekansPublicDomainStoryReader/1.0 (source attribution in video metadata)",
                 "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        data = json.load(response)
    raw = data.get("parse", {}).get("text", "")
    if isinstance(raw, dict):
        raw = raw.get("*", "")
    if not isinstance(raw, str) or not raw:
        raise ValueError("Wikisource did not return a full-text page")
    parser = _StoryParagraphs()
    parser.feed(raw)
    text = "\n\n".join(parser.paragraphs)
    if len(text) < 2200 or len(text.split()) < 350:
        raise ValueError("Wikisource response is not a substantial story")
    return text[:32000]


def fetch_story(topic: str) -> dict | None:
    """Prefer a verified full story. Return None on outage; never copy a blog."""
    topic_lower = topic.casefold()
    ranked = sorted(_SOURCES, key=lambda source: sum(
        term in topic_lower for term in source["themes"].split()), reverse=True)
    for source in ranked:
        if source["author_death_year"] > 1900:
            continue  # Conservative worldwide rights filter; never use modern adaptations.
        try:
            text = _download(source["page"])
        except Exception as exc:
            print(f"Kamu malı hikâye kaynağına erişilemedi ({source['title']}): {type(exc).__name__}: {str(exc)[:130]}", flush=True)
            continue
        result = {key: value for key, value in source.items() if key != "themes"}
        result.update({
            "url": "https://en.wikisource.org/wiki/" + source["page"],
            "source_kind": "curated_public_domain_original_story",
            "source_language": "en", "story_text": text,
            "source_words": len(text.split()), "retrieved": True,
            "adaptation_requires_attribution": True,
            "do_not_present_as_true_account": True,
        })
        print(f"İnternetten kamu malı hikâye alındı: {result['title']} ({result['source_words']} kelime)", flush=True)
        return result
    print("İnternetten doğrulanabilir kamu malı TAM hikâye alınamadı; özgün hikâye yedeği kullanılacak.", flush=True)
    return None


def source_excerpt(source: dict | None, index: int = 0, count: int = 1) -> str:
    """Feed a bounded excerpt to the model, preserving the source's progression."""
    if not source:
        return ""
    text = str(source.get("story_text", ""))
    if not text:
        return ""
    count = max(1, count)
    index = max(0, min(index, count - 1))
    start = len(text) * index // count
    end = len(text) * (index + 1) // count
    segment = text[start:end].strip()
    if not segment:
        return ""
    return (
        "İNTERNETTEN ALINAN KAMU MALI HİKÂYE DAYANAĞI (İNGİLİZCE): "
        f"{source.get('author')} — {source.get('title')}. "
        "Türkçe ve cinli özgün UYARLAMA yaz; kaynakta olmayan gerçeklik iddiası ekleme. "
        "Olay örgüsünün bu bölümdeki sırasını gözet, özgün cümleleri aynen kopyalama.\n"
        + segment[:1850]
    )
