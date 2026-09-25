"""Lead harvester: find public YouTube videos about the 34 villages, at scale.

Two passes, both through yt-dlp's public search (no login, no cookies):

1. Search pass. For every village unit, a small bilingual query set built from its
   names and the phrases people actually use in titles ("34 गांव", "पुराणा 34 गाँव",
   "महाजन फायरिंग रेंज" ...), plus umbrella queries for the whole area.
2. Snowball pass. Every channel that posted at least one strong hit is listed in full
   (videos + shorts) and filtered with the same matcher. Uploaders who film one
   village usually film several; this is where most leads come from.

Output is a leads file, not the research store: research/leads/youtube.jsonl (one row
per video, merged across runs) and research/leads/youtube_summary.md. Leads are
triaged later and promoted with `python -m gaon34 video <slug> <url>`.
Matching is deliberately generous (collect now, filter later) but every row carries
the words that matched, so a person can see why it is there.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from . import RESEARCH_DIR, STORE_DIR
from .normalize import canonical_url
from .registry import load_villages

LEADS_DIR = RESEARCH_DIR / "leads"
YT_LEADS = LEADS_DIR / "youtube.jsonl"
YT_SUMMARY = LEADS_DIR / "youtube_summary.md"

# words that tie a title to the displaced area (not to a namesake village elsewhere)
CONTEXT = [
    r"34\s*(?:गांव|गाँव|गाव|गांवो|गाँवो|ganv|gaon|gaav|gav|village)", r"चौंतीस", r"#34gaav", r"#34gaon",
    r"पुराण[ाे]\s*(?:34|गांव|गाँव)", r"पुरान[ाे]\s*(?:34|गांव|गाँव)", r"उजड़", r"उठे\s*हुए", r"छूटे\s*हुए", r"विस्थापित",
    r"महाजन", r"mahajan", r"फायरिंग", r"firing", r"रेंज", r"mffr", r"लूणकरणसर", r"लूनकरनसर", r"lunkaransar", r"loonkaransar",
    r"oldvillage", r"old\s*village", r"40\s*साल", r"35\s*-?\s*40\s*साल", r"1984", r"1985", r"1986",
]
CONTEXT_RE = re.compile("|".join(CONTEXT), re.I)
UMBRELLA_RE = re.compile(r"34\s*(?:गांव|गाँव|गाव|गांवो|गाँवो|ganv|gaon|gaav|gav)|#34gaav|महाजन\s*(?:फील्ड\s*)?फायरिंग|mahajan\s*(?:field\s*)?firing", re.I)

UMBRELLA_QUERIES = [
    "34 गांव महाजन फायरिंग रेंज", "पुराणा 34 गाँव", "पुराने 34 गांव", "34 गाँव लूणकरणसर", "34 गांव एरिया",
    "महाजन फील्ड फायरिंग रेंज गांव", "महाजन फायरिंग रेंज उजड़े गांव", "महाजन रेंज से उठे हुए गांव",
    "34 gaon mahajan", "34 gaav old village", "mahajan field firing range village", "mahajan firing range old village",
    "34 गांव विस्थापित", "34 गांव होली कुम्भाणा", "नाथू दादा धोरा मेला खिंयाणा", "पीर बाबा कानोलाई धाम",
]

QUERY_TEMPLATES_HI = ["{n} 34 गांव", "पुराणा 34 गाँव {n}", "{n} गांव महाजन", "{n} फायरिंग रेंज"]
QUERY_TEMPLATES_EN = ["{n} village mahajan", "{n} 34 gaon"]


def _run_json_lines(args: list[str], timeout: int = 180) -> list[dict]:
    try:
        out = subprocess.run(["yt-dlp", "--no-warnings", "--flat-playlist", "-j", *args],
                             capture_output=True, text=True, timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return []
    rows = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def search(query: str, n: int = 20) -> list[dict]:
    return _run_json_lines([f"ytsearch{n}:{query}"])


def channel_uploads(channel_url: str, limit: int = 800) -> list[dict]:
    rows = []
    for tab in ("videos", "shorts", "streams"):
        rows += _run_json_lines(["--playlist-end", str(limit), f"{channel_url.rstrip('/')}/{tab}"], timeout=300)
    return rows


def _name_patterns(v: dict) -> list[str]:
    names = {v["names"]["hi"], v["names"]["en"], *v["names"].get("variants", [])}
    out = set()
    for n in names:
        n = n.strip()
        # single-word names only; "Kumbhana Holi" style variants are queries, not names
        if not n or len(n) < 3 or " " in n and not re.search(r"(छोटी|मोटी|Chhoti|Moti)", n):
            continue
        out.add(n)
    return sorted(out, key=len, reverse=True)


class Matcher:
    def __init__(self, villages: list[dict]):
        self.units = []
        for v in villages:
            if v.get("unit_type") == "umbrella":
                continue
            pats = _name_patterns(v)
            if not pats:
                continue
            rx = re.compile(r"(?<![\wऀ-ॿ])(" + "|".join(re.escape(p) for p in pats) + r")(?![\wऀ-ॿ])", re.I)
            neg = [t for t in v.get("disambiguation", {}).get("negative_terms", [])]
            self.units.append((v["slug"], rx, neg))

    def match(self, text: str) -> dict:
        text = text or ""
        villages, words = [], []
        for slug, rx, neg in self.units:
            m = rx.search(text)
            if m:
                if any(n.lower() in text.lower() for n in neg):
                    continue
                villages.append(slug)
                words.append(m.group(1))
        ctx = sorted({m.group(0) for m in CONTEXT_RE.finditer(text)})
        umb = bool(UMBRELLA_RE.search(text))
        score = 0
        if villages:
            score += 40
        if ctx:
            score += min(40, 15 * len(ctx))
        if umb:
            score += 20
        return {"villages": villages, "name_hits": words, "context_hits": ctx, "umbrella": umb, "score": min(score, 100)}


def queries_for(v: dict) -> list[str]:
    hi = [v["names"]["hi"]] + [x for x in v["names"].get("variants", []) if re.search(r"[ऀ-ॿ]", x) and " " not in x][:1]
    en = [v["names"]["en"]]
    qs = []
    for n in dict.fromkeys(hi):
        qs += [t.format(n=n) for t in QUERY_TEMPLATES_HI]
    for n in en:
        qs += [t.format(n=n) for t in QUERY_TEMPLATES_EN]
    return list(dict.fromkeys(qs))


def _known_urls() -> set[str]:
    idx = STORE_DIR / "_index" / "url_index.json"
    known = set()
    if idx.exists():
        known |= set(json.loads(idx.read_text(encoding="utf-8")).keys())
    for p in STORE_DIR.glob("*/sources.json"):
        for s in json.loads(p.read_text(encoding="utf-8")).values():
            known.add(canonical_url(s.get("url", "")))
    return known


def load_leads(path: Path = YT_LEADS) -> dict[str, dict]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def save_leads(leads: dict[str, dict], path: Path = YT_LEADS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(leads.values(), key=lambda r: (-r["score"], r.get("channel") or "", r["id"]))
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def _row(entry: dict, m: dict, found_by: str, known: set[str]) -> dict:
    vid = entry.get("id")
    url = f"https://www.youtube.com/watch?v={vid}"
    return {
        "id": vid, "url": url, "title": entry.get("title") or "",
        "channel": entry.get("channel") or entry.get("uploader") or "",
        "channel_id": entry.get("channel_id") or "", "channel_url": entry.get("channel_url") or entry.get("uploader_url") or "",
        "duration": entry.get("duration"), "views": entry.get("view_count"),
        "villages": m["villages"], "name_hits": m["name_hits"], "context_hits": m["context_hits"],
        "umbrella": m["umbrella"], "score": m["score"], "found_by": [found_by],
        "known": canonical_url(url) in known, "first_seen": date.today().isoformat(),
    }


def _merge(leads: dict, row: dict) -> None:
    old = leads.get(row["id"])
    if not old:
        leads[row["id"]] = row
        return
    old["found_by"] = sorted(set(old.get("found_by", [])) | set(row["found_by"]))
    for k in ("title", "channel", "channel_id", "channel_url", "duration", "views"):
        old[k] = row.get(k) or old.get(k)
    for k in ("villages", "name_hits", "context_hits"):
        old[k] = sorted(set(old.get(k, [])) | set(row.get(k, [])))
    old["umbrella"] = old.get("umbrella") or row["umbrella"]
    old["score"] = max(old["score"], row["score"])
    old["known"] = row["known"]


def keep(m: dict, channel_is_area: bool = False) -> bool:
    """A village name AND some area context, or an explicit 34-gaon/MFFR phrase.
    On a channel already known to film the 34 gaon, the village name alone is enough
    (the channel supplies the context); such rows are marked context_from_channel."""
    if m["umbrella"] or (m["villages"] and m["context_hits"]):
        return True
    return bool(channel_is_area and m["villages"])


def harvest(slugs: list[str] | None = None, per_query: int = 20, snowball: bool = True,
            max_channels: int = 40, log=print) -> dict:
    villages = load_villages()
    matcher = Matcher(villages)
    known = _known_urls()
    leads = load_leads()
    before = len(leads)
    targets = [v for v in villages if v.get("unit_type") != "umbrella" and (not slugs or v["slug"] in slugs)] if slugs != ["-"] else []
    queries = ([] if slugs else UMBRELLA_QUERIES) + [q for v in targets for q in queries_for(v)]
    if slugs == ["-"]:  # channels only
        queries = []
    qstats = {}
    channel_hits: Counter = Counter()
    channel_url: dict[str, str] = {}
    for i, q in enumerate(queries, 1):
        rows = search(q, per_query)
        kept = 0
        for e in rows:
            if not e.get("id"):
                continue
            m = matcher.match(f"{e.get('title','')} {e.get('description') or ''}")
            if not keep(m):
                continue
            kept += 1
            r = _row(e, m, f"search:{q}", known)
            _merge(leads, r)
            if r["channel_id"]:
                channel_hits[r["channel_id"]] += 1
                channel_url[r["channel_id"]] = r["channel_url"] or f"https://www.youtube.com/channel/{r['channel_id']}"
        qstats[q] = {"results": len(rows), "kept": kept}
        log(f"[{i}/{len(queries)}] {q}: {len(rows)} results, {kept} kept")
        time.sleep(0.5)
    save_leads(leads)
    chstats = {}
    seed_file = RESEARCH_DIR / "config" / "seed_channels.json"
    seeds = json.loads(seed_file.read_text(encoding="utf-8"))["channels"] if seed_file.exists() else {}
    if snowball:
        order = [(cid, 99) for cid in seeds] + [(c, n) for c, n in channel_hits.most_common(max_channels) if c not in seeds]
        for cid, n in order:
            channel_url.setdefault(cid, seeds.get(cid, {}).get("url") or f"https://www.youtube.com/channel/{cid}")
            rows = channel_uploads(channel_url[cid])
            kept = 0
            for e in rows:
                if not e.get("id"):
                    continue
                e.setdefault("channel_id", cid)
                e.setdefault("channel_url", channel_url[cid])
                m = matcher.match(f"{e.get('title','')} {e.get('description') or ''}")
                if not keep(m, channel_is_area=True):
                    continue
                kept += 1
                r = _row(e, m, f"channel:{cid}", known)
                if not (m["umbrella"] or m["context_hits"]):
                    r["context_from_channel"] = True
                    r["score"] = max(r["score"] - 10, 25)
                _merge(leads, r)
            chstats[cid] = {"url": channel_url[cid], "search_hits": n, "uploads": len(rows), "kept": kept}
            log(f"channel {channel_url[cid]}: {len(rows)} uploads, {kept} kept")
            save_leads(leads)
    save_leads(leads)
    write_summary(leads, qstats, chstats)
    return {"queries": len(queries), "channels": len(chstats), "leads_before": before, "leads_after": len(leads),
            "new": len(leads) - before}


def write_summary(leads: dict, qstats: dict | None = None, chstats: dict | None = None) -> None:
    by_village: dict[str, list] = defaultdict(list)
    for r in leads.values():
        for s in r["villages"] or ["34-gaon"]:
            by_village[s].append(r)
    names = {v["slug"]: v["names"]["hi"] for v in load_villages()}
    chans = Counter(r["channel"] for r in leads.values())
    lines = [f"# YouTube leads ({date.today().isoformat()})", "",
             f"कुल {len(leads)} वीडियो; इनमें से {sum(1 for r in leads.values() if r['known'])} पहले से शोध-भंडार में हैं। "
             "यह कच्ची सूची है: हर पंक्ति में वे शब्द लिखे हैं जिनकी वजह से वीडियो चुना गया। सत्यापन बाद में।", "",
             "## गांव-वार", "", "| गांव | वीडियो | नए | सबसे मज़बूत शीर्षक |", "|---|---|---|---|"]
    for slug, rows in sorted(by_village.items(), key=lambda kv: -len(kv[1])):
        rows.sort(key=lambda r: -r["score"])
        new = sum(1 for r in rows if not r["known"])
        lines.append(f"| {names.get(slug, slug)} | {len(rows)} | {new} | {rows[0]['title'][:70].replace('|', '/')} |")
    missing = [names[s] for s in names if s != "34-gaon" and s not in by_village]
    lines += ["", f"**जिन गांवों का कोई वीडियो नहीं मिला:** {', '.join(missing) or 'कोई नहीं'}", "",
              "## सबसे ज़्यादा वीडियो वाले channel", "", "| channel | वीडियो |", "|---|---|"]
    for ch, n in chans.most_common(25):
        lines.append(f"| {ch.replace('|', '/')} | {n} |")
    if qstats:
        dead = [q for q, s in qstats.items() if s["kept"] == 0]
        lines += ["", f"## खोजें: {len(qstats)} चलीं, {len(dead)} से कुछ नहीं मिला", ""]
        best = sorted(qstats.items(), key=lambda kv: -kv[1]["kept"])[:15]
        lines += [f"- `{q}`: {s['kept']} काम के" for q, s in best]
    YT_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
