"""Entity resolution: is this source about OUR village, or a same-name place elsewhere?

Never accept on name alone. Positive geographic context raises confidence, negative terms lower it.
"""
from .normalize import contains_term


def resolve(village: dict, text: str, agent_direct_mention=None, agent_geo=None) -> dict:
    reasons, score = [], 0.0
    names = village["all_names"]
    matched = [n for n in names if contains_term(text, n)]
    if matched:
        primary = village["names"]["en"], village["names"]["hi"]
        if any(m in primary for m in matched):
            score += 0.35
            reasons.append(f"primary name match: {[m for m in matched if m in primary][0]}")
        else:
            score += 0.25
            reasons.append(f"variant match: {matched[0]}")
    elif agent_direct_mention:
        score += 0.15
        reasons.append("agent reports direct mention (name not found in captured text)")
    else:
        reasons.append("village name not found in captured text")

    geo = village["geo"]
    strong = geo.get("sub_tehsil", []) + geo.get("tehsil", []) + geo.get("region", [])
    medium = geo.get("district", []) + geo.get("nearby", []) + geo.get("clans", [])
    weak = geo.get("state", [])
    corpus = text + " " + " ".join(agent_geo or [])
    s_hits = [g for g in strong if contains_term(corpus, g)]
    m_hits = [g for g in medium if contains_term(corpus, g)]
    w_hits = [g for g in weak if contains_term(corpus, g)]
    if s_hits:
        score += 0.35
        reasons.append(f"strong geo context: {s_hits[:3]}")
    if m_hits:
        score += 0.2 if not s_hits else 0.1
        reasons.append(f"district/nearby/clan context: {m_hits[:3]}")
    if w_hits and not (s_hits or m_hits):
        score += 0.05
        reasons.append("state-level context only")

    neg = [n for n in village.get("negative_terms", []) if contains_term(corpus, n)]
    if neg:
        penalty = 0.15 if (s_hits or m_hits) else 0.45
        score -= penalty
        reasons.append(f"negative/other-place signals: {neg[:3]}")
    if village.get("unit_type") == "umbrella":
        score = max(score, 0.6 if (matched and (s_hits or m_hits)) else score)

    score = max(0.0, min(1.0, round(score, 3)))
    if score >= 0.6:
        decision = "accept"
    elif score >= 0.35:
        decision = "review"
    else:
        decision = "reject"
    return {"decision": decision, "confidence": score, "reasons": reasons, "matched_names": matched,
            "geo_hits": s_hits + m_hits + w_hits, "negative_hits": neg}
