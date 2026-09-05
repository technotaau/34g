"""Per-village research record (JSON) and Hindi-first Markdown report answering the standard questions."""
from collections import defaultdict
from datetime import date

from .registry import get_village, load_villages
from .store import load_sources, load_claims, save_record, village_dir, load_runs
from .verify import needs_verification
from . import STORE_DIR

QUESTIONS = [
    ("what", "यह गांव क्या है?", ["census_admin", "history"]),
    ("where", "यह कहां स्थित है?", ["census_admin"]),
    ("history", "कौन सी ऐतिहासिक जानकारी उपलब्ध है?", ["history", "displacement", "legal"]),
    ("people", "कौन से लोग/परिवार/गोत्र इससे जुड़े हैं?", ["people_family"]),
    ("culture", "सांस्कृतिक जानकारी", ["culture"]),
    ("temples", "मंदिर, लोक देवता, स्थल", ["religion_temple"]),
    ("festivals", "त्योहार व परंपराएं", ["religion_temple", "culture"]),
    ("land", "भूमि, खेती, पशुपालन, नहर", ["land_agriculture"]),
    ("education", "शिक्षा व विद्यालय", ["education"]),
]
MEDIA_SECTIONS = [
    ("photos", "ऐतिहासिक/वर्तमान फोटो", lambda s: s["media_type"] == "image" or "photo" in " ".join(s["topics"] + [s["title"].lower()])),
    ("videos", "वीडियो", lambda s: s["media_type"] == "video"),
    ("audio", "साक्षात्कार / ऑडियो", lambda s: s["media_type"] == "audio" or "interview" in s["title"].lower() or "साक्षात्कार" in s["title"]),
    ("books", "पुस्तकें व ऐतिहासिक संदर्भ", lambda s: s["source_type"] in ("book", "archive", "academic", "encyclopedia") or s["media_type"] in ("book", "document")),
    ("social", "सार्वजनिक सोशल मीडिया स्रोत", lambda s: s["source_type"] == "social"),
    ("gov", "सरकारी / कानूनी अभिलेख", lambda s: s["source_type"] in ("government", "legal", "census_mirror")),
    ("news", "समाचार", lambda s: s["source_type"] == "news"),
]


def _accepted(sources: dict) -> list[dict]:
    return sorted([s for s in sources.values() if not s.get("duplicate_of") and s["resolution"]["decision"] != "reject"],
                  key=lambda s: -s["relevance"]["score"])


def build_record(slug: str) -> dict:
    v = get_village(slug)
    sources = load_sources(slug)
    claims = load_claims(slug)
    acc = _accepted(sources)
    by_topic = defaultdict(list)
    for s in acc:
        for t in s["topics"]:
            by_topic[t].append(s["id"])
    entities = defaultdict(set)
    for s in acc:
        for k, vals in (s.get("entities") or {}).items():
            entities[k].update(vals or [])
    record = {
        "village": {"slug": slug, "name_en": v["names"]["en"], "name_hi": v["names"]["hi"], "status": v.get("status"), "notes": v.get("notes", ""),
                    "location": {"state": "Rajasthan", "district": "Bikaner", "tehsil": "Lunkaransar", "sub_tehsil": "Mahajan"} if v.get("unit_type") != "umbrella" else {}},
        "built": date.today().isoformat(),
        "counts": {"sources_total": len(sources), "accepted": len(acc), "review": sum(1 for s in sources.values() if s["resolution"]["decision"] == "review"),
                   "rejected": sum(1 for s in sources.values() if s["resolution"]["decision"] == "reject"),
                   "duplicates": sum(1 for s in sources.values() if s.get("duplicate_of")), "claims": len(claims)},
        "questions": {qid: {"label": label, "source_ids": sorted({sid for t in topics for sid in by_topic.get(t, [])}, key=lambda sid: -sources[sid]["relevance"]["score"])} for qid, label, topics in QUESTIONS},
        "media": {mid: {"label": label, "source_ids": [s["id"] for s in acc if pred(s)]} for mid, label, pred in MEDIA_SECTIONS},
        "entities": {k: sorted(v) for k, v in entities.items()},
        "claims": {"well_supported": [c for c in claims.values() if c["status"] in ("verified", "corroborated")],
                   "needs_verification": needs_verification(claims)},
        "manual_review": [{"id": s["id"], "url": s["url"], "title": s["title"], "flags": s["review_flags"], "reasons": s["resolution"]["reasons"]}
                          for s in sources.values() if s["review_flags"] and not s.get("duplicate_of")],
        "sources": {s["id"]: {k: s[k] for k in ("url", "title", "platform", "source_type", "media_type", "published_date", "language", "relevance", "resolution", "topics", "license", "attribution", "is_primary")} for s in acc},
        "runs": load_runs(slug),
    }
    save_record(slug, record)
    return record


def _src_line(s: dict) -> str:
    meta = [s["source_type"], s["media_type"], s.get("published_date") or "तिथि अज्ञात", f"स्कोर {s['relevance']['score']}"]
    lic = f" · लाइसेंस: {s['license']}" if s.get("license") else ""
    return f"- [{s['title']}]({s['url']}) ({' · '.join(meta)}){lic}"


def render_report(slug: str, record: dict | None = None) -> str:
    record = record or build_record(slug)
    sources = load_sources(slug)
    v = record["village"]
    L = [f"# {v['name_hi']} ({v['name_en']}) — शोध रिकॉर्ड", "",
         f"**स्थिति:** {v.get('status')} · **निर्मित:** {record['built']} · **तैयारकर्ता:** TechnoTaau Team (Jakhar Singh)", "",
         f"स्रोत: कुल {record['counts']['sources_total']}, स्वीकृत {record['counts']['accepted']}, समीक्षा हेतु {record['counts']['review']}, अस्वीकृत {record['counts']['rejected']}, डुप्लिकेट {record['counts']['duplicates']} · दावे: {record['counts']['claims']}", ""]
    if v.get("notes"):
        L += [f"> {v['notes']}", ""]
    L += ["## मुख्य प्रश्न", ""]
    for qid, q in record["questions"].items():
        L.append(f"### {q['label']}")
        if not q["source_ids"]:
            L.append("_अभी कोई स्रोत नहीं मिला। मैनुअल शोध आवश्यक।_")
        for sid in q["source_ids"][:12]:
            s = sources[sid]
            L.append(_src_line(s))
            if s.get("summary"):
                L.append(f"  - {s['summary'][:300]}")
        L.append("")
    L += ["## मीडिया व स्रोत प्रकार", ""]
    for mid, m in record["media"].items():
        L.append(f"### {m['label']} ({len(m['source_ids'])})")
        for sid in m["source_ids"][:15]:
            s = sources[sid]
            L.append(_src_line(s))
            md = s.get("media") or {}
            extra = [f"{k}: {str(val)[:160]}" for k, val in md.items() if val and k in ("channel", "uploader", "caption", "creator", "transcript_available", "timestamps", "book_title", "pages")]
            if extra:
                L.append("  - " + " · ".join(extra))
        L.append("")
    if record["entities"]:
        L += ["## निकाले गए नाम (entities)", ""]
        for k, vals in record["entities"].items():
            L.append(f"- **{k}:** " + ", ".join(vals[:40]))
        L.append("")
    L += ["## तथ्य / दावे", "", "### अच्छी तरह समर्थित (verified / corroborated)"]
    for c in record["claims"]["well_supported"]:
        L.append(f"- **{c['claim_key']}** = {c['value']} · {c['status']} ({c['independent_sources']} स्वतंत्र स्रोत) · {c.get('statement_hi') or c.get('statement_en','')}")
    if not record["claims"]["well_supported"]:
        L.append("_कोई नहीं_")
    L += ["", "### सत्यापन आवश्यक (single-source / unverified / conflicting)"]
    for c in record["claims"]["needs_verification"]:
        comp = f" · प्रतिस्पर्धी मान: {c['competing']}" if c.get("competing") else ""
        L.append(f"- **{c['claim_key']}** = {c['value']} · {c['status']} · विश्वास {c['confidence']}{comp} · स्रोत: {', '.join(c['sources'])}")
    if not record["claims"]["needs_verification"]:
        L.append("_कोई नहीं_")
    L += ["", "## शोधकर्ता द्वारा मैनुअल समीक्षा हेतु स्रोत", ""]
    for m in record["manual_review"]:
        L.append(f"- [{m['title']}]({m['url']}) · flags: {', '.join(m['flags'])} · {'; '.join(m['reasons'][:2])}")
    if not record["manual_review"]:
        L.append("_कोई नहीं_")
    L += ["", "## सभी स्वीकृत स्रोत (स्कोर क्रम में)", ""]
    for sid, s in record["sources"].items():
        full = sources[sid]
        q = ", ".join(full.get("found_by_query", [])[:2])
        L.append(f"- [{s['title']}]({s['url']}) · {s['platform']} · {s['source_type']} · स्कोर {s['relevance']['score']} · रिज़ॉल्यूशन {s['resolution']['decision']} ({s['resolution']['confidence']}) · खोज: {q}")
    text = "\n".join(L) + "\n"
    (village_dir(slug) / "report.md").write_text(text, encoding="utf-8")
    return text


def render_index() -> str:
    rows = ["# 34 गांव शोध सूचकांक", "", "| गांव | स्रोत | स्वीकृत | समीक्षा | दावे | सत्यापन बाकी | रिपोर्ट |", "|---|---|---|---|---|---|---|"]
    for v in load_villages():
        d = STORE_DIR / v["slug"]
        if not (d / "record.json").exists():
            rows.append(f"| {v['names']['hi']} ({v['names']['en']}) | – | – | – | – | – | _अभी शोध नहीं_ |")
            continue
        import json
        r = json.loads((d / "record.json").read_text(encoding="utf-8"))
        c = r["counts"]
        rows.append(f"| {v['names']['hi']} ({v['names']['en']}) | {c['sources_total']} | {c['accepted']} | {c['review']} | {c['claims']} | {len(r['claims']['needs_verification'])} | [report](store/{v['slug']}/report.md) |")
    text = "\n".join(rows) + "\n"
    (STORE_DIR.parent / "INDEX.md").write_text(text, encoding="utf-8")
    return text
