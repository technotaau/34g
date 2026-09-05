"""Deterministic classification: platform, source type, reliability, media type, topics, period, primary/secondary."""
import json
import re
from . import CONFIG_DIR
from .normalize import host_of, norm_text, contains_term

LEXICON = json.loads((CONFIG_DIR / "lexicon.json").read_text(encoding="utf-8"))
DOWNGRADES = {"community_wiki": 0.45, "blog": 0.4, "social": 0.35, "video": 0.4, "website": 0.4}


def _suffix_lookup(table: dict, host: str):
    best, best_len = None, -1
    for suffix, val in table.items():
        if (host == suffix or host.endswith("." + suffix) or suffix in host) and len(suffix) > best_len:
            best, best_len = val, len(suffix)
    return best


def classify_platform(url: str) -> str:
    host = host_of(url)
    return _suffix_lookup(LEXICON["platforms"], host) or host


def classify_source_type(url: str, agent_hint: str = "") -> tuple[str, float, bool]:
    host = host_of(url)
    hit = _suffix_lookup(LEXICON["source_types"], host)
    if hit:
        stype, rel, primary = hit[0], float(hit[1]), bool(hit[2])
        if agent_hint and agent_hint in DOWNGRADES and DOWNGRADES[agent_hint] < rel:
            return agent_hint, DOWNGRADES[agent_hint], False  # agent saw user-page/blog/social content on a reputable host
        return stype, rel, primary
    if agent_hint:
        return agent_hint, 0.45, False
    return "website", 0.4, False


def classify_media(url: str, platform: str, agent_hint: str = "") -> str:
    if agent_hint:
        return agent_hint
    m = LEXICON["media_by_platform"].get(platform)
    if m:
        return m
    if re.search(r"\.(pdf|djvu)(\?|$)", url, re.I):
        return "document"
    if re.search(r"\.(jpe?g|png|gif|webp)(\?|$)", url, re.I):
        return "image"
    if re.search(r"\.(mp3|wav|m4a)(\?|$)", url, re.I):
        return "audio"
    return "text"


def classify_topics(text: str, agent_topics=None) -> list[str]:
    found = set(agent_topics or [])
    for topic, kws in LEXICON["topics"].items():
        if any(contains_term(text, k) for k in kws):
            found.add(topic)
    return sorted(found)


def classify_period(text: str, agent_period: str = "") -> str:
    if agent_period:
        return agent_period
    t = norm_text(text)
    hits = []
    for period, markers in LEXICON["period_markers"].items():
        for m in markers:
            if re.search(m, t) or contains_term(text, m):
                hits.append(period)
                break
    if not hits:
        return ""
    return hits[0] if len(hits) == 1 else "mixed:" + "+".join(hits)


def detect_language(text: str) -> str:
    dev = len(re.findall(r"[ऀ-ॿ]", text or ""))
    lat = len(re.findall(r"[A-Za-z]", text or ""))
    if dev and lat:
        return "hi" if dev > lat else "en+hi"
    return "hi" if dev else ("en" if lat else "")
