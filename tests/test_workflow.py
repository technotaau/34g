import json
from pathlib import Path

import pytest

from gaon34 import normalize, dedup, resolve, score, verify, queries, registry, pipeline, store, report
from gaon34.classify import classify_platform, classify_source_type, classify_topics, classify_media


# ---------- normalisation & dedup ----------
def test_canonical_url_strips_tracking_and_aliases():
    a = normalize.canonical_url("https://m.youtube.com/watch?v=abc123&feature=share&utm_source=x")
    b = normalize.canonical_url("https://youtu.be/abc123?si=zz")
    c = normalize.canonical_url("https://www.youtube.com/shorts/abc123")
    assert a == b == c == "https://www.youtube.com/watch?v=abc123"
    assert normalize.canonical_url("http://m.facebook.com/Page/posts/1?mibextid=q") == "https://www.facebook.com/Page/posts/1"
    assert normalize.canonical_url("https://www.patrika.com/x/amp/") == normalize.canonical_url("https://patrika.com/x")


def test_hindi_normalisation_tolerates_nukta_and_anusvara():
    assert normalize.contains_term("चिडासर गांव", "चिड़ासर")
    assert normalize.contains_term("कुंभाणा में होली", "कुम्भाणा") is False  # conjunct differs: variants list must cover it
    assert normalize.contains_term("Kumbhana village", "kumbhana")
    assert normalize.contains_term("Kumbhanagar", "Kumbhana") is False


def test_find_duplicates_marks_same_url_near_title_and_syndication():
    recs = [
        {"id": "a", "url": "https://patrika.com/news/one", "url_key": "k1", "title": "34 गांवों को विस्थापित कर बनी महाजन फायरिंग रेंज"},
        {"id": "b", "url": "https://patrika.com/news/one?utm=1", "url_key": "k1", "title": "same"},
        {"id": "c", "url": "https://patrika.com/news/two", "url_key": "k2", "title": "34 गांवों को विस्थापित कर बनी महाजन फायरिंग रेंज!"},
        {"id": "d", "url": "https://bhaskar.com/news/three", "url_key": "k3", "title": "34 गांवों को विस्थापित कर बनी महाजन फायरिंग रेंज"},
    ]
    dedup.find_duplicates(recs)
    assert recs[1]["duplicate_of"] == "a"
    assert recs[2]["duplicate_of"] == "a"
    assert recs[3]["syndicate_group"] == recs[0]["syndicate_group"] == "syn_a"
    assert dedup.independent_hosts(recs) == {"patrika.com"}


# ---------- entity resolution ----------
def village(slug="bhojrasar"):
    return registry.get_village(slug)


def test_resolution_rejects_same_name_other_district():
    r = resolve.resolve(village(), "Bhojrasar village in Sardarshahar tehsil, Churu district, Rajasthan")
    assert r["decision"] == "reject"
    assert r["negative_hits"]


def test_resolution_accepts_with_strong_geo_context():
    r = resolve.resolve(village(), "भोजरासर से आकर महाजन में बसे राजूराम शर्मा, फायरिंग रेंज")
    assert r["decision"] == "accept" and r["confidence"] >= 0.6


def test_resolution_reviews_name_only():
    r = resolve.resolve(village(), "Bhojrasar is a nice place")
    assert r["decision"] == "review"


def test_resolution_no_name_no_context_is_reject():
    r = resolve.resolve(village(), "Some page about Rajasthan tourism")
    assert r["decision"] == "reject"


# ---------- classification ----------
def test_classification_by_host():
    assert classify_platform("https://www.youtube.com/watch?v=1") == "youtube"
    assert classify_source_type("https://indiankanoon.org/doc/1/") == ("legal", 0.9, True)
    assert classify_source_type("https://www.patrika.com/x")[0] == "news"
    assert classify_source_type("https://random-site.example/x")[0] == "website"
    assert classify_media("https://x.org/a.pdf", "x.org") == "document"
    assert "religion_temple" in classify_topics("गांव का प्राचीन मंदिर और मेला")
    assert "displacement" in classify_topics("villagers displaced by the firing range")


# ---------- queries ----------
def test_query_matrix_is_bilingual_tiered_and_deduplicated():
    qs = queries.generate_queries(village("kumbhana"))
    texts = [q["query"] for q in qs]
    assert len(texts) == len({t.lower() for t in texts})
    assert any("कुम्भाणा" in t for t in texts) and any("Kumbhana" in t for t in texts)
    assert qs[0]["tier"] == 1 and all(qs[i]["tier"] <= qs[i + 1]["tier"] for i in range(len(qs) - 1))
    assert {q["channel"] for q in qs} >= {"web", "news", "video", "social", "image", "book", "gov"}
    only_video = queries.generate_queries(village("kumbhana"), channels=["video"])
    assert only_video and all(q["channel"] == "video" for q in only_video)


