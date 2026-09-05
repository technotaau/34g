"""Data model. Sources are what agents discover; claims are facts extracted from sources; entities link them.

A SourceRecord is intentionally flat so agents can emit it as JSON. Computed fields are filled by the pipeline.
"""
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any

SOURCE_TYPES = {"news", "government", "legal", "archive", "census_mirror", "encyclopedia", "community_wiki", "video",
                "social", "blog", "book", "academic", "website", "image", "audio", "unknown"}
MEDIA_TYPES = {"text", "video", "audio", "image", "social_post", "document", "book", "map", "dataset"}
VERIFICATION_STATES = ("verified", "corroborated", "single-source", "unverified", "conflicting")

AGENT_REQUIRED = ("village", "url", "title")
AGENT_OPTIONAL = {
    "platform": "", "source_type": "", "media_type": "", "author": "", "published_date": "", "language": "",
    "found_by_query": "", "summary": "", "topics": [], "period": "", "geo_mentions": [], "direct_mention": None,
    "name_form_matched": "", "evidence_snippets": [], "entities": {}, "license": "", "attribution": "",
    "is_primary": None, "related_villages": [], "claims": [], "media": {}, "notes": "",
}


def source_id(url_key: str) -> str:
    return "src_" + hashlib.sha1(url_key.encode("utf-8")).hexdigest()[:12]


@dataclass
class SourceRecord:
    id: str
    village: str
    url: str
    url_key: str
    title: str
    platform: str = ""
    source_type: str = "unknown"
    media_type: str = "text"
    author: str = ""
    published_date: str = ""
    discovered_date: str = field(default_factory=lambda: date.today().isoformat())
    language: str = ""
    found_by_query: list = field(default_factory=list)
    summary: str = ""
    topics: list = field(default_factory=list)
    period: str = ""
    geo_mentions: list = field(default_factory=list)
    direct_mention: bool | None = None
    name_form_matched: str = ""
    evidence_snippets: list = field(default_factory=list)
    entities: dict = field(default_factory=dict)  # people, places, events, organizations
    license: str = ""
    attribution: str = ""
    is_primary: bool = False
    reliability: float = 0.5
    related_villages: list = field(default_factory=list)
    media: dict = field(default_factory=dict)  # video: channel, transcript, timestamps; image: caption, creator
    claims: list = field(default_factory=list)  # list of {claim_key, value, statement_hi, statement_en, snippet}
    resolution: dict = field(default_factory=dict)  # {decision, confidence, reasons}
    relevance: dict = field(default_factory=dict)  # {score, factors}
    duplicate_of: str = ""
    syndicate_group: str = ""
    review_flags: list = field(default_factory=list)
    runs: list = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_agent_record(raw: dict) -> list[str]:
    errors = []
    for k in AGENT_REQUIRED:
        if not raw.get(k):
            errors.append(f"missing {k}")
    if raw.get("topics") is not None and not isinstance(raw.get("topics"), list):
        errors.append("topics must be a list")
    if raw.get("claims") is not None:
        if not isinstance(raw["claims"], list):
            errors.append("claims must be a list")
        else:
            for c in raw["claims"]:
                if not isinstance(c, dict) or not c.get("claim_key") or c.get("value") in (None, ""):
                    errors.append("each claim needs claim_key and value")
                    break
    return errors
