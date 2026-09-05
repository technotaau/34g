"""Search-matrix generation from data-driven templates. Extensible: edit research/config/query_templates.json."""
import json
from . import CONFIG_DIR

TEMPLATES_FILE = CONFIG_DIR / "query_templates.json"


def _first(lst, default=""):
    return lst[0] if lst else default


def _geo_fields(v: dict) -> dict:
    g = v["geo"]
    hi = lambda key: next((x for x in g.get(key, []) if any("ऀ" <= ch <= "ॿ" for ch in x)), "")
    en = lambda key: next((x for x in g.get(key, []) if not any("ऀ" <= ch <= "ॿ" for ch in x)), "")
    return {"district_en": en("district"), "district_hi": hi("district"), "tehsil_en": en("tehsil"), "tehsil_hi": hi("tehsil"),
            "subtehsil_en": en("sub_tehsil"), "subtehsil_hi": hi("sub_tehsil"), "state_en": en("state"), "state_hi": hi("state")}


def generate_queries(village: dict, max_tier: int = 3, channels=None, max_variants: int = 6, templates_path=None) -> list[dict]:
    """Return ordered list of {id, tier, channel, lang, query}. Tier 1 first. Deduplicated."""
    templates = json.loads((templates_path or TEMPLATES_FILE).read_text(encoding="utf-8"))["templates"]
    fields = {"en": village["names"]["en"], "hi": village["names"]["hi"], **_geo_fields(village)}
    out, seen = [], set()

    def push(t, q):
        q = " ".join(q.split())
        if q.lower() in seen:
            return
        seen.add(q.lower())
        out.append({"id": t["id"], "tier": t["tier"], "channel": t["channel"], "lang": t["lang"], "query": q})

    for t in sorted(templates, key=lambda x: x["tier"]):
        if t["tier"] > max_tier or (channels and t["channel"] not in channels):
            continue
        if t.get("per_variant"):
            geo_words = {w.lower() for k in ("district_en", "district_hi", "tehsil_en", "tehsil_hi", "subtehsil_en", "subtehsil_hi") for w in fields[k].split()}
            for var in village["all_names"][:max_variants]:
                if any(w.lower() in geo_words for w in var.split()):
                    continue  # variant already carries a geo term; core templates cover it
                push(t, t["template"].format(variant=var, **fields))
        else:
            push(t, t["template"].format(variant=fields["en"], **fields))
    if village.get("unit_type") == "umbrella":
        # umbrella unit: the variants themselves are the queries
        for var in village["all_names"]:
            push({"id": "umbrella_variant", "tier": 1, "channel": "web", "lang": "any"}, var)
    return out
