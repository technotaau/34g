# 34 Gaon Research Workflow (शोध कार्यप्रवाह)

Maintained by TechnoTaau Team (Jakhar Singh). Purpose: find, organise and validate publicly available content about each of the 34 villages so a Hindi website can present legacy, culture, history, families and today's diaspora with verifiable sources.

## 1. Architecture

```
Village Input (research/villages.json)
   │
   ▼
Search Strategy ── gaon34/queries.py + research/config/query_templates.json
   │                (bilingual, tiered, per-channel matrix; data-driven, extensible)
   ▼
Source Discovery + Content Retrieval/Extraction ── Discovery Agent (agents/discovery.md)
   │                one Claude subagent per unit, fixed search budget, all channels,
   │                writes research/inbox/<slug>/discovery.json (strict schema)
   ▼
Ingest (gaon34/pipeline.py)
   ├─ Classification ── gaon34/classify.py (platform, source type, reliability, media, topics, period, language)
   ├─ Entity Resolution ── gaon34/resolve.py (name + geographic context − negative terms → accept/review/reject)
   ├─ Deduplication ── gaon34/dedup.py (canonical URL, near-duplicate titles, syndication groups)
   ├─ Relevance Scoring ── gaon34/score.py (0–100, factor breakdown)
   ├─ Claims & Verification ── gaon34/verify.py (verified/corroborated/single-source/unverified/conflicting)
   └─ Storage ── gaon34/store.py (research/store/<slug>/sources.json, claims.json, runs.json + global URL index)
   ▼
Verification Agent (agents/verification.md) ── only for conflicting / single-source claims → verdicts.json
   ▼
Review/Output ── gaon34/report.py → record.json (machine) + report.md (Hindi, answers the 15 standard questions)
                 research/INDEX.md (all units)
```

Every village is an independent unit. Adding a village is a data change (one JSON object or `add-village`), never a code change.

### Agents (only two, by design)
| Agent | Why it exists | Input | Output |
|---|---|---|---|
| Discovery Agent | Needs the web and judgment: runs the query matrix across web, news, YouTube, Facebook (public), images, books, archives, government records; extracts metadata and short evidence | prompt from `python -m gaon34 prompt <slug>` | `research/inbox/<slug>/discovery.json` |
| Verification Agent | Cross-checks claims the pipeline marks conflicting / single-source / unverified | prompt from `python -m gaon34 verify-prompt <slug>` | `research/inbox/<slug>/verdicts.json` |

Classification, dedup, entity resolution, scoring and status assignment are deterministic Python. They cost no tokens, are unit-tested, and can be re-run any time (`build`). Separate per-media agents were rejected: they multiply cost and lose cross-channel context.

## 2. Data model (research/store/<slug>/)
- `sources.json`: `{source_id: SourceRecord}`. Fields: village, url (original, never altered), url_key, title, platform, source_type, media_type, author, published_date, discovered_date, language, found_by_query[], summary, topics[], period, geo_mentions[], direct_mention, name_form_matched, evidence_snippets[], entities{people,places,events,organizations}, license, attribution, is_primary, reliability, related_villages[], media{channel,uploader,caption,creator,transcript_available,timestamps,book_title,pages}, claims[], resolution{decision,confidence,reasons}, relevance{score,band,factors}, duplicate_of, syndicate_group, review_flags[], runs[], notes.
- `claims.json`: `{claim_id: Claim}` grouped by `claim_key`; each has value, statement_hi/en, sources[], independent_sources, has_strong_source, status, confidence, evidence[], competing[] (other values for the same key), agent_verdict.
- `verdicts.json`: Verification Agent output keyed by claim id.
- `record.json`: the per-village research record (questions → sources, media sections, entities, well-supported vs needs-verification claims, manual-review list).
- `report.md`: Hindi report generated from record.json.
- `runs.json`: ingest history (run id, counts, invalid records).
- `research/store/_index/url_index.json`: url_key → villages, for cross-village dedup and rerun detection.

People, places, events and organisations live in `entities` on each source and are aggregated in `record.json`. Relationships village↔source are the `village` and `related_villages` fields. This is enough for a site generator; a relational DB can be derived later.

## 3. Key rules
- **Entity resolution:** a source is accepted only when the village name (any registered spelling) co-occurs with geographic context (Mahajan / Lunkaransar / firing range / Bikaner / nearby villages / clans). Negative terms (other districts, states, same-name places) push it to review or reject. Rejected sources are kept, never deleted.
- **Verification ladder:** `verified` = 2+ independent sources incl. a strong one (government, legal, archive, academic, book, or primary); `corroborated` = 2+ independent; `single-source` = one strong source; `unverified` = one weak source; `conflicting` = same claim_key, different values (all values kept, competing values listed). Independence = different publisher, except document repositories (indiankanoon, sansad, archive.org, Google Books, Wikipedia, YouTube, Facebook) where each document counts.
- **Dedup:** canonical URL (tracking params, amp, mobile hosts, youtu.be/shorts → watch?v=), near-identical titles on one host = duplicate, on different hosts = syndicate group (counts once).
- **Reruns:** ingest merges by url_key; list fields are unioned, longer text wins, `runs[]` records every run. Known URLs are injected into the next discovery prompt so agents do not re-add them.
- **Safety:** public content only; no login, paywall, CAPTCHA or rate-limit circumvention; metadata + short quotes, no bulk downloads.