def test_registry_add_village_is_data_only(tmp_path):
    p = tmp_path / "v.json"
    p.write_text(json.dumps({"defaults": {"geo": {"district": ["Bikaner"]}, "negative_terms": ["Churu"]}, "villages": []}), encoding="utf-8")
    registry.add_village("newgaon", "Newgaon", "नयागांव", ["Naya Gaon"], path=p)
    vs = registry.load_villages(p)
    assert vs[0]["slug"] == "newgaon" and "Naya Gaon" in vs[0]["all_names"] and "Churu" in vs[0]["negative_terms"]
    with pytest.raises(ValueError):
        registry.add_village("newgaon", "x", "y", path=p)


# ---------- verification ----------
def _src(i, host, stype, claims, primary=False):
    return {"id": f"s{i}", "url": f"https://{host}/p{i}", "source_type": stype, "is_primary": primary, "claims": claims, "resolution": {"decision": "accept"}}


def test_claim_status_ladder():
    c1 = {"claim_key": "acquisition_year", "value": "1984"}
    c2 = {"claim_key": "acquisition_year", "value": "1982"}
    c3 = {"claim_key": "founder", "value": "Nathu Dhatarwal"}
    srcs = {"s1": _src(1, "patrika.com", "news", [c1]), "s2": _src(2, "indiankanoon.org", "legal", [c2], True),
            "s3": _src(3, "jatland.com", "community_wiki", [c3]), "s4": _src(4, "hi.wikipedia.org", "encyclopedia", [c3])}
    claims = verify.build_claims(srcs)
    by_key = {}
    for c in claims.values():
        by_key.setdefault(c["claim_key"], []).append(c)
    ay = by_key["acquisition_year"]
    assert len(ay) == 2 and all(c["status"] == "conflicting" for c in ay)
    assert {c["value"] for c in ay} == {"1984", "1982"} and all(c["competing"] for c in ay)
    f = by_key["founder"][0]
    assert f["status"] == "corroborated" and f["independent_sources"] == 2
    single = verify.build_claims({"s2": srcs["s2"]})
    assert list(single.values())[0]["status"] == "single-source"
    weak = verify.build_claims({"s3": srcs["s3"]})
    assert list(weak.values())[0]["status"] == "unverified"
    strong2 = verify.build_claims({"s2": srcs["s2"], "s5": _src(5, "sansad.in", "government", [c2], True)})
    assert list(strong2.values())[0]["status"] == "verified"


def test_claim_ids_are_stable():
    c = {"claim_key": "x", "value": "Y"}
    a = verify.build_claims({"s1": _src(1, "a.com", "news", [c])})
    b = verify.build_claims({"s1": _src(1, "a.com", "news", [c])})
    assert list(a) == list(b)


# ---------- scoring ----------
def test_score_orders_true_hit_above_false_positive():
    good = {"resolution": {"matched_names": ["Bhojrasar"], "geo_hits": ["Mahajan", "Bikaner"], "confidence": 0.9, "negative_hits": []},
            "reliability": 0.75, "is_primary": False, "found_by_query": ["q1", "q2"], "evidence_snippets": ["x"], "claims": [{}], "published_date": "2022", "media_type": "text"}
    bad = {"resolution": {"matched_names": ["Bhojrasar"], "geo_hits": [], "confidence": 0.1, "negative_hits": ["Churu"]},
           "reliability": 0.75, "is_primary": False, "found_by_query": ["q1"], "evidence_snippets": [], "claims": [], "published_date": "", "media_type": "text"}
    assert score.score_source(good)["score"] > score.score_source(bad)["score"] + 30
    assert score.score_source(good)["band"] == "high" and score.score_source(bad)["band"] == "low"


