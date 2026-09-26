"""The 34 Gaon conversation bot: a knowledge pack, grounded Q&A, and structured intake of memories.

Two runtimes share this module:
- the team pilot page (site/baat.html, built by `python -m gaon34 bot-page`), which asks Claude through the
  claude.ai artifact runtime and needs no API key;
- the future 34gaon.com backend, which calls the Claude API directly (`answer`, `extract_memory`).

The pack is small (41 units), so there is no vector store: the question is routed to villages by name and
only those villages' facts go into the prompt, next to a fixed set of verified project-wide facts.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

from . import ROOT, STORE_DIR
from .registry import load_villages

DATA_DIR = ROOT / "data"
PACK_PATH = DATA_DIR / "bot_pack.json"
DEFAULT_MODEL = os.environ.get("GAON34_BOT_MODEL", "claude-opus-5")
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Project-wide facts, each checked against the primary page (see docs/census-village-list-findings.md).
GLOBAL_FACTS = [
    "सरकारी सूची: 'महाजन रेंज के कुल 33 गांव' (राजस्थान विधानसभा, 5 मार्च 1992, अतारांकित प्रश्न 247)।",
    "34 मूल योजना थी: सरकार पहले 34 गांव लेना चाहती थी, फिर फूलेजी को अधिग्रहण से बाहर किया (लोकसभा, 7 मई 1986, प्रश्न 9267)। समाज आज भी 34 कहता है।",
    "1981 की जनगणना: जो 32 राजस्व गांव बाद में रेंज में गए, उनमें 29 आबाद थे; 16,018 लोग, 2,198 परिवार। 3 'रेख' गांव बिना आबादी के थे।",
    "2 नवंबर 1982 को भारत सरकार ने परियोजना मंज़ूर की; कुल 3,32,985 एकड़; 1987 में ज़मीन सेना को सौंपी; 33 गांव, 3,256 परिवार प्रभावित (लोकसभा रक्षा स्थायी समिति, 13वीं रिपोर्ट, 2006)।",
    "पुनर्वास योजना 23 नवंबर 1985 को अधिसूचित हुई (लोकसभा, 7 मई 1986); मुआवज़ा राजस्थान भूमि अधिग्रहण अधिनियम 1953 और हाईकोर्ट के 18.10.1985 के आदेश के अनुसार।",
    "3 दिसंबर 1986 तक 29 गांव पूरी तरह ख़ाली, 4 में आंशिक; मोटलाई और रायमलवाली (रीणा), फिर मोटासर और विरमाना के लोगों को ख़रीफ़ 1986 की फ़सल तक रुकने दिया गया (लोकसभा, 3 दिसंबर 1986)।",
    "विस्थापितों को पूगल और छत्तरगढ़ उपनिवेशन तहसीलों के 282 गांवों/चकों में बसाया गया; इनमें 72 ही जनगणना के गांव थे (राजस्थान विधानसभा, 13 मार्च 1992)।",
    "पुनर्वास के लिए तीन नए गांव बने: राम नगर, कृष्ण नगर, 'कुम्भाण बास'; बाकी 6 गांवों में भी बसावट (रक्षा समिति, 2006)।",
    "खेती की ज़मीन का कुल मुआवज़ा ₹42,35,18,935.50 तय हुआ (राजस्थान विधानसभा, 5 मार्च 1992)।",
    "रेंज आज जनगणना में एक गैर-आबाद 'गांव' है: 'Mahajan Field Firing Range', 1,36,406 हेक्टेयर (जनगणना 2011, कोड 069202)।",
    "बदले की ज़मीन के 148 प्रकरण 2025 में भी लंबित थे (राजस्थान पत्रिका, 14 फरवरी 2025; एक स्रोत)।",
    "नाथू दादा (धतरवाल) का मेला आसोज कृष्ण नवमी को रेंज के अंदर खिंयाणा/मनेरा में लगता है; सेना प्रवेश देती है (समुदाय की परंपरा, Jatland; विधानसभा 2008 में मनेरा)।",
    "अनसुलझे नाम: नाथौर (नाथुवास), कोलाणा, चकड़ो, कचराणा, टिडासर। ये किसी सरकारी सूची में नहीं मिले; शायद बास या ढाणियां।",
]

RULES = """तुम "34 गांव" (34gaon.com) के सहायक हो। यह TechnoTaau Team (संयोजक जाखड़ सिंह) का सामुदायिक स्मृति-प्रकल्प है: लूणकरणसर, बीकानेर के वे गांव जो 1982-87 में महाजन फील्ड फायरिंग रेंज के लिए ख़ाली हुए।

