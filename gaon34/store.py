"""Per-village JSON store + global URL index. Re-runs merge instead of duplicating."""
import json
from datetime import date
from . import STORE_DIR

INDEX_DIR = STORE_DIR / "_index"


def village_dir(slug: str):
    d = STORE_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False), encoding="utf-8")


def load_sources(slug: str) -> dict:
    return _read(village_dir(slug) / "sources.json", {})


def save_sources(slug: str, sources: dict):
    _write(village_dir(slug) / "sources.json", sources)
    idx = load_url_index()
    for s in sources.values():
        idx.setdefault(s["url_key"], {"villages": [], "first_seen": s.get("discovered_date", date.today().isoformat())})
        if slug not in idx[s["url_key"]]["villages"]:
            idx[s["url_key"]]["villages"].append(slug)
    _write(INDEX_DIR / "url_index.json", idx)


def load_url_index() -> dict:
    return _read(INDEX_DIR / "url_index.json", {})


def load_claims(slug: str) -> dict:
    return _read(village_dir(slug) / "claims.json", {})


def save_claims(slug: str, claims: dict):
    _write(village_dir(slug) / "claims.json", claims)


def load_verdicts(slug: str) -> dict:
    return _read(village_dir(slug) / "verdicts.json", {})


def save_verdicts(slug: str, verdicts: dict):
    _write(village_dir(slug) / "verdicts.json", verdicts)


def save_record(slug: str, record: dict):
    _write(village_dir(slug) / "record.json", record)


def load_runs(slug: str) -> list:
    return _read(village_dir(slug) / "runs.json", [])


def append_run(slug: str, run: dict):
    runs = load_runs(slug)
    runs.append(run)
    _write(village_dir(slug) / "runs.json", runs)


def merge_source(existing: dict | None, new: dict, run_id: str) -> dict:
    """Keep first-seen metadata, union list fields, refresh agent-provided text if longer."""
    if not existing:
        new["runs"] = [run_id]
        return new
    out = dict(existing)
    for k in ("found_by_query", "topics", "geo_mentions", "evidence_snippets", "related_villages", "review_flags"):
        out[k] = sorted(set(existing.get(k, [])) | set(new.get(k, [])))
    for k in ("summary", "author", "published_date", "license", "attribution", "language", "period", "name_form_matched", "notes"):
        if len(str(new.get(k) or "")) > len(str(existing.get(k) or "")):
            out[k] = new[k]
    seen = {(c["claim_key"], str(c["value"])) for c in existing.get("claims", [])}
    out["claims"] = existing.get("claims", []) + [c for c in new.get("claims", []) if (c["claim_key"], str(c["value"])) not in seen]
    ent = dict(existing.get("entities", {}))
    for k, v in (new.get("entities") or {}).items():
        ent[k] = sorted(set(ent.get(k, [])) | set(v or []))
    out["entities"] = ent
    media = dict(existing.get("media", {}))
    media.update({k: v for k, v in (new.get("media") or {}).items() if v})
    out["media"] = media
    out["direct_mention"] = existing.get("direct_mention") or new.get("direct_mention")
    out["is_primary"] = existing.get("is_primary") or new.get("is_primary")
    out["runs"] = sorted(set(existing.get("runs", [])) | {run_id})
    return out
