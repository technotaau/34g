"""Relevance scoring 0-100 to rank sources and separate real hits from false positives."""
from datetime import date


def _year(published: str):
    try:
        return int(str(published)[:4])
    except (TypeError, ValueError):
        return None


def score_source(rec: dict, corroboration_count: int = 0) -> dict:
    f = {}
    res = rec.get("resolution", {})
    conf = res.get("confidence", 0.0)
    f["name_match"] = 30 if any(m for m in res.get("matched_names", [])) else (10 if rec.get("direct_mention") else 0)
    f["geo_match"] = min(20, 10 * len(res.get("geo_hits", []))) if res.get("geo_hits") else 0
    f["resolution_conf"] = round(15 * conf)
    f["credibility"] = round(15 * float(rec.get("reliability", 0.4)))
    f["primary"] = 8 if rec.get("is_primary") else 0
    f["corroboration"] = min(9, 3 * corroboration_count)
    f["queries"] = min(6, 2 * len(rec.get("found_by_query", [])))
    f["evidence"] = min(6, 2 * len(rec.get("evidence_snippets", [])))
    f["claims"] = min(6, 2 * len(rec.get("claims", [])))
    y = _year(rec.get("published_date"))
    f["recency"] = 3 if y and y >= date.today().year - 3 else (1 if y else 0)
    f["media"] = 3 if rec.get("media_type") in ("video", "image", "audio", "document", "book") else 0
    f["negative"] = -25 if res.get("negative_hits") and not res.get("geo_hits") else (-8 if res.get("negative_hits") else 0)
    total = max(0, min(100, sum(f.values())))
    band = "high" if total >= 65 else ("medium" if total >= 40 else "low")
    return {"score": total, "band": band, "factors": f}