# ---------- end-to-end ingest with rerun idempotence ----------
def test_ingest_rerun_does_not_duplicate(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STORE_DIR", tmp_path / "store")
    monkeypatch.setattr(store, "INDEX_DIR", tmp_path / "store" / "_index")
    monkeypatch.setattr(report, "STORE_DIR", tmp_path / "store")
    payload = {"village": "bhojrasar", "sources": [
        {"village": "bhojrasar", "url": "https://www.patrika.com/bikaner-news/mahajan-field-firing-range-7893463?utm_source=t", "title": "आंखों में उतर आता है आशियाना उजड़ने का दर्द",
         "summary": "भोजरासर से आकर महाजन में बसे राजूराम शर्मा", "found_by_query": "भोजरासर महाजन", "direct_mention": True,
         "claims": [{"claim_key": "resettlement_site", "value": "Mahajan", "statement_hi": "भोजरासर के परिवार महाजन में बसे"}]},
        {"village": "bhojrasar", "url": "https://en.wikipedia.org/wiki/Bhojrasar", "title": "Bhojrasar", "summary": "Bhojrasar is a village in Sardarshahar tehsil, Churu", "found_by_query": "Bhojrasar"},
        {"village": "bhojrasar", "url": "", "title": "broken"},
    ]}
    f = tmp_path / "in.json"
    f.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    s1 = pipeline.ingest("bhojrasar", f, run_id="r1")
    assert s1["new"] == 2 and s1["invalid"] == 1
    payload["sources"][0]["url"] = "https://patrika.com/bikaner-news/mahajan-field-firing-range-7893463/amp"
    payload["sources"][0]["found_by_query"] = "Bhojrasar Mahajan"
    f.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    s2 = pipeline.ingest("bhojrasar", f, run_id="r2")
    assert s2["new"] == 0 and s2["updated"] == 2 and s2["total_after"] == 2
    srcs = store.load_sources("bhojrasar")
    pat = next(s for s in srcs.values() if "patrika" in s["url"])
    assert set(pat["found_by_query"]) == {"भोजरासर महाजन", "Bhojrasar Mahajan"} and pat["runs"] == ["r1", "r2"]
    assert pat["resolution"]["decision"] == "accept" and pat["source_type"] == "news" and pat["language"] == "hi"
    wiki = next(s for s in srcs.values() if "wikipedia" in s["url"])
    assert wiki["resolution"]["decision"] == "reject"
    rec = report.build_record("bhojrasar")
    assert rec["counts"]["accepted"] == 1 and rec["counts"]["rejected"] == 1
    md = report.render_report("bhojrasar", rec)
    assert "भोजरासर" in md and "resettlement_site" in md
    assert (tmp_path / "store" / "_index" / "url_index.json").exists()


def test_repository_documents_count_as_independent():
    c = {"claim_key": "notif_date", "value": "1985-11-23"}
    a = _src(1, "indiankanoon.org", "legal", [c], True); a["url"] = "https://indiankanoon.org/doc/1/"; a["url_key"] = a["url"]
    b = _src(2, "indiankanoon.org", "legal", [c], True); b["url"] = "https://indiankanoon.org/doc/2/"; b["url_key"] = b["url"]
    claims = verify.build_claims({"s1": a, "s2": b})
    assert list(claims.values())[0]["status"] == "verified"
    n1 = _src(3, "patrika.com", "news", [c]); n2 = _src(4, "patrika.com", "news", [c])
    assert list(verify.build_claims({"s3": n1, "s4": n2}).values())[0]["independent_sources"] == 1


def test_agent_downgrade_of_source_type_is_honoured():
    assert classify_source_type("https://hi.wikipedia.org/wiki/सदस्य:x", "community_wiki") == ("community_wiki", 0.45, False)
    assert classify_source_type("https://indiankanoon.org/doc/1/", "blog") == ("blog", 0.4, False)
    assert classify_source_type("https://www.patrika.com/x", "government")[0] == "news"  # upgrades ignored


def test_direct_mention_false_uses_strict_text_and_yields_context():
    v = village()
    # agent note mentions the name while denying it; title/evidence do not
    r = resolve.resolve(v, "Bhojoosar village Bikaner. Note: not the same as Bhojrasar of the firing range", False, ["Bikaner"], strict_text="Bhojoosar Village in Bikaner")
    assert r["decision"] != "accept" and r["confidence"] <= 0.55
    r2 = resolve.resolve(v, "Mahajan Field Firing Range 34 villages displaced, Lunkaransar", False, ["Mahajan"], strict_text="महाजन फायरिंग रेंज 34 गांव")
    assert r2["decision"] == "context"
    r3 = resolve.resolve(v, "भोजरासर से आकर महाजन में बसे", False, [], strict_text="भोजरासर से आकर महाजन में बसे")
    assert r3["decision"] == "review" and r3["confidence"] <= 0.55  # named in title but agent unsure


def test_same_headline_different_years_not_duplicate():
    recs = [{"id": "a", "url": "https://patrika.com/a", "url_key": "a", "title": "आंखों में उतर आता है आशियाना उजड़ने का दर्द", "published_date": "2018-11-05"},
            {"id": "b", "url": "https://patrika.com/b", "url_key": "b", "title": "आंखों में उतर आता है आशियाना उजड़ने का दर्द", "published_date": "2022-11-29"},
            {"id": "c", "url": "https://patrika.com/c", "url_key": "c", "title": "आंखों में उतर आता है आशियाना उजड़ने का दर्द", "published_date": ""}]
    dedup.find_duplicates(recs)
    assert recs[1]["duplicate_of"] == "" and recs[2]["duplicate_of"] == "a"


def test_personal_profiles_are_held_for_privacy_review():
    r = {"url": "https://www.linkedin.com/in/someone-kumbhana", "resolution": {"decision": "accept", "reasons": []}, "review_flags": []}
    pipeline.privacy_check(r)
    assert r["resolution"]["decision"] == "review" and "privacy_review" in r["review_flags"]
    r2 = {"url": "https://www.facebook.com/RajasthanPatrika/posts/1", "resolution": {"decision": "accept", "reasons": []}, "review_flags": []}
    pipeline.privacy_check(r2)
    assert r2["resolution"]["decision"] == "accept"
