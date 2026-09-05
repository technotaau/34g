"""Claims, evidence and verification status. Conflicts are preserved, never silently resolved."""
import hashlib
from collections import defaultdict
from .normalize import norm_text, host_of

import re

STRONG_TYPES = {"government", "legal", "archive", "academic", "book"}


def norm_value(v) -> str:
    """Compare claim values on their core: drop parentheticals, slash/comma-separated glosses, unit words."""
    s = str(v)
    s = re.sub(r"\(.*?\)", " ", s)
    s = s.split(" / ")[0]
    s = re.sub(r"\b(per|as per|cited|generally|approx\.?|about)\b.*$", " ", s, flags=re.I)
    return norm_text(s)
REPOSITORY_HOSTS = ("indiankanoon.org", "sansad.in", "archive.org", "books.google", "wikipedia.org", "youtube.com", "facebook.com")


def independence_key(s: dict) -> str:
    """Same newspaper = one voice; but each judgment/record/video on a repository host is a distinct document."""
    if s.get("syndicate_group"):
        return s["syndicate_group"]
    h = host_of(s["url"])
    if any(r in h for r in REPOSITORY_HOSTS):
        return s.get("url_key") or s["url"]
    return h


def build_claims(sources: dict[str, dict], existing: dict | None = None, verdicts: dict | None = None) -> dict:
    """Group per-source claims by claim_key. Returns {claim_id: claim}."""
    groups: dict[str, list] = defaultdict(list)
    for s in sources.values():
        if s.get("duplicate_of") or s.get("resolution", {}).get("decision") == "reject":
            continue
        for c in s.get("claims", []):
            groups[c["claim_key"]].append((s, c))
    claims = {}
    for key, items in groups.items():
        by_value: dict[str, dict] = {}
        for s, c in items:
            vk = norm_value(c["value"])
            e = by_value.setdefault(vk, {"value": c["value"], "statement_hi": c.get("statement_hi", ""), "statement_en": c.get("statement_en", ""),
                                         "sources": [], "hosts": set(), "strong": False, "snippets": []})
            e["sources"].append(s["id"])
            e["hosts"].add(independence_key(s))
            e["strong"] = e["strong"] or s.get("source_type") in STRONG_TYPES or bool(s.get("is_primary"))
            if c.get("snippet"):
                e["snippets"].append({"source": s["id"], "text": c["snippet"]})
            if not e["statement_hi"] and c.get("statement_hi"):
                e["statement_hi"] = c["statement_hi"]
        conflicting = len(by_value) > 1
        for vk, e in by_value.items():
            cid = "clm_" + key + "_" + hashlib.sha1(vk.encode("utf-8")).hexdigest()[:8]
            n_indep = len(e["hosts"])
            if conflicting:
                status = "conflicting"
            elif n_indep >= 2 and e["strong"]:
                status = "verified"
            elif n_indep >= 2:
                status = "corroborated"
            elif e["strong"]:
                status = "single-source"
            else:
                status = "unverified"
            confidence = {"verified": 0.9, "corroborated": 0.7, "single-source": 0.5, "unverified": 0.3, "conflicting": 0.4}[status]
            if e["strong"] and conflicting:
                confidence = 0.55
            claim = {"id": cid, "claim_key": key, "value": e["value"], "statement_hi": e["statement_hi"], "statement_en": e["statement_en"],
                     "sources": sorted(set(e["sources"])), "independent_sources": n_indep, "has_strong_source": e["strong"],
                     "status": status, "confidence": confidence, "evidence": e["snippets"],
                     "competing": [o["value"] for ok, o in by_value.items() if ok != vk]}
            if verdicts and cid in verdicts:
                v = verdicts[cid]
                claim["agent_verdict"] = v
                if v.get("status") in ("verified", "corroborated", "conflicting", "unverified", "single-source"):
                    claim["status"] = v["status"]
                    claim["confidence"] = float(v.get("confidence", claim["confidence"]))
                if v.get("preferred") and conflicting:
                    claim["preferred_by_agent"] = v["preferred"]
            claims[cid] = claim
    return claims


def needs_verification(claims: dict) -> list[dict]:
    return [c for c in claims.values() if c["status"] in ("conflicting", "single-source", "unverified")]
