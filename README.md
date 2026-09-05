# 34 Gaon of Mahajan: Cultural Preservation Research

Research repository for a cultural preservation website about the 33/34 villages of Lunkaransar tehsil (Mahajan sub-tehsil), Bikaner, Rajasthan, acquired for the Mahajan Field Firing Range in 1982 to 1984.

Prepared by the TechnoTaau Team (lead: Jakhar Singh).

## Contents

| Path | What it is |
|---|---|
| `docs/34-gaon-research-blueprint.md` | The full five-pillar research blueprint: village registry, legal timeline, cultural profile, present-day crisis, and website architecture, with source links and confidence tags. |
| `data/villages_34gaon.csv` | Registry of the 15 recovered village names plus 3 surviving sister villages, with evidence and status. |
| `data/resettlement_sites.csv` | Where the displaced families were allotted land (IGNP command: Ranjeetpura, Khajuwala, Pugal, Chhatargarh, Bajju and others). |
| `data/incidents.csv` | Incident register for the range and its periphery, 2014 to 2026. |
| `data/mffr_range_polygon.geojson` | The range boundary as drawn on OpenStreetMap (way 412765540), for the website map. |

| `gaon34/` | Research workflow package (query matrix, ingest pipeline, classification, entity resolution, dedup, scoring, verification, Hindi reports). See `docs/RESEARCH_WORKFLOW.md`. |
| `agents/` | Prompt templates for the Discovery Agent and Verification Agent. |
| `research/villages.json` | Village registry (the only input; add villages here). |
| `research/config/` | Query templates, classification lexicon, claim-key aliases. |
| `research/inbox/<slug>/` | Raw agent output per unit (discovery.json, verdicts.json). |
| `research/store/<slug>/` | Processed store per unit: sources.json, claims.json, record.json, report.md (Hindi), runs.json. |
| `research/INDEX.md` | Coverage index across all units. |
| `tests/` | 21 pytest tests for the pipeline. |

## Research status (first pass, 5 Sep 2026)

All 15 known units researched (umbrella + 14 villages): 122 source records, 62 unique URLs. Units flagged `budget_starved` in `runs.json` (Kolana, Ladera, Bhanabasti, Nathor) had fewer than 12 searches because the session search quota ran out and should be rerun first. Meusar and Ladera each have a same-name village elsewhere in Bikaner district; those hits are held in review, not accepted.

## Confidence tags

Every row and bullet carries one of: `confirmed` (primary or reputable source read), `press` (newspaper report), `community` (community-written history), `unverified` (snippet or social media only). Eighteen to nineteen village names are still missing and can only be recovered offline (1981 District Census Handbook, Bikaner Collectorate land acquisition notifications, Colonisation Commissioner MFFR Branch registers).