## 4. How to run

```bash
python3 -m pytest -q tests                      # 16 tests
python3 -m gaon34 villages                      # list units
python3 -m gaon34 add-village --slug xyz --en Xyz --hi ज़ाइज़ --variants "Xyz Mahajan" "जाइज" --negative "Nagaur"
python3 -m gaon34 queries kumbhana --tier 1     # inspect search matrix
python3 -m gaon34 prompt kumbhana --budget 25 > /tmp/prompt_kumbhana.md
#   → give that file to a Discovery Agent (Claude subagent with WebSearch/WebFetch, Sonnet is sufficient)
python3 -m gaon34 ingest kumbhana               # reads research/inbox/kumbhana/discovery.json, rebuilds record + report + INDEX
python3 -m gaon34 verify-prompt kumbhana > /tmp/verify_kumbhana.md   # only if needs_verification is non-empty
python3 -m gaon34 ingest-verdicts kumbhana      # reads research/inbox/kumbhana/verdicts.json
python3 -m gaon34 build --all                   # recompute everything after registry/config/code changes
python3 -m gaon34 status
```

Batch (complete list or only units without sources yet):
```bash
python3 -m gaon34 prompts --out /tmp/prompts --pending --budget 25
# dispatch one Discovery Agent per prompt file (5 in parallel is a sensible cap), then:
for s in $(python3 -m gaon34 villages | awk '{print $1}'); do [ -f research/inbox/$s/discovery.json ] && python3 -m gaon34 ingest $s; done
```

Adding a new village later: append to `research/villages.json` (or `add-village`), run `prompt` → agent → `ingest`. Nothing else changes. Re-running an existing village: same commands; the agent receives the known URLs and the store merges.

## 5. Extending
- New search angle: add a template to `research/config/query_templates.json` (placeholders documented in the file).
- New platform or credibility rule: edit `research/config/lexicon.json`.
- New topic vocabulary (e.g. `migration_diaspora`): add keywords in `lexicon.json`; reports pick it up via `QUESTIONS` in `gaon34/report.py`.
- Scoring weights: `gaon34/score.py` (single function, factor dict is stored on each source for auditability).

## 6. Getting content out of videos (burned-in subtitles and speech)

Many village vlogs have no YouTube caption track but carry burned-in subtitles. `scripts/video_extract.py` turns a local video file into timestamped research notes:

```bash
apt-get install -y ffmpeg tesseract-ocr tesseract-ocr-hin && pip install faster-whisper
python3 scripts/video_extract.py /path/to/video.mp4 --out research/inbox/<slug>/<youtube_id>.content.json --lang hin+eng --whisper small
```

It samples one frame per second, OCRs the bottom subtitle band (Hindi + English), collapses repeated lines into `[start–end] text`, and transcribes speech with Whisper (CPU, `small` model by default; use `medium` for better Rajasthani/Hindi accuracy if time allows). Output: `<id>.content.json` and a readable `<id>.content.md`. Feed the useful lines back into the source record as `evidence_snippets` or `media.timestamps`, then re-run `ingest`.

Rules: obtain the file legitimately (download it yourself from YouTube on your own account/device, or ask the uploader). The script never copies media into the repository, and this cloud environment cannot fetch YouTube media directly (YouTube blocks datacenter downloads with a sign-in check; do not work around it with cookies). Quote sparingly and attribute the uploader.

## 7. Ingesting a YouTube video in one command

```bash
python3 -m gaon34 video <slug> "<youtube url>" [--related 34-gaon other-slug] \
        [--drive-id <link-shared Google Drive file id> | --media /path/video.mp4] [--every 20] [--ocr-band 0.88 --ocr-lang hin+eng] [--whisper small]
```

What it does, in order: pulls public metadata, description, tags, location, caption tracks (manual and auto, if any) and public comments with yt-dlp (mobile-web client, no media); writes `research/inbox/<slug>/yt_<id>.meta.json`, `video_<id>.json` (a source record in the agent schema) and any `yt_<id>.captions.<lang>.txt`; if media is supplied, extracts a still every N seconds into `research/media/<slug>/<id>/frames/` with `manifest.json` and a timestamped `contact_sheet.png`, OCRs burned-in subtitles into `<id>.content.json/.md`, optionally runs Whisper; then ingests, rebuilds the report and index.

Notes: YouTube blocks media downloads from this environment, so frames and OCR need a Drive upload shared as "Anyone with the link" (`--drive-id`), or a local file. Frame descriptions in the manifest are blank until a person (or the orchestrating session, by viewing `contact_sheet.png`) annotates them, as was done for Berawala. Claims are not auto-generated from a video; add them by editing `video_<id>.json` after viewing, then re-run `ingest`. Add the village first if it is new (`add-village` or `research/villages.json`); the resolver decides accept/context/review from the title, description and comments.
