"""Build prompts for the two agents from templates in agents/ plus the village's query matrix."""
import json
from . import AGENTS_DIR, INBOX_DIR
from .queries import generate_queries
from .registry import get_village
from .store import load_sources, load_claims
from .verify import needs_verification


def discovery_prompt(slug: str, budget: int = 30, max_tier: int = 3, channels=None) -> str:
    v = get_village(slug)
    tpl = (AGENTS_DIR / "discovery.md").read_text(encoding="utf-8")
    queries = generate_queries(v, max_tier=max_tier, channels=channels)
    known = load_sources(slug)
    known_urls = sorted({s["url"] for s in known.values()})
    out_path = INBOX_DIR / slug / "discovery.json"
    geo = v["geo"]
    ctx = {"slug": slug, "name_en": v["names"]["en"], "name_hi": v["names"]["hi"], "all_names": v["all_names"],
           "unit_type": v.get("unit_type", "village"), "status": v.get("status"), "notes": v.get("notes", ""),
           "geo": {k: geo.get(k, []) for k in ("state", "district", "tehsil", "sub_tehsil", "region", "nearby", "clans")},
           "negative_terms": v.get("negative_terms", [])}
    return (tpl.replace("{{VILLAGE_JSON}}", json.dumps(ctx, ensure_ascii=False, indent=1))
               .replace("{{QUERIES}}", "\n".join(f"- [T{q['tier']}/{q['channel']}] {q['query']}" for q in queries))
               .replace("{{BUDGET}}", str(budget))
               .replace("{{KNOWN_URLS}}", "\n".join(f"- {u}" for u in known_urls) or "- (none yet)")
               .replace("{{OUTPUT_PATH}}", str(out_path)))


def verification_prompt(slug: str, max_claims: int = 25) -> str:
    v = get_village(slug)
    tpl = (AGENTS_DIR / "verification.md").read_text(encoding="utf-8")
    claims = needs_verification(load_claims(slug))
    claims = sorted(claims, key=lambda c: (c["status"] != "conflicting", -len(c["sources"])))[:max_claims]
    sources = load_sources(slug)
    slim = []
    for c in claims:
        slim.append({"id": c["id"], "claim_key": c["claim_key"], "value": c["value"], "statement_hi": c.get("statement_hi", ""),
                     "status": c["status"], "competing": c.get("competing", []),
                     "sources": [{"id": sid, "url": sources[sid]["url"], "title": sources[sid]["title"]} for sid in c["sources"] if sid in sources]})
    out_path = INBOX_DIR / slug / "verdicts.json"
    return (tpl.replace("{{VILLAGE}}", f"{v['names']['hi']} / {v['names']['en']} (slug: {slug})")
               .replace("{{CLAIMS_JSON}}", json.dumps(slim, ensure_ascii=False, indent=1))
               .replace("{{OUTPUT_PATH}}", str(out_path)))