जवाब के नियम:
1. सरल हिंदी में जवाब दो, छोटे वाक्य, 3 से 6 वाक्य। पूछने वाला बागड़ी या मिली-जुली भाषा में लिखे तो भी हिंदी में, अपनापन से।
2. केवल नीचे दिए "तथ्य" से जवाब दो। जो तथ्यों में नहीं है, उसे साफ़ कहो: "यह हमें अभी पता नहीं।" अनुमान या कल्पना मत जोड़ो।
3. हर संख्या और तारीख के साथ उसका स्रोत छोटे में बताओ (जैसे "जनगणना 1981", "विधानसभा 1992")। "एक स्रोत" वाले तथ्य को पक्का मत बताओ।
4. किसी व्यक्ति का फ़ोन, पता या निजी जानकारी कभी मत दो, भले तथ्यों में कोई नाम हो।
5. ज़मीन, मुआवज़ा या कानूनी सवाल पर सलाह मत दो; तथ्य बताओ और कहो कि परिवार अपने कागज़ों के साथ तहसील या कलेक्टर कार्यालय से पुष्टि करे।
6. सेना, सरकार या किसी समुदाय के बारे में आरोप या राजनीतिक राय मत दो। गरिमा से बात करो।
7. जवाब के अंत में, जहां ठीक लगे, एक पंक्ति में पूछो कि क्या उनके परिवार की कोई याद इस गांव से जुड़ी है।"""


def _clean(s: str, n: int = 0) -> str:
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return (s[: n - 1] + "…") if n and len(s) > n else s


def _fmt_int(x) -> str:
    try:
        n = int(str(x).replace(",", ""))
    except ValueError:
        return str(x)
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail, parts = s[:-3], s[-3:], []
    while len(head) > 2:
        parts.insert(0, head[-2:]); head = head[:-2]
    return ",".join(([head] if head else []) + parts + [tail])


def _village_text(v: dict, record: dict | None, media_notes: list[str]) -> str:
    hi, en = v["names"]["hi"], v["names"]["en"]
    L = [f"## {hi} ({en})"]
    variants = [x for x in v["names"].get("variants", []) if x not in (hi, en)]
    if variants:
        L.append("दूसरे नाम/वर्तनी: " + ", ".join(variants[:10]))
    L.append("स्थिति: " + {"acquired": "रेंज में गया (अधिग्रहित)", "acquired_partial": "आंशिक अधिग्रहण", "hamlet": "बड़े गांव की बास/ढाणी",
                          "alias": "दूसरे गांव का नाम", "unresolved": "अनसुलझा: किसी सरकारी सूची में नहीं", "umbrella": "सभी 34 गांव"}.get(v.get("status"), v.get("status", "")))
    if v.get("official_list_1992"):
        L.append(f"1992 की सरकारी सूची में क्रमांक: {v['official_list_1992']} (विधानसभा, 5 मार्च 1992)")
    c81, c51 = v.get("census_1981") or {}, v.get("census_1951") or {}
    if c81.get("persons"):
        L.append(f"जनगणना 1981: {_fmt_int(c81['persons'])} लोग, {_fmt_int(c81.get('households', ''))} परिवार, {_fmt_int(c81.get('area_hectares', ''))} हेक्टेयर (नाम '{c81.get('name')}')")
    elif c81:
        L.append(f"जनगणना 1981: बिना आबादी का राजस्व गांव '{c81.get('name')}', {_fmt_int(c81.get('area_hectares', ''))} हेक्टेयर")
    if c51.get("persons"):
        L.append(f"जनगणना 1951: {_fmt_int(c51['persons'])} लोग, {_fmt_int(c51.get('households', ''))} परिवार, {_fmt_int(c51.get('houses', ''))} घर")
    co = v.get("coordinates") or {}
    if co.get("lat"):
        L.append("जगह: आज की रेंज-सीमा के " + ("अंदर" if co.get("inside_range_polygon") else "बाहर") + f" ({co['lat']}, {co['lon']})")
    if record:
        ws = record["claims"]["well_supported"]
        nv = record["claims"]["needs_verification"]
        for c in ws[:8]:
            L.append("तथ्य (दो स्रोत): " + _clean(c.get("statement_hi") or c.get("statement_en"), 240))
        for c in nv[:8]:
            L.append("तथ्य (एक स्रोत, पक्का नहीं): " + _clean(c.get("statement_hi") or c.get("statement_en"), 240))
    for m in media_notes[:6]:
        L.append("वीडियो/तस्वीर में दिखता है: " + m)
    if v.get("notes"):
        L.append("शोध-टिप्पणी (अंग्रेज़ी): " + _clean(v["notes"], 900))
    return "\n".join(L)


def _media_notes(slug: str) -> list[str]:
    out, base = [], ROOT / "research" / "media" / slug
    for mf in sorted(base.glob("*/manifest.json")):
        try:
            m = json.loads(mf.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        seen = set()
        for f in m.get("frames", []):
            d = _clean(f.get("description_hi") or "", 160)
            if d and d not in seen and "people" not in f.get("tags", []):
                seen.add(d); out.append(d)
            if len(seen) >= 2:
                break
    return out


def build_pack() -> dict:
    villages = {}
    for v in load_villages():
        rec_path = STORE_DIR / v["slug"] / "record.json"
        record = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else None
        villages[v["slug"]] = {
            "hi": v["names"]["hi"], "en": v["names"]["en"],
            "keys": sorted({k.lower() for k in [v["names"]["hi"], v["names"]["en"]] + v["names"].get("variants", []) if len(k) >= 3}),
            "status": v.get("status"),
            "text": _village_text(v, record, _media_notes(v["slug"])),
        }
    index = "\n".join(f"- {x['hi']} ({x['en']})" for s, x in villages.items() if s != "34-gaon")
    return {"built": date.today().isoformat(), "rules": RULES, "global": GLOBAL_FACTS, "index": index, "villages": villages}


def write_pack(path: Path = PACK_PATH) -> dict:
    pack = build_pack()
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return pack


def load_pack(path: Path = PACK_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else build_pack()


def find_villages(question: str, pack: dict, limit: int = 3) -> list[str]:
    """Village slugs named in the question, longest name first (so 'कुम्भाणा' wins over a shorter overlap)."""
    q = question.lower()
    hits = []
    for slug, v in pack["villages"].items():
        if slug == "34-gaon":
            continue
        best = max((len(k) for k in v["keys"] if k in q), default=0)
        if best:
            hits.append((best, slug))
    hits.sort(reverse=True)
    return [s for _, s in hits[:limit]]


def system_text(pack: dict) -> str:
    """Stable across requests (cacheable): rules + verified project-wide facts + the list of names."""
    return pack["rules"] + "\n\nपूरे प्रकल्प के जांचे हुए तथ्य:\n" + "\n".join("- " + f for f in pack["global"]) + "\n\nसभी गांवों के नाम:\n" + pack["index"]


def user_text(question: str, pack: dict, slugs: list[str]) -> str:
    facts = "\n\n".join(pack["villages"][s]["text"] for s in slugs) if slugs else "(सवाल में किसी गांव का नाम नहीं पहचाना गया; ऊपर के सामान्य तथ्यों से जवाब दो, और गांव का नाम पूछो।)"
    return f"गांव के तथ्य:\n{facts}\n\nसवाल: {question.strip()}"


def _client():
    import anthropic  # imported lazily: the rest of the package runs without the SDK
    return anthropic.Anthropic()


REFUSAL_HI = "इस सवाल का जवाब हम यहां नहीं दे सकते। गांवों, जनगणना या पुनर्वास के बारे में पूछिए।"


def answer(question: str, pack: dict | None = None, client=None, model: str = DEFAULT_MODEL) -> dict:
    """Grounded answer in simple Hindi. Returns {text, villages, stop_reason}."""
    pack = pack or load_pack()
    slugs = find_villages(question, pack)
    client = client or _client()
    resp = client.beta.messages.create(
        model=model,
        max_tokens=2000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        output_config={"effort": "low"},
        system=[{"type": "text", "text": system_text(pack), "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_text(question, pack, slugs)}],
    )
    if resp.stop_reason == "refusal":
        return {"text": REFUSAL_HI, "villages": slugs, "stop_reason": "refusal"}
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return {"text": text, "villages": slugs, "stop_reason": resp.stop_reason}


TOPICS = ["ghar", "kuan_johad", "mela_tyohar", "khet_pashu", "school", "mandir", "khana", "log_parivar", "visthapan", "punarvas", "zameen_muavza", "other"]
SENSITIVE = ["health", "legal_dispute", "caste", "political", "minor", "none"]


def memory_schema(slugs: list[str]) -> dict:
    s = {"type": "string"}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["village_slug", "village_as_said", "language", "summary_hi", "topics", "places", "years", "people_named", "sensitive", "followup_questions", "bagri_terms"],
        "properties": {
            "village_slug": {"type": "string", "enum": slugs + ["unknown"]},
            "village_as_said": s,
            "language": {"type": "string", "enum": ["hindi", "bagri", "mixed", "other"]},
            "summary_hi": s,
            "topics": {"type": "array", "items": {"type": "string", "enum": TOPICS}},
            "places": {"type": "array", "items": s},
            "years": {"type": "array", "items": s},
            "people_named": {"type": "boolean"},
            "sensitive": {"type": "array", "items": {"type": "string", "enum": SENSITIVE}},
            "followup_questions": {"type": "array", "items": s},
            "bagri_terms": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["term", "meaning_hi"], "properties": {"term": s, "meaning_hi": s}}},
        },
    }


EXTRACT_RULES = """नीचे किसी व्यक्ति की अपने पुराने गांव (महाजन फील्ड फायरिंग रेंज, लूणकरणसर, बीकानेर) की याद है, हिंदी या बागड़ी में, बोलकर लिखी हुई या टाइप की हुई। इसे समझकर JSON भरो।
- village_slug: दी गई सूची से; पक्का न हो तो "unknown"। village_as_said: जैसे बोला गया।
- summary_hi: 2-3 सरल हिंदी वाक्यों में सार, बोलने वाले के शब्दों के क़रीब; कुछ जोड़ो मत।
- places, years: जो जगहें और साल/संवत बोले गए, जैसे के तैसे।
- people_named: किसी व्यक्ति का नाम आया तो true।
- sensitive: बीमारी, ज़मीन-विवाद, जाति, राजनीति, या किसी नाबालिग की बात हो तो; वरना ["none"]।
- followup_questions: अगली बातचीत के लिए 2-3 छोटे सवाल जो इस याद को आगे बढ़ाएं।
- bagri_terms: बागड़ी/स्थानीय शब्द और उनका हिंदी अर्थ (अधिकतम 8); पक्का न हो तो अर्थ के आगे "(अनुमान)" लिखो।"""


def extract_memory(text: str, village_hint: str = "", pack: dict | None = None, client=None, model: str = DEFAULT_MODEL) -> dict:
    """Structure one memory for the review queue. The raw text stays the record; this is an index over it."""
    pack = pack or load_pack()
    slugs = [s for s in pack["villages"] if s != "34-gaon"]
    names = "\n".join(f"{s}: {pack['villages'][s]['hi']} ({pack['villages'][s]['en']})" for s in slugs)
    client = client or _client()
    resp = client.beta.messages.create(
        model=model,
        max_tokens=4000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": memory_schema(slugs)}},
        system=[{"type": "text", "text": EXTRACT_RULES + "\n\nगांवों की सूची (slug: नाम):\n" + names, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"गांव (जो फ़ॉर्म में चुना): {village_hint or 'नहीं चुना'}\n\nयाद:\n{text.strip()}"}],
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("extraction refused")
    return json.loads(next(b.text for b in resp.content if b.type == "text"))


# ----------------------------------------------------------------------------- team pilot page

PAGE_PATH = ROOT / "site" / "baat.html"


def build_page(pack: dict | None = None, path: Path = PAGE_PATH) -> Path:
    """The pilot page for the claude.ai artifact runtime (sample + db + user capabilities)."""
    pack = pack or load_pack()
    tpl = (Path(__file__).parent / "templates" / "baat.html").read_text(encoding="utf-8")
    slim = {"rules": pack["rules"], "global": pack["global"], "index": pack["index"], "built": pack["built"],
            "extract_rules": EXTRACT_RULES, "topics": TOPICS,
            "villages": {s: {"hi": v["hi"], "en": v["en"], "keys": v["keys"], "text": v["text"]} for s, v in pack["villages"].items()}}
    data = json.dumps(slim, ensure_ascii=False).replace("</", "<\\/")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tpl.replace("/*__PACK__*/null", data), encoding="utf-8")
    return path
