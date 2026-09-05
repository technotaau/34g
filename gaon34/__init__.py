"""34 Gaon research workflow: deterministic pipeline around agent-driven discovery.

Stages: Village Input -> Search Strategy (queries) -> Source Discovery (agents) ->
Content Retrieval/Extraction (agents) -> Classification -> Deduplication ->
Relevance Scoring -> Source Validation (entity resolution) -> Metadata Extraction ->
Storage -> Verification -> Review/Output (reports).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESEARCH_DIR = ROOT / "research"
CONFIG_DIR = RESEARCH_DIR / "config"
STORE_DIR = RESEARCH_DIR / "store"
INBOX_DIR = RESEARCH_DIR / "inbox"
AGENTS_DIR = ROOT / "agents"
