"""Village registry: the only input the workflow needs to know about a research unit."""
import json
from . import RESEARCH_DIR

VILLAGES_FILE = RESEARCH_DIR / "villages.json"


def _load():
    return json.loads(VILLAGES_FILE.read_text(encoding="utf-8"))


def load_villages(path=None) -> list[dict]:
    data = json.loads((path or VILLAGES_FILE).read_text(encoding="utf-8"))
    defaults = data.get("defaults", {})
    out = []
    for v in data["villages"]:
        v = dict(v)
        geo = dict(defaults.get("geo", {}))
        geo.update(v.get("geo", {}))
        v["geo"] = geo
        neg = list(defaults.get("negative_terms", [])) + list(v.get("disambiguation", {}).get("negative_terms", []))
        v["negative_terms"] = neg
        v.setdefault("unit_type", "village")
        names = v["names"]
        variants = [names["en"], names["hi"]] + list(names.get("variants", []))
        seen, uniq = set(), []
        for x in variants:
            if x and x.lower() not in seen:
                seen.add(x.lower())
                uniq.append(x)
        v["all_names"] = uniq
        out.append(v)
    return out


def get_village(slug: str, path=None) -> dict:
    for v in load_villages(path):
        if v["slug"] == slug:
            return v
    raise KeyError(f"unknown village slug: {slug}")


def add_village(slug: str, en: str, hi: str, variants=None, status="acquired", negative_terms=None, notes="", path=None):
    """Append a village without touching the workflow. Returns the new entry."""
    p = path or VILLAGES_FILE
    data = json.loads(p.read_text(encoding="utf-8"))
    if any(v["slug"] == slug for v in data["villages"]):
        raise ValueError(f"slug exists: {slug}")
    entry = {"slug": slug, "names": {"en": en, "hi": hi, "variants": list(variants or [])}, "status": status, "notes": notes}
    if negative_terms:
        entry["disambiguation"] = {"negative_terms": list(negative_terms)}
    data["villages"].append(entry)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry
