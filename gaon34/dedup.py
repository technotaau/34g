"""Exact and near-duplicate detection plus syndication linking across villages."""
from .normalize import tokens, jaccard, host_of

NEAR_DUP_THRESHOLD = 0.8


def find_duplicates(records: list[dict]) -> list[dict]:
    """Mutates records: sets duplicate_of (same url_key or near-identical title on same host)
    and syndicate_group (near-identical title on different hosts). First-seen record is canonical."""
    by_key: dict[str, dict] = {}
    fps: list[tuple[set, dict]] = []
    for r in records:
        r["duplicate_of"] = r.get("duplicate_of") or ""
        r["syndicate_group"] = r.get("syndicate_group") or ""
        k = r["url_key"]
        if k in by_key and by_key[k]["id"] != r["id"]:
            r["duplicate_of"] = by_key[k]["id"]
            continue
        by_key.setdefault(k, r)
        t = tokens(r.get("title", ""))
        if len(t) < 3:
            fps.append((t, r))
            continue
        for ft, other in fps:
            if other is r or len(ft) < 3:
                continue
            if jaccard(t, ft) >= NEAR_DUP_THRESHOLD:
                if host_of(r["url"]) == host_of(other["url"]):
                    r["duplicate_of"] = other["duplicate_of"] or other["id"]
                else:
                    g = other["syndicate_group"] or ("syn_" + other["id"])
                    other["syndicate_group"] = g
                    r["syndicate_group"] = g
                break
        fps.append((t, r))
    return records


def independent_hosts(records: list[dict]) -> set[str]:
    """Hosts of non-duplicate, non-syndicated records (one per syndicate group)."""
    hosts, groups = set(), set()
    for r in records:
        if r.get("duplicate_of"):
            continue
        g = r.get("syndicate_group")
        if g:
            if g in groups:
                continue
            groups.add(g)
        hosts.add(host_of(r["url"]))
    return hosts
