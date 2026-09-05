"""Ingest agent output -> classify -> resolve -> dedup -> score -> claims -> store."""
import json
from datetime import datetime, timezone
from pathlib import Path

import re

from .classify import LEXICON, classify_platform, classify_source_type, classify_media, classify_topics, classify_period, detect_language
from .dedup import find_duplicates
from .normalize import canonical_url
from .registry import get_village
from .resolve import resolve
from .schema import SourceRecord, source_id, validate_agent_record, AGENT_OPTIONAL
from .score import score_source
from .store import load_sources, save_sources, merge_source, append_run, load_claims, save_claims, load_verdicts
from .verify import build_claims


def _text_of(raw: dict) -> str:
    parts = [raw.get("title", ""), raw.get("summary", ""), " ".join(raw.get("evidence_snippets", []) or []),
             " ".join(raw.get("geo_mentions", []) or []), raw.get("url", "")]
    for c in raw.get("claims", []) or []:
        parts += [str(c.get("statement_hi", "")), str(c.get("statement_en", "")), str(c.get("snippet", ""))]
    return " ".join(p for p in parts if p)


def _strict_text(raw: dict) -> str:
    return " ".join([raw.get("title", ""), raw.get("name_form_matched", "") or "", " ".join(raw.get("evidence_snippets", []) or [])])


def canonical_claim_key(key: str) -> str:
    k = re.sub(r"[^a-z0-9]+", "_", str(key or "").strip().lower()).strip("_")
    return LEXICON.get("claim_key_aliases", {}).get(k, k)


def normalise_record(raw: dict, village: dict, run_id: str) -> SourceRecord:
    raw = {**AGENT_OPTIONAL, **raw}
    raw["claims"] = [{**c, "claim_key": canonical_claim_key(c.get("claim_key"))} for c in (raw.get("claims") or []) if isinstance(c, dict)]
    url = raw["url"].strip()
    key = canonical_url(url)
    platform = classify_platform(url)
    stype, reliability, primary_by_host = classify_source_type(url, raw.get("source_type", ""))
    text = _text_of(raw)
    rec = SourceRecord(
        id=source_id(key), village=village["slug"], url=url, url_key=key, title=raw["title"].strip(),
        platform=platform, source_type=stype, media_type=classify_media(url, platform, raw.get("media_type", "")),
        author=raw.get("author", "") or "", published_date=str(raw.get("published_date", "") or ""),
        language=raw.get("language") or detect_language(text),
        found_by_query=[raw["found_by_query"]] if isinstance(raw.get("found_by_query"), str) and raw["found_by_query"] else list(raw.get("found_by_query") or []),
        summary=raw.get("summary", "") or "", topics=classify_topics(text, raw.get("topics")),
        period=classify_period(text, raw.get("period", "")), geo_mentions=list(raw.get("geo_mentions") or []),
        direct_mention=raw.get("direct_mention"), name_form_matched=raw.get("name_form_matched", "") or "",
        evidence_snippets=list(raw.get("evidence_snippets") or []), entities=dict(raw.get("entities") or {}),
        license=raw.get("license", "") or "", attribution=raw.get("attribution", "") or "",
        is_primary=bool(raw.get("is_primary")) or primary_by_host, reliability=reliability,
        related_villages=list(raw.get("related_villages") or []), media=dict(raw.get("media") or {}),
        claims=list(raw.get("claims") or []), notes=raw.get("notes", "") or "", runs=[run_id],
    )
    rec.resolution = resolve(village, text, rec.direct_mention, rec.geo_mentions, _strict_text(raw))
    return rec


def ingest(slug: str, inbox_file: Path, run_id: str | None = None) -> dict:
    village = get_village(slug)
    run_id = run_id or datetime.now(timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    payload = json.loads(Path(inbox_file).read_text(encoding="utf-8"))
    raws = payload["sources"] if isinstance(payload, dict) else payload
    existing = load_sources(slug)
    stats = {"run_id": run_id, "file": str(inbox_file), "input": len(raws), "invalid": 0, "new": 0, "updated": 0, "errors": []}
    for raw in raws:
        errs = validate_agent_record(raw)
        if errs:
            stats["invalid"] += 1
            stats["errors"].append({"url": raw.get("url"), "errors": errs})
            continue
        rec = normalise_record(raw, village, run_id).to_dict()
        if rec["id"] in existing:
            stats["updated"] += 1
        else:
            stats["new"] += 1
        existing[rec["id"]] = merge_source(existing.get(rec["id"]), rec, run_id)
    rebuild(slug, existing)
    stats["total_after"] = len(existing)
    stats["at"] = datetime.now(timezone.utc).isoformat()
    append_run(slug, stats)
    return stats


PERSONAL_PROFILE = re.compile(r"linkedin\.com/in/|facebook\.com/profile\.php|facebook\.com/people/|instagram\.com/[^/]+/?$", re.I)


def privacy_check(r: dict):
    """Public profiles of private individuals are held for human review, never auto-published."""
    if PERSONAL_PROFILE.search(r["url"]):
        r["review_flags"] = sorted(set(r.get("review_flags", [])) | {"privacy_review"})
        if r["resolution"]["decision"] in ("accept", "context"):
            r["resolution"]["decision"] = "review"
            r["resolution"]["reasons"].append("personal profile page: human must confirm it is a public figure/page and consent is appropriate")


UMBRELLA_SLUG = "34-gaon"


def shared_umbrella_sources(slug: str) -> dict:
    """Umbrella-unit sources that explicitly relate to this village (by related_villages) corroborate its claims."""
    if slug == UMBRELLA_SLUG:
        return {}
    return {sid: s for sid, s in load_sources(UMBRELLA_SLUG).items() if slug in (s.get("related_villages") or [])
            and s.get("resolution", {}).get("decision") in ("accept", "context")}


def rebuild(slug: str, sources: dict | None = None) -> dict:
    """Recompute dedup, scores and claims for a village store (idempotent)."""
    sources = sources if sources is not None else load_sources(slug)
    village = get_village(slug)
    recs = list(sources.values())
    for r in recs:  # re-run resolution so registry edits (new variants/negatives) take effect
        for c in r.get("claims", []):
            c["claim_key"] = canonical_claim_key(c.get("claim_key"))
        r["resolution"] = resolve(village, _text_of(r), r.get("direct_mention"), r.get("geo_mentions"), _strict_text(r))
        privacy_check(r)
    find_duplicates(recs)
    shared = shared_umbrella_sources(slug)
    claims = build_claims({**shared, **sources}, verdicts=load_verdicts(slug))
    corroboration = {}
    for c in claims.values():
        if c["independent_sources"] >= 2:
            for sid in c["sources"]:
                corroboration[sid] = corroboration.get(sid, 0) + 1
    for r in recs:
        r["relevance"] = score_source(r, corroboration.get(r["id"], 0))
        flags = set(r.get("review_flags", []))
        flags.discard("resolution_review"); flags.discard("low_relevance"); flags.discard("duplicate")
        if r["resolution"]["decision"] == "review":
            flags.add("resolution_review")
        if r["relevance"]["band"] == "low" and r["resolution"]["decision"] != "reject":
            flags.add("low_relevance")
        if r.get("duplicate_of"):
            flags.add("duplicate")
        r["review_flags"] = sorted(flags)
    save_sources(slug, sources)
    save_claims(slug, claims)
    return {"sources": len(sources), "claims": len(claims)}
