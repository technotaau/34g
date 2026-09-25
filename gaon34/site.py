"""Static site generator for 34gaon.com (Phase 1 preview).

Reads the research store (research/villages.json, research/store/*/record.json,
research/media/*/manifest.json, data/*.csv, data/timeline.json, research/FOLLOWUPS.md)
and writes:

  site/                 multi-page Hindi site (index.html, gaon/<slug>.html, ...)
  site/preview.html     the same content as one self-contained file (images inlined)

Nothing here is hand-written per village: every page is rendered from the data,
so re-running the research pipeline and then `python -m gaon34 site` refreshes the site.
Only stills whose manifest rights allow it are shown with people in them.
"""
from __future__ import annotations

import base64
import csv
import html
import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import date
from pathlib import Path

from . import ROOT, STORE_DIR
from .registry import load_villages

DATA_DIR = ROOT / "data"
MEDIA_DIR = ROOT / "research" / "media"
FOLLOWUPS = ROOT / "research" / "FOLLOWUPS.md"
SITE_DIR = ROOT / "site"

TAGLINE = "गांव उजड़े, जड़ें नहीं।"
SITE_NAME = "34 गांव"
DOMAIN = "34gaon.com"

STATUS_HI = {
    "verified": ("पक्का", "ok"),
    "corroborated": ("मिलान", "ok"),
    "single-source": ("एक स्रोत", "one"),
    "unverified": ("जांच बाकी", "todo"),
    "conflicting": ("विरोधी स्रोत", "conf"),
}
UNIT_STATUS_HI = {
    "acquired": "अधिग्रहित",
    "acquired_partial": "आंशिक अधिग्रहण",
    "umbrella": "साझा इकाई",
}
SOURCE_TYPE_HI = {
    "video": "वीडियो", "news": "समाचार", "government": "सरकारी", "court": "अदालत",
    "social": "सोशल मीडिया", "community": "समुदाय", "encyclopedia": "विश्वकोश",
    "academic": "शोध", "book": "पुस्तक", "archive": "अभिलेख", "blog": "ब्लॉग",
    "directory": "निर्देशिका", "map": "नक्शा", "other": "अन्य",
}
TL_STATUS = {"pakka": ("पक्का", "ok"), "samachar": ("समाचार", "one"), "samuday": ("समुदाय", "one"), "sandigdh": ("विवादित", "conf")}
TL_PHASE = {"kanoon": "कानूनी अधिग्रहण", "visthapan": "विस्थापन", "punarvas": "पुनर्वास और मुकदमे", "aaj": "आज"}

NAV = [
    ("index", "घर"), ("gaon", "गांव"), ("naksha", "नक्शा"), ("samay", "समय-रेखा"),
    ("yaadein", "यादें"), ("asar", "रेंज का असर"), ("basera", "नया बसेरा"),
    ("chaupal", "चौपाल"), ("yogdan", "योगदान"), ("srot", "स्रोत"),
]

MAX_STILLS_PER_VIDEO = 6
STILL_WIDTH = 720
PREVIEW_WIDTH = 520


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


# ----------------------------------------------------------------------------- data


def load_records() -> dict:
    out = {}
    for v in load_villages():
        p = STORE_DIR / v["slug"] / "record.json"
        if p.exists():
            out[v["slug"]] = json.loads(p.read_text(encoding="utf-8"))
    return out


def load_csv(name: str) -> list[dict]:
    p = DATA_DIR / name
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_timeline() -> list[dict]:
    p = DATA_DIR / "timeline.json"
    if not p.exists():
        return []
    ev = json.loads(p.read_text(encoding="utf-8"))["events"]
    return sorted(ev, key=lambda e: e["sort"])


def load_quotes() -> list[dict]:
    p = DATA_DIR / "quotes.json"
    return json.loads(p.read_text(encoding="utf-8"))["quotes"] if p.exists() else []


def load_polygon() -> list[tuple[float, float]]:
    p = DATA_DIR / "mffr_range_polygon.geojson"
    if not p.exists():
        return []
    gj = json.loads(p.read_text(encoding="utf-8"))
    coords = gj["features"][0]["geometry"]["coordinates"][0]
    return [(float(c[0]), float(c[1])) for c in coords]


def load_followups() -> dict[str, list[dict]]:
    """Parse the markdown tables in FOLLOWUPS.md into rows keyed by unit slug.
    Section D (personal contacts) is deliberately not exported to the site."""
    rows: dict[str, list[dict]] = {}
    if not FOLLOWUPS.exists():
        return rows
    section = ""
    for line in FOLLOWUPS.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:4]
            continue
        if not line.startswith("|") or section in ("", "D", "E"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0].startswith("---") or cells[0] in ("तारीख", "इकाई"):
            continue
        unit = cells[1]
        if section == "C":
            text, how, state = cells[2], cells[3], cells[4] if len(cells) > 4 else ""
        else:
            text = f"{cells[2]}: {cells[3]}" if len(cells) > 3 else cells[2]
            how, state = (cells[4] if len(cells) > 4 else ""), (cells[5] if len(cells) > 5 else "")
        for slug in re.split(r"[,/]| और ", unit):
            slug = slug.strip()
            if slug:
                rows.setdefault(slug, []).append({"section": section, "text": text, "how": how, "state": state})
    return rows


def pick_stills(manifest_path: Path) -> dict:
    """Choose a small, varied set of stills from a manifest, honouring its rights note."""
    d = json.loads(manifest_path.read_text(encoding="utf-8"))
    rights = d.get("rights", "")
    needs_permission = bool(re.search(r"obtain|permission|consent", rights, re.I)) and "with permission" not in rights.lower()
    seen, chosen = set(), []
    for f in d.get("frames", []):
        desc = f.get("description", "")
        tags = set(f.get("tags", []))
        if needs_permission and "people" in tags:
            continue
        key = desc[:60]
        if key in seen:
            continue
        seen.add(key)
        chosen.append(f)
    # prefer frames that show people, ruins, temples, shrines; keep original order
    prio = {"people": 0, "oral-history": 0, "ruins": 1, "temple": 1, "shrine": 1, "fort": 1, "legend": 1, "water": 2, "landscape": 3, "title": 4}
    chosen.sort(key=lambda f: min([prio.get(t, 5) for t in f.get("tags", [])] or [5]))
    chosen = sorted(chosen[:MAX_STILLS_PER_VIDEO], key=lambda f: f.get("timestamp_s", 0))
    src = d.get("source", {})
    url = d.get("source_url") or src.get("url", "")
    m_yt = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
    vid_id = d.get("video_id") or (m_yt.group(1) if m_yt else None) or manifest_path.parent.name
    return {
        "dir": manifest_path.parent,
        "slug": manifest_path.parent.parent.name if manifest_path.parent.name != manifest_path.parent.parent.name else manifest_path.parent.name,
        "video_id": vid_id,
        "url": url,
        "credit": d.get("credit") or src.get("creator", ""),
        "title": src.get("title", ""),
        "rights": rights,
        "needs_permission": needs_permission,
        "frames": chosen,
        "total": len(d.get("frames", [])),
        "kind": d.get("media_kind", "video"),
        "pending_village": "confirm" in rights.lower() and "village" in rights.lower(),
    }


def load_media() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    if not MEDIA_DIR.exists():
        return out
    for m in sorted(MEDIA_DIR.glob("*/manifest.json")) + sorted(MEDIA_DIR.glob("*/*/manifest.json")):
        slug = m.parent.name if m.parent.parent == MEDIA_DIR else m.parent.parent.name
        info = pick_stills(m)
        info["slug"] = slug
        out.setdefault(slug, []).append(info)
    return out


# ----------------------------------------------------------------------------- images


def resize(src: Path, dst: Path, width: int) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return True
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", f"scale='min({width},iw)':-2", "-q:v", "8" if width <= 520 else "7", str(dst)],
            check=True, capture_output=True,
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        shutil.copyfile(src, dst)
        return dst.exists()


class Images:
    """Copies/resizes stills into site/media and (for the preview) inlines them."""

    def __init__(self, out_dir: Path, inline: bool):
        self.out_dir = out_dir
        self.inline = inline
        self.cache: dict[str, str] = {}
        self.bytes = 0

    def src(self, still: Path, slug: str, video_id: str, width: int = STILL_WIDTH, depth: int = 0) -> str:
        rel = f"media/{slug}/{video_id}/{still.name}"
        key = f"{rel}@{width}"
        if key in self.cache:
            return ("../" * depth + self.cache[key]) if not self.inline else self.cache[key]
        if self.inline:
            width = min(width, PREVIEW_WIDTH) if width < 1000 else 960  # keep the single-file preview small
            tmp = self.out_dir / "_preview_cache" / f"{slug}_{video_id}_{width}_{still.name}"
            resize(still, tmp, width)
            data = tmp.read_bytes()
            self.bytes += len(data)
            val = "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
        else:
            resize(still, self.out_dir / rel, width)
            val = rel
        self.cache[key] = val
        return ("../" * depth + val) if not self.inline else val


# ----------------------------------------------------------------------------- html bits


def badge(status: str) -> str:
    label, cls = STATUS_HI.get(status, (status, "todo"))
    return f'<span class="badge b-{cls}">{esc(label)}</span>'


def unit_name(v: dict) -> tuple[str, str]:
    return v["names"]["hi"], v["names"]["en"]


CSS = r"""
/* Single-theme, deliberately: the desert at night. Every colour is set explicitly. */
:root{
  --bg:#0E1017; --bg2:#151824; --panel:#1B1F2C; --line:#2A2F3E; --ink:#F1ECE2; --ink2:#D8D1C4; --muted:#9A937F;
  --sand:#E2B45A; --sand2:#B98A3A; --green:#8DBB74; --rust:#E0774A; --indigo:#7F8FFF;
  --ok:#8DBB74; --one:#E2B45A; --todo:#8B8577; --conf:#E0774A;
  --radius:8px; color-scheme:dark;
}
*{box-sizing:border-box}
html{background:var(--bg)}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Mukta","Noto Sans Devanagari",system-ui,sans-serif;font-size:17px;line-height:1.65;font-variant-numeric:tabular-nums;-webkit-font-smoothing:antialiased}
a{color:var(--sand);text-decoration-thickness:1px;text-underline-offset:3px}
a:focus-visible,button:focus-visible{outline:2px solid var(--sand);outline-offset:3px}
img{max-width:100%;height:auto;display:block}
h1,h2,h3{font-family:"Rozha One","Noto Serif Devanagari",serif;font-weight:400;line-height:1.15;text-wrap:balance;margin:0;letter-spacing:-.005em}
h1{font-size:clamp(2.4rem,6vw,4.6rem)}
h2{font-size:clamp(1.8rem,3.6vw,2.7rem)}
h3{font-size:1.3rem}
p{margin:0}
.serif{font-family:"Tiro Devanagari Hindi","Noto Serif Devanagari",serif}
.wrap{max-width:1160px;margin:0 auto;padding-inline:clamp(16px,4vw,40px)}
.prose{max-width:66ch}
.eyebrow{font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;color:var(--sand);font-weight:500}
.muted{color:var(--muted)} .small{font-size:.9rem} .lede{font-size:clamp(1.1rem,1.6vw,1.35rem);line-height:1.55;color:var(--ink2)}
.stack{display:grid;gap:.7rem}
.section{padding-block:clamp(2.4rem,6vw,5rem)}
.section+.section{border-top:1px solid var(--line)}
.section-head{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:.5rem 1.5rem;margin-bottom:1.4rem}
/* top bar */
.top{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:rgba(14,16,23,.82);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.top .wrap{display:flex;align-items:center;gap:1rem;min-height:60px}
.brand{font-family:"Rozha One",serif;font-size:1.5rem;color:var(--ink);text-decoration:none;white-space:nowrap;line-height:1}
.brand small{font-family:"Mukta",sans-serif;font-size:.7rem;color:var(--muted);margin-left:.5rem;letter-spacing:.1em}
nav.main{display:flex;gap:.1rem;min-width:0;overflow-x:auto;scrollbar-width:none;margin-left:auto}
nav.main::-webkit-scrollbar{display:none}
nav.main a{white-space:nowrap;padding:.4rem .7rem;border-radius:999px;text-decoration:none;color:var(--ink2);font-size:.95rem}
nav.main a:hover{color:var(--ink)}
nav.main a[aria-current="page"]{background:var(--sand);color:#1A1406;font-weight:500}
/* photo treatment */
.ph{filter:contrast(1.08) saturate(1.12)}
/* hero */
.hero{position:relative;min-height:min(86vh,860px);display:grid;align-items:end;overflow:hidden;background:var(--bg2)}
.hero .bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:60% 35%;filter:contrast(1.1) saturate(1.15) brightness(.92)}
.hero::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(14,16,23,.25) 0%,rgba(14,16,23,.05) 35%,rgba(14,16,23,.55) 62%,rgba(14,16,23,.96) 100%),linear-gradient(90deg,rgba(14,16,23,.55) 0%,rgba(14,16,23,0) 55%)}
.hero .text{position:relative;z-index:1;padding-block:clamp(2rem,6vw,4.5rem) clamp(1.6rem,4vw,3rem)}
.hero h1{font-size:clamp(3rem,9.5vw,7.4rem);line-height:1.05;color:#FFFFFF;text-shadow:0 4px 30px rgba(0,0,0,.55)}
.hero .lede{max-width:56ch;margin-top:1rem;color:#E9E3D6;text-shadow:0 2px 12px rgba(0,0,0,.6)}
.hero .credit{font-size:.78rem;color:#B9B2A2;margin-top:1.2rem;letter-spacing:.03em}
.hero .cue{position:absolute;right:clamp(16px,4vw,40px);bottom:1.6rem;z-index:1;color:#C9C2B1;font-size:.75rem;letter-spacing:.14em;text-transform:uppercase}
@media (prefers-reduced-motion:no-preference){
  .hero .bg{animation:kb 28s ease-out both}
  @keyframes kb{from{transform:scale(1.08) translate(1.5%,0)}to{transform:scale(1) translate(0,0)}}
  .hero h1,.hero .lede,.hero .credit{animation:rise 1.1s cubic-bezier(.2,.7,.2,1) both}
  .hero .lede{animation-delay:.25s}.hero .credit{animation-delay:.45s}
  @keyframes rise{from{opacity:.001;transform:translateY(14px)}to{opacity:1;transform:none}}
}
/* quotes strip */
.quotes{display:flex;gap:1rem;overflow-x:auto;scroll-snap-type:x mandatory;padding-block:.4rem 1rem;scrollbar-width:thin;scrollbar-color:var(--line) transparent}
.quotes blockquote{flex:0 0 min(78vw,520px);scroll-snap-align:start;margin:0;padding:1.6rem 1.6rem 1.4rem;background:var(--panel);border-radius:var(--radius);border-top:3px solid var(--sand);display:grid;align-content:space-between;gap:1rem}
.quotes p{font-family:"Tiro Devanagari Hindi","Noto Serif Devanagari",serif;font-size:clamp(1.25rem,2.1vw,1.6rem);line-height:1.45;color:var(--ink)}
.quotes cite{font-style:normal;font-size:.82rem;color:var(--muted)}
.quotes cite a{color:var(--sand2)}
/* film strip */
.strip{display:flex;gap:.8rem;overflow-x:auto;scroll-snap-type:x mandatory;padding-block:.4rem 1rem;scrollbar-width:thin;scrollbar-color:var(--line) transparent}
.strip figure{flex:0 0 min(84vw,440px);scroll-snap-align:start;margin:0}
.strip img{aspect-ratio:3/2;object-fit:cover;width:100%;border-radius:var(--radius);filter:contrast(1.08) saturate(1.12)}
.strip figcaption{padding:.5rem .1rem 0;font-size:.88rem;line-height:1.45;color:var(--ink2)}
.strip figcaption b{font-family:"Rozha One",serif;font-weight:400;font-size:1.05rem;color:var(--sand);margin-right:.4rem}
.strip figcaption .cr{display:block;color:var(--muted);font-size:.76rem;margin-top:.15rem}
/* wall of names */
.wall{display:flex;flex-wrap:wrap;gap:.25rem .9rem;align-items:baseline}
.wall a{font-family:"Rozha One",serif;font-size:clamp(1.7rem,3.6vw,3rem);line-height:1.25;text-decoration:none;color:var(--ink);position:relative;padding-inline:.1rem}
.wall a.thin{color:var(--muted);font-family:"Tiro Devanagari Hindi",serif;font-size:clamp(1.35rem,2.8vw,2.3rem)}
.wall a small{font-family:"Mukta",sans-serif;font-size:.7rem;color:var(--sand2);vertical-align:super;margin-left:.15rem;letter-spacing:.05em}
.wall a.media::after{content:"";display:inline-block;width:.45rem;height:.45rem;border-radius:50%;background:var(--green);margin-left:.35rem;vertical-align:middle}
.wall a:hover{color:var(--sand)}
.wall-note{display:flex;flex-wrap:wrap;gap:.6rem 1.4rem;margin-top:1.2rem;font-size:.88rem;color:var(--muted)}
/* big numbers */
.big{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1px;background:var(--line);border-block:1px solid var(--line)}
.big div{background:var(--bg);padding:1.6rem 1.2rem 1.4rem}
.big b{display:block;font-family:"Rozha One",serif;font-weight:400;font-size:clamp(2.4rem,4.6vw,4rem);line-height:1;color:var(--sand)}
.big span{display:block;margin-top:.6rem;color:var(--ink2);font-size:.95rem;max-width:26ch}
.big i{font-style:normal;display:block;color:var(--muted);font-size:.78rem;margin-top:.3rem}
/* badges */
.badge{display:inline-block;font-size:.72rem;line-height:1.3;padding:.15rem .55rem;border-radius:999px;border:1px solid currentColor;white-space:nowrap;vertical-align:middle;letter-spacing:.02em}
.b-ok{color:var(--ok)} .b-one{color:var(--one)} .b-todo{color:var(--todo);border-style:dashed} .b-conf{color:var(--conf)}
/* claims */
.claims{list-style:none;padding:0;margin:0;display:grid;gap:.6rem}
.claims li{display:grid;grid-template-columns:auto 1fr;gap:.7rem;align-items:start;padding:.8rem 1rem;border-left:3px solid var(--line);background:var(--panel);border-radius:0 var(--radius) var(--radius) 0;font-size:1.02rem}
.claims li.ok{border-left-color:var(--ok)} .claims li.one{border-left-color:var(--one)} .claims li.conf{border-left-color:var(--conf)}
.claims .why{font-size:.86rem;color:var(--muted);grid-column:1/-1}
/* gallery grid */
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:.8rem}
.gallery figure{margin:0;background:var(--panel);border-radius:var(--radius);overflow:hidden}
.gallery img{aspect-ratio:16/10;object-fit:cover;width:100%;filter:contrast(1.08) saturate(1.12)}
.gallery figcaption{padding:.5rem .7rem .7rem;font-size:.85rem;line-height:1.45;color:var(--ink2)}
.gallery figcaption .t{color:var(--sand2);font-size:.74rem;margin-right:.4rem}
.video{padding-block:1.4rem}
.video+.video{border-top:1px solid var(--line)}
.video header{display:flex;flex-wrap:wrap;gap:.3rem 1rem;align-items:baseline;margin-bottom:.8rem}
.video h3{font-family:"Tiro Devanagari Hindi",serif;font-size:1.25rem;color:var(--ink)}
/* village header */
.vhead{position:relative;min-height:min(62vh,600px);display:grid;align-items:end;overflow:hidden;background:var(--bg2)}
.vhead .bg{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:center 45%;filter:contrast(1.1) saturate(1.15) brightness(.9)}
.vhead.nophoto{min-height:280px;background:radial-gradient(120% 90% at 20% 100%,#2A2416 0%,var(--bg2) 55%,var(--bg) 100%)}
.vhead::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(14,16,23,.15) 0%,rgba(14,16,23,.35) 45%,rgba(14,16,23,.97) 100%)}
.vhead .text{position:relative;z-index:1;padding-block:2.5rem 1.6rem;display:grid;gap:.5rem}
.vhead h1{font-size:clamp(3rem,9vw,6.4rem);line-height:1.05;color:#FFF;text-shadow:0 4px 30px rgba(0,0,0,.55)}
.vhead .en{font-family:"Tiro Devanagari Hindi",serif;color:#D9D2C3;font-size:1.15rem}
.vhead .row{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin-top:.4rem}
.vhead .credit{font-size:.75rem;color:#B9B2A2}
/* tables */
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius)}
table{border-collapse:collapse;width:100%;font-size:.93rem}
th,td{text-align:left;padding:.6rem .8rem;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--panel);font-weight:500;white-space:nowrap;color:var(--ink2)}
tr:last-child td{border-bottom:0}
td.num{text-align:right;white-space:nowrap}
/* timeline */
.tl{list-style:none;margin:0;padding:0;border-left:2px solid var(--line);margin-left:.6rem}
.tl li{position:relative;padding:.2rem 0 1.8rem 1.6rem}
.tl li::before{content:"";position:absolute;left:-8px;top:.9rem;width:14px;height:14px;border-radius:50%;background:var(--bg);border:2px solid var(--sand)}
.tl li.visthapan::before{background:var(--sand)}
.tl .when{font-family:"Rozha One",serif;font-size:1.6rem;color:var(--sand)}
.tl .phase{font-size:.74rem;color:var(--muted);letter-spacing:.08em;margin-left:.6rem;text-transform:uppercase}
.tl b{display:block;font-family:"Tiro Devanagari Hindi",serif;font-weight:400;font-size:1.25rem;margin:.2rem 0 .25rem}
.phases{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:.7rem;margin-bottom:1.4rem}
.phases div{padding:1rem;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel)}
.phases b{display:block;font-family:"Rozha One",serif;font-weight:400;font-size:1.25rem;color:var(--sand)}
/* map */
.map{border:1px solid var(--line);border-radius:var(--radius);background:var(--bg2);padding:.5rem}
.map svg{width:100%;height:auto;display:block}
/* callouts, cards */
.callout{padding:1.2rem 1.4rem;border-left:3px solid var(--sand);background:var(--panel);border-radius:0 var(--radius) var(--radius) 0}
.callout.warn{border-left-color:var(--rust)}
.callout h3{font-family:"Tiro Devanagari Hindi",serif}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:1.2rem}
.list{padding-left:1.2rem;margin:0;display:grid;gap:.35rem}
.srcs{list-style:none;padding:0;margin:0;display:grid;gap:.5rem}
.srcs li{padding:.6rem .8rem;border:1px solid var(--line);border-radius:var(--radius);font-size:.93rem;background:var(--bg2)}
.srcs .meta{color:var(--muted);font-size:.8rem}
.tag{display:inline-block;font-size:.76rem;padding:.1rem .55rem;border-radius:999px;background:rgba(226,180,90,.12);border:1px solid rgba(226,180,90,.35);color:var(--sand);margin-right:.3rem}
.legend{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:center;font-size:.9rem;color:var(--ink2)}
.btn{display:inline-block;padding:.7rem 1.3rem;border-radius:999px;background:var(--sand);color:#1A1406;text-decoration:none;font-weight:500}
.btn:hover{background:#EDC36E}
.btn.ghost{background:transparent;color:var(--sand);border:1px solid var(--sand2)}
.kv{display:grid;grid-template-columns:auto 1fr;gap:.3rem 1.2rem;font-size:.97rem}
.kv dt{color:var(--sand2)} .kv dd{margin:0;color:var(--ink2)}
/* chaupal mock */
.chat{max-width:440px;border:1px solid var(--line);border-radius:14px;padding:.9rem;background:var(--bg2);display:grid;gap:.55rem}
.chat .m{max-width:85%;padding:.55rem .8rem;border-radius:12px;background:var(--panel);font-size:.95rem}
.chat .m.me{margin-left:auto;background:var(--sand);color:#1A1406}
.chat .m small{display:block;color:var(--muted);font-size:.72rem}
.chat .m.me small{color:#1A1406;opacity:.7}
/* call band */
.band{position:relative;overflow:hidden;border-radius:var(--radius);background:var(--bg2);min-height:340px;display:grid;align-items:end}
.band img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;filter:contrast(1.1) saturate(1.1) brightness(.75)}
.band::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(14,16,23,.1),rgba(14,16,23,.92))}
.band .text{position:relative;z-index:1;padding:2rem clamp(1rem,4vw,2.5rem)}
.band h2{color:#FFF}
footer{border-top:1px solid var(--line);margin-top:2rem;padding-block:2rem 2.6rem;font-size:.9rem;color:var(--muted)}
footer .wrap{display:grid;gap:.5rem}
footer .tag-line{font-family:"Rozha One",serif;font-size:1.6rem;color:var(--ink)}
@media (prefers-reduced-motion:no-preference){ .gallery figure,.strip img{transition:transform .25s} .gallery figure:hover,.strip figure:hover img{transform:translateY(-3px)} }
@media (max-width:480px){ body{font-size:16px} .hero{min-height:78vh} .big b{font-size:2.2rem} }
"""

FONT_LINK = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rozha+One&family=Tiro+Devanagari+Hindi:ital@0;1&family=Mukta:wght@400;500;700&display=swap">'


# ----------------------------------------------------------------------------- generator


class Site:
    def __init__(self, out_dir: Path = SITE_DIR):
        self.out = out_dir
        self.villages = load_villages()
        self.by_slug = {v["slug"]: v for v in self.villages}
        self.records = load_records()
        self.media = load_media()
        self.timeline = load_timeline()
        self.incidents = load_csv("incidents.csv")
        self.resettle = load_csv("resettlement_sites.csv")
        self.polygon = load_polygon()
        self.quotes = load_quotes()
        self.followups = load_followups()
        self.built = date.today().isoformat()
        self.mode = "multi"  # or "single"
        self.images: Images | None = None
        self.stats = self._stats()

    # ---- routing -------------------------------------------------------------
    def href(self, route: str, depth: int = 0) -> str:
        """route: 'index' | 'gaon' | 'gaon/<slug>' | 'naksha' ..."""
        if self.mode == "single":
            return f"#/{route}"
        prefix = "../" * depth
        if route == "index":
            return f"{prefix}index.html"
        if route.startswith("gaon/"):
            return f"{prefix}gaon/{route[5:]}.html"
        return f"{prefix}{route}.html"

    def _stats(self) -> dict:
        st = Counter()
        st["units"] = len([v for v in self.villages if v.get("unit_type") != "umbrella"])
        for slug, r in self.records.items():
            c = r["counts"]
            st["sources"] += c["sources_total"]; st["accepted"] += c["accepted"]; st["claims"] += c["claims"]
            for cl in r["claims"]["well_supported"] + r["claims"]["needs_verification"]:
                st[cl["status"]] += 1
            if c["accepted"] > 0 and slug != "34-gaon":
                st["units_with_sources"] += 1
        st["videos"] = sum(len(m) for m in self.media.values())
        st["stills"] = sum(x["total"] for m in self.media.values() for x in m)
        return st

    # ---- layout ---------------------------------------------------------------
    def layout(self, route: str, title: str, body: str, depth: int = 0, desc: str = "") -> str:
        page_title = f"{title} · {SITE_NAME}" if route != "index" else f"{SITE_NAME}: {TAGLINE}"
        return f"""<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(page_title)}</title>
<meta name="description" content="{esc(desc or TAGLINE)}">
{FONT_LINK}
<style>{CSS}</style>
</head>
<body>
{self.topbar(route, depth)}
<main>{body}</main>
{self.footer(depth)}
</body>
</html>"""

    def topbar(self, route: str, depth: int = 0) -> str:
        cur = route.split("/")[0]
        nav = ""
        for r, label in NAV:
            current = ' aria-current="page"' if r == cur else ""
            nav += f'<a href="{self.href(r, depth)}"{current}>{esc(label)}</a>'
        return f'<header class="top"><div class="wrap"><a class="brand" href="{self.href("index", depth)}">{SITE_NAME}<small>{DOMAIN}</small></a><nav class="main" aria-label="मुख्य">{nav}</nav></div></header>'

    def footer(self, depth: int = 0) -> str:
        return f"""<footer><div class="wrap">
<div class="tag-line">{esc(TAGLINE)}</div>
<div>महाजन फील्ड फायरिंग रेंज (बीकानेर) के लिए 1982–86 में उजड़े गांवों की सामुदायिक स्मृति। TechnoTaau Team, संयोजक जाखड़ सिंह।</div>
<div>हर तथ्य के साथ उसकी जांच का स्तर: {badge("verified")} {badge("corroborated")} {badge("single-source")} {badge("unverified")} {badge("conflicting")} · <a href="{self.href("srot", depth)}">तरीका और स्रोत</a></div>
<div class="small">Phase 1 preview · डेटा {esc(self.built)} तक · तस्वीरें उनके रचनाकारों की हैं, हर तस्वीर के साथ श्रेय है।</div>
</div></footer>"""

    def best_still(self, slug: str, prefer_people: bool = False) -> dict | None:
        """The most evocative permitted still for a unit: people (if allowed) > temple/shrine/ruins > landscape."""
        prio = {"people": 0 if prefer_people else 2, "oral-history": 0 if prefer_people else 2, "temple": 1, "shrine": 1, "fort": 1, "ruins": 1, "water": 2, "landscape": 3, "title": 5, "journey": 4}
        best, best_p = None, 99
        for vid in self.media.get(slug, []):
            for f in vid["frames"]:
                pr = min([prio.get(t, 4) for t in f.get("tags", [])] or [4])
                if pr < best_p:
                    best, best_p = {"vid": vid, "frame": f}, pr
        return best

    def all_stills(self) -> list[tuple[str, dict, dict]]:
        out = []
        for slug, vids in self.media.items():
            for vid in vids:
                for f in vid["frames"]:
                    if slug == "34-gaon" and "title" in f.get("tags", []):
                        continue
                    out.append((slug, vid, f))
        return out

    def page_index(self, depth=0) -> str:
        h = lambda r: self.href(r, depth)
        hero = self.hero_image(depth)
        st = self.stats
        q_html = ""
        for q in self.quotes:
            link = f' · <a href="{h("gaon/" + q["unit"])}">{esc(unit_name(self.by_slug[q["unit"]])[0])}</a>' if q.get("unit") in self.by_slug else ""
            q_html += f'<blockquote><p>{esc(q["text"])}</p><cite>{esc(q["who"])}{link}</cite></blockquote>'
        prio = {"people": 0, "oral-history": 0, "temple": 1, "shrine": 1, "fort": 1, "ruins": 1, "water": 2, "landscape": 3}
        ranked = sorted(self.all_stills(), key=lambda x: min([prio.get(t, 4) for t in x[2].get("tags", [])] or [4]))
        picked, seen = [], set()
        for slug, vid, f in ranked:
            if vid["video_id"] in seen:
                continue
            seen.add(vid["video_id"]); picked.append((slug, vid, f))
        strip_html = ""
        for slug, vid, f in picked[:12]:
            src = self.images.src(vid["dir"] / f["file"], slug, vid["video_id"], depth=depth)
            cap = f.get("description_hi") or f["description"]
            strip_html += f'<figure><a href="{h("gaon/" + slug)}"><img loading="lazy" src="{src}" alt="{esc(cap)}"></a><figcaption><b>{esc(unit_name(self.by_slug[slug])[0])}</b>{esc(cap)}<span class="cr">{esc(vid["credit"])}</span></figcaption></figure>'
        band = self.best_still("berawala") or self.best_still("kanolai")
        band_img = f'<img loading="lazy" src="{self.images.src(band["vid"]["dir"] / band["frame"]["file"], band["vid"]["slug"], band["vid"]["video_id"], 1280, depth)}" alt="">' if band else ""
        return f"""
<section class="hero">
  <img class="bg" src="{hero['src']}" alt="{esc(hero['alt'])}" fetchpriority="high">
  <div class="text"><div class="wrap">
    <p class="eyebrow">महाजन फील्ड फायरिंग रेंज · लूणकरणसर, बीकानेर · 1982–86</p>
    <h1>{esc(TAGLINE)}</h1>
    <p class="lede serif">चौंतीस गांव खाली कराए गए। घर, कुएं, मंदिर और तालाब आज भी रेंज के अंदर खड़े हैं, और जो लोग वहां से निकले, वे आज भी होली पर लौटते हैं। यह जगह उन गांवों की याद, उनके परिवारों और उनकी आवाज़ के लिए है।</p>
    <p class="credit">तस्वीर: {esc(hero['credit'])}</p>
  </div></div>
  <div class="cue">↓ नीचे</div>
</section>

<div class="wrap">
<section class="section">
  <p class="eyebrow">एक-एक पंक्ति में</p>
  <div class="quotes" style="margin-top:.8rem">{q_html}</div>
</section>

<section class="section">
  <div class="section-head"><h2>जो लौटकर गए, उन्होंने यह देखा</h2><a class="small" href="{h('yaadein')}">सारे वीडियो और तस्वीरें →</a></div>
  <div class="strip">{strip_html}</div>
</section>

<section class="section">
  <div class="section-head"><h2>नामों की दीवार</h2><span class="small muted">{st['units_with_sources']} गांवों की कहानी मिलनी शुरू हुई · {st['units'] - st['units_with_sources']} का अभी सिर्फ़ नाम बचा है</span></div>
  {self.village_grid(depth)}
  <div class="wall-note"><span>उजले नाम: स्रोत मिले</span><span>धुंधले नाम: सिर्फ़ नाम, कहानी आपसे चाहिए</span><span><span style="display:inline-block;width:.45rem;height:.45rem;border-radius:50%;background:var(--green);vertical-align:middle"></span> वीडियो/तस्वीरें हैं</span><a href="{h('gaon')}">सूची का आधार और 33/34 का सवाल →</a></div>
</section>

<section class="section">
  <p class="eyebrow" style="margin-bottom:1rem">जो अब तक पक्का पता है</p>
  <div class="big">
    <div><b>33 / 34</b><span>गांव। सरकारी कागज़ 33 कहते हैं, लोग और अखबार 34।</span><i>लोकसभा 1987 · पत्रिका 2022</i></div>
    <div><b>1,364 km²</b><span>रेंज का क्षेत्रफल, दिल्ली से थोड़ा छोटा।</span><i>जनगणना 2011 · OSM</i></div>
    <div><b>₹300</b><span>प्रति बीघा, बदले की बारानी ज़मीन की दर।</span><i>अधिसूचना 23 नवंबर 1985</i></div>
    <div><b>₹64.11 करोड़</b><span>कुल मुआवजा, 3,12,649 बीघा निजी ज़मीन के लिए।</span><i>लोकसभा, 21 अगस्त 1987</i></div>
    <div><b>148</b><span>बदले की ज़मीन के प्रकरण 2025 में भी लंबित।</span><i>पत्रिका, 14 फरवरी 2025</i></div>
    <div><b>40 साल</b><span>गांव छोड़े हुए। होली पर आज भी कुम्भाणा में होलिका जलती है।</span><i>पत्रिका 2022 (एक स्रोत)</i></div>
  </div>
  <p class="small muted" style="margin-top:.8rem"><a href="{h('samay')}">पूरी समय-रेखा 1938 से आज तक →</a></p>
</section>

<section class="section">
  <div class="band">{band_img}<div class="text">
    <p class="eyebrow">आपके घर में जो है, वही इतिहास है</p>
    <h2>अपने गांव की बात यहां रखिए</h2>
    <p class="lede" style="max-width:52ch;margin-top:.6rem;color:#E9E3D6">बुज़ुर्गों की 15 मिनट की बात, ट्रंक में रखा पट्टा, एक पुरानी तस्वीर, या सिर्फ़ यह कि आपका परिवार किस गांव से किस गांव गया।</p>
    <p style="margin-top:1.2rem"><a class="btn" href="{h('yogdan')}">योगदान दें</a> &nbsp; <a class="btn ghost" href="{h('gaon')}">अपना गांव खोजें</a></p>
  </div></div>
</section>
</div>"""

    def hero_image(self, depth: int) -> dict:
        for slug, vid_id, fname, alt in (
            ("berawala", "fb655816430875515", "0078s.jpg", "बेरावाला: छगनलाल जाखड़ अपने उजड़े गांव के मैदान को देखते हुए, जुलाई 2025"),
            ("berawala", "fb2884290418425839", "0002s.jpg", "बेरावाला: छगनलाल जाखड़ अपने उजड़े घर की मिट्टी की दीवार पर खड़े हैं, जुलाई 2025"),
        ):
            for vid in self.media.get(slug, []):
                if vid["video_id"] == vid_id and (vid["dir"] / "frames" / fname).exists():
                    return {"src": self.images.src(vid["dir"] / "frames" / fname, slug, vid_id, 1600, depth), "alt": alt, "credit": vid["credit"]}
        for slug, vids in self.media.items():
            for vid in vids:
                if vid["frames"]:
                    f = vid["frames"][0]
                    return {"src": self.images.src(vid["dir"] / f["file"], slug, vid["video_id"], 1600, depth), "alt": f["description"], "credit": vid["credit"]}
        return {"src": "", "alt": "", "credit": ""}

    def village_grid(self, depth: int, show_all: bool = True) -> str:
        cells = []
        for v in self.villages:
            if v.get("unit_type") == "umbrella":
                continue
            hi, en = unit_name(v)
            r = self.records.get(v["slug"])
            acc = r["counts"]["accepted"] if r else 0
            cls = []
            if not acc:
                cls.append("thin")
            if self.media.get(v["slug"]):
                cls.append("media")
            cls_attr = f' class="{" ".join(cls)}"' if cls else ""
            sup = f"<small>{acc}</small>" if acc else ""
            cells.append(f'<a href="{self.href("gaon/" + v["slug"], depth)}"{cls_attr} title="{esc(en)}: {acc} स्रोत">{esc(hi)}{sup}</a>')
        wall = "".join(cells)
        return f'<div class="wall">{wall}</div>'

    def page_gaon(self, depth=0) -> str:
        return f"""<div class="wrap">
<section class="section">
  <p class="eyebrow">गांव</p>
  <h1>34 गांव, एक-एक करके</h1>
  <p class="lede serif prose" style="margin-top:.8rem">हर गांव का अपना पन्ना है। जहां स्रोत मिले, वहां कहानी शुरू हो चुकी है; जहां सिर्फ़ नाम है, वहां आपकी याद चाहिए।</p>
  <p class="prose small muted" style="margin-top:.6rem">नाम समुदाय की सूची से हैं, इसलिए वर्तनी और पहचान अभी पक्की नहीं। सूची में 32 नाम थे, 2 खाली; अजीतवाणा, भानाबस्ती और नाथौर सूची में नहीं थे पर दूसरे स्रोतों में मिले।</p>
</section>
<section class="section">
  {self.village_grid(depth)}
</section>
<section class="section">
  <h2>33 या 34?</h2>
  <div class="cols" style="margin-top:1rem">
    <div class="callout"><b>सरकारी कागज़: 33 गांव</b><p class="small">लोकसभा उत्तर, 21 अगस्त 1987; राजस्थान उच्च न्यायालय, 8 फरवरी 2024 (अधिग्रहण 1983-84)।</p></div>
    <div class="callout"><b>लोग और अखबार: 34 गांव</b><p class="small">पत्रिका (2018, 2022), परिवारों के वीडियो, समुदाय की सूची (अधिग्रहण 1984-85)।</p></div>
  </div>
  <p class="small muted" style="margin-top:.8rem">हम दोनों को साथ रखते हैं। संभव है कि कानूनी अधिग्रहण 33 राजस्व गांवों का हुआ और एक ढाणी या आंशिक गांव (जैसे बिरमाणा या अजीतवाणा) लोगों की गिनती में 34वां है। 1981 की जिला जनगणना पुस्तिका मिलते ही यह सवाल सुलझेगा।</p>
</section>
</div>"""

    def page_village(self, slug: str, depth=1) -> str:
        v = self.by_slug[slug]
        r = self.records.get(slug)
        hi, en = unit_name(v)
        h = lambda route: self.href(route, depth)
        status = UNIT_STATUS_HI.get(v.get("status"), v.get("status", ""))
        variants = [x for x in v["names"].get("variants", []) if x not in (hi, en)][:8]
        notes = v.get("notes", "")
        best = self.best_still(slug, prefer_people=True)
        if best:
            src = self.images.src(best["vid"]["dir"] / best["frame"]["file"], slug, best["vid"]["video_id"], 1600, depth)
            bg = f'<img class="bg" src="{src}" alt="{esc(best["frame"].get("description_hi") or best["frame"]["description"])}" fetchpriority="high">'
            credit = f'<p class="credit">तस्वीर: {esc(best["vid"]["credit"])}</p>'
            cls = "vhead"
        else:
            bg, credit, cls = "", "", "vhead nophoto"
        var_txt = (" · " + esc(", ".join(variants[:5]))) if variants else ""
        parts = [f"""<section class="{cls}">{bg}<div class="text"><div class="wrap">
<p class="eyebrow"><a href="{h('gaon')}" style="color:inherit">गांव</a> · {esc(status)}</p>
<h1>{esc(hi)}</h1>
<div class="en">{esc(en)}{var_txt}</div>
{credit}
</div></div></section><div class="wrap">"""]
        if not r:
            c51 = v.get("census_1951") or {}
            co = v.get("coordinates") or {}
            extra = ""
            if c51.get("persons"):
                extra += f'<p class="small">1951 की जनगणना: <b>{esc(c51["persons"])}</b> लोग, {esc(c51.get("households"))} परिवार, {esc(c51.get("area_acres"))} एकड़ (कोड {esc(c51.get("code"))}).</p>'
            if co.get("lat"):
                extra += f'<p class="small">जगह: {co["lat"]}, {co["lon"]} ({"रेंज-सीमा के अंदर" if co.get("inside_range_polygon") else "रेंज-सीमा के बाहर"}).</p>'
            parts.append(f'<section class="section">{"<div class=callout>" + extra + "</div>" if extra else ""}<p style="margin-top:1rem">इस गांव के लिए अभी कोई वीडियो या लेख दर्ज नहीं है। {esc(notes)}</p><p style="margin-top:.8rem"><a class="btn" href="{h("yogdan")}">इस गांव के बारे में बताइए</a></p></section></div>')
            return "".join(parts)

        c = r["counts"]
        ws, nv = r["claims"]["well_supported"], r["claims"]["needs_verification"]
        # summary row
        parts.append(f"""<div class="row" style="display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin:1.4rem 0 1rem">
<span class="tag">{c['accepted']} स्वीकृत स्रोत</span><span class="tag">{c['claims']} दावे</span><span class="tag">{len(ws)} पक्के/मिलान</span>{f'<span class="tag">{sum(len(m["frames"]) for m in self.media.get(slug, []))} तस्वीरें</span>' if self.media.get(slug) else ''}
</div>""")
        c51 = v.get("census_1951")
        co = v.get("coordinates")
        facts = []
        if c51 and c51.get("list") == "populated":
            facts.append(f'1951 की जनगणना: <b>{esc(c51.get("persons"))}</b> लोग, {esc(c51.get("households"))} परिवार, {esc(c51.get("houses"))} घर, {esc(c51.get("area_acres"))} एकड़ (कोड {esc(c51.get("code"))}, "{esc(c51.get("name"))}"{", मिलान संभावित" if c51.get("match") == "probable" else ""})')
        elif c51:
            facts.append(f'1951 की जनगणना में गैर-आबाद राजस्व गांव "{esc(c51.get("name"))}" (कोड {esc(c51.get("code"))}){", मिलान संभावित" if c51.get("match") == "probable" else ""}')
        if co and co.get("lat"):
            facts.append(f'जगह: {co["lat"]}, {co["lon"]} ({"रेंज-सीमा के अंदर" if co.get("inside_range_polygon") else "रेंज-सीमा के बाहर"}; {esc(co.get("source", "")[:80])})')
        if facts:
            parts.append('<div class="callout" style="margin-bottom:1rem">' + "".join(f'<p class="small">{x}</p>' for x in facts) + '</div>')
        if notes:
            parts.append(f'<p class="prose small muted">{esc(notes)}</p>')

        # media
        vids = self.media.get(slug, [])
        if vids:
            parts.append('<section class="section"><div class="section-head"><h2>तस्वीरें और वीडियो</h2></div>')
            for vid in vids:
                parts.append(self.video_block(slug, vid, depth))
            parts.append("</section>")

        # claims
        if ws or nv:
            parts.append('<section class="section"><div class="section-head"><h2>क्या पता है</h2><span class="small muted">हर पंक्ति के साथ उसकी जांच का स्तर</span></div>')
            if ws:
                parts.append("<h3 class='muted' style='margin-bottom:.5rem'>पक्का या दो स्रोतों से मिलान</h3>" + self.claims_list(ws))
            if nv:
                parts.append("<h3 class='muted' style='margin:1rem 0 .5rem'>अभी एक ही स्रोत, या जांच बाकी</h3>" + self.claims_list(nv))
            parts.append("</section>")

        # entities
        ent = r.get("entities", {})
        if any(ent.get(k) for k in ("people", "places", "events")):
            parts.append('<section class="section"><h2>कौन, कहां, कब</h2><dl class="kv" style="margin-top:.8rem">')
            for k, label in (("people", "लोग"), ("places", "जगहें"), ("events", "घटनाएं"), ("organizations", "संस्थाएं")):
                if ent.get(k):
                    parts.append(f"<dt>{label}</dt><dd>{esc('; '.join(ent[k][:14]))}</dd>")
            parts.append("</dl><p class='small muted' style='margin-top:.6rem'>नाम स्रोतों से जैसे के तैसे लिए गए हैं; सार्वजनिक पोस्ट और वीडियो में जो नाम खुद लोगों ने लिखे, वही यहां हैं।</p></section>")

        # sources
        srcs = r.get("sources", {})
        acc = [(sid, s) for sid, s in srcs.items() if s.get("resolution", {}).get("decision") == "accept"]
        if acc:
            acc.sort(key=lambda x: -x[1].get("relevance", {}).get("score", 0))
            parts.append('<section class="section"><div class="section-head"><h2>स्रोत</h2><span class="small muted">जो इस गांव के बारे में सीधे बोलते हैं</span></div><ul class="srcs">')
            for sid, s in acc:
                st = SOURCE_TYPE_HI.get(s.get("source_type"), s.get("source_type", ""))
                url = s.get("url", "")
                link = f'<a href="{esc(url)}" rel="noopener">{esc(s.get("title") or url)}</a>' if url.startswith("http") else esc(s.get("title") or url)
                parts.append(f'<li>{link}<div class="meta">{esc(st)} · {esc(s.get("platform",""))} · {esc(s.get("published_date") or "तारीख नहीं")}</div></li>')
            parts.append("</ul></section>")
        shared = r.get("shared_umbrella_sources", [])
        if shared:
            parts.append(f'<p class="small muted">साझा स्रोत (पूरे 34 गांव के बारे में, इस गांव का नाम लेते हुए): {len(shared)} · <a href="{h("gaon/34-gaon")}">साझा इकाई</a></p>')

        # followups
        fu = self.followups.get(slug, [])
        if fu:
            parts.append('<section class="section"><h2>क्या छूटा है, किसमें मदद चाहिए</h2><ul class="list" style="margin-top:.6rem">')
            for row in fu:
                how = f' <span class="muted small">({esc(row["how"])})</span>' if row["how"] else ""
                parts.append(f'<li>{esc(row["text"])}{how}</li>')
            parts.append(f'</ul><p style="margin-top:.8rem"><a class="btn" href="{h("yogdan")}">इस गांव के बारे में कुछ भेजें</a></p></section>')
        else:
            parts.append(f'<section class="section"><p>क्या आपका परिवार {esc(hi)} से है? <a href="{h("yogdan")}">यहां बताइए</a>।</p></section>')
        parts.append("</div>")
        return "".join(parts)

    def claims_list(self, claims: list[dict]) -> str:
        items = []
        for cl in claims:
            label, cls = STATUS_HI.get(cl["status"], (cl["status"], "todo"))
            text = cl.get("statement_hi") or cl.get("statement_en") or cl.get("value", "")
            why = ""
            av = cl.get("agent_verdict") or {}
            if av.get("reasoning_hi") and cl["status"] in ("conflicting", "unverified", "verified"):
                why = f'<span class="why">{esc(av["reasoning_hi"][:260])}{"…" if len(av["reasoning_hi"]) > 260 else ""}</span>'
            comp = cl.get("competing") or []
            if comp and not why:
                why = f'<span class="why">दूसरे स्रोत कहते हैं: {esc("; ".join(str(x.get("value", x)) if isinstance(x, dict) else str(x) for x in comp[:3]))}</span>'
            items.append(f'<li class="{cls}">{badge(cl["status"])}<span>{esc(text)}</span>{why}</li>')
        return f'<ul class="claims">{"".join(items)}</ul>'

    def video_block(self, slug: str, vid: dict, depth: int) -> str:
        figs = []
        for f in vid["frames"]:
            src = self.images.src(vid["dir"] / f["file"], slug, vid["video_id"], depth=depth)
            cap = f.get("description_hi") or f["description"]
            figs.append(f'<figure><img loading="lazy" src="{src}" alt="{esc(cap)}"><figcaption><span class="t">{esc(f.get("timestamp",""))}</span>{esc(cap)}</figcaption></figure>')
        url = vid["url"]
        link = f'<a href="{esc(url)}" rel="noopener">{"मूल पोस्ट" if vid.get("kind") == "photos" else "मूल वीडियो"}</a>' if url.startswith("http") else ""
        note = '<span class="badge b-todo">लोगों वाली तस्वीरें अनुमति के बाद</span>' if vid["needs_permission"] else ""
        if vid.get("pending_village"):
            note += ' <span class="badge b-todo">गांव की पुष्टि बाकी</span>'
        title = vid["title"] or vid["credit"]
        credit = f'<span class="small muted">{esc(vid["credit"])}</span>' if vid["title"] else ""
        if figs:
            gallery = f'<div class="gallery">{"".join(figs)}</div>'
            count = f'<span class="small muted">{vid["total"]} में से {len(vid["frames"])} तस्वीरें</span>'
        else:
            gallery = '<p class="small muted">इस वीडियो की सभी तस्वीरों में पहचाने जा सकने वाले लोग हैं; रचनाकार और परिवार की अनुमति मिलने पर यहां दिखेंगी।</p>'
            count = f'<span class="small muted">{vid["total"]} तस्वीरें दर्ज</span>'
        return f"""<div class="video"><header><h3>{esc(title)}</h3>{credit} {link} {count} {note}</header>{gallery}</div>"""

    def page_naksha(self, depth=0) -> str:
        poly = self.polygon
        svg = ""
        if poly:
            lons = [p[0] for p in poly]; lats = [p[1] for p in poly]
            minx, maxx, miny, maxy = min(lons), max(lons), min(lats), max(lats)
            W, H = 900, 720
            pad = 40
            # equirectangular with cos(lat) correction
            import math
            kx = math.cos(math.radians((miny + maxy) / 2))
            sx = (W - 2 * pad) / ((maxx - minx) * kx); sy = (H - 2 * pad) / (maxy - miny)
            s = min(sx, sy)
            def X(lon): return pad + (lon - minx) * kx * s
            def Y(lat): return H - pad - (lat - miny) * s
            pts = " ".join(f"{X(lo):.1f},{Y(la):.1f}" for lo, la in poly)
            pins = []
            ctx = DATA_DIR / "ams_1955_villages.geojson"
            if ctx.exists():
                for f in json.loads(ctx.read_text(encoding="utf-8"))["features"]:
                    pr = f["properties"]
                    lo, la = f["geometry"]["coordinates"]
                    if pr.get("project_slug") or not (minx - .05 <= lo <= maxx + .05 and miny - .05 <= la <= maxy + .05):
                        continue
                    x, y = X(lo), Y(la)
                    if 0 <= x <= W and 0 <= y <= H:
                        pins.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="var(--muted)"/><text x="{x+8:.1f}" y="{y+4:.1f}" font-size="13" fill="var(--muted)" font-family="Mukta,sans-serif">{esc(pr["name_on_map"])}</text>')
            for v in self.villages:
                co = v.get("coordinates")
                if co and co.get("lat"):
                    x, y = X(co["lon"]), Y(co["lat"])
                    pins.append(f'<a href="{self.href("gaon/" + v["slug"], depth)}"><circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="var(--sand)" stroke="var(--bg)" stroke-width="2"/><text x="{x+11:.1f}" y="{y+6:.1f}" font-size="19" fill="var(--ink)" font-family="Mukta,sans-serif">{esc(v["names"]["hi"])}</text></a>')
            ticks = []
            for lon in (73.3, 73.4, 73.5, 73.6, 73.7, 73.8):
                if minx <= lon <= maxx:
                    ticks.append(f'<text x="{X(lon):.1f}" y="{H-10}" font-size="14" text-anchor="middle" fill="var(--muted)" font-family="Mukta,sans-serif">{lon}°E</text>')
            for lat in (28.6, 28.7, 28.8, 28.9, 29.0):
                if miny <= lat <= maxy:
                    ticks.append(f'<text x="6" y="{Y(lat)+5:.1f}" font-size="14" fill="var(--muted)" font-family="Mukta,sans-serif">{lat}°N</text>')
            # approximate compass labels for neighbouring towns (direction only, not plotted as points)
            svg = f"""<svg viewBox="0 0 {W} {H}" role="img" aria-label="महाजन फील्ड फायरिंग रेंज की सीमा (OpenStreetMap)">
<polygon points="{pts}" fill="#E2B45A" fill-opacity=".07" stroke="#E0774A" stroke-width="2.5" stroke-dasharray="8 5" stroke-linejoin="round"/>
{"".join(ticks)}{"".join(pins)}

</svg>"""
        rows = "".join(
            f"<tr><td>{esc(v['names']['hi'])}</td><td>{esc(v['names']['en'])}</td><td>{(str(v['coordinates']['lat']) + ', ' + str(v['coordinates']['lon'])) if v.get('coordinates') else '—'}</td><td class='num'>{esc((v.get('census_1951') or {}).get('persons', '—'))}</td><td class='num'>{esc((v.get('census_1951') or {}).get('code', '—'))}</td></tr>"
            for v in self.villages if v.get("unit_type") != "umbrella"
        )
        return f"""<div class="wrap">
<section class="section"><p class="eyebrow">नक्शा</p><h1>गांव कहां थे</h1>
<p class="lede serif prose" style="margin-top:.8rem">सुनहरे बिंदु वे गांव हैं जो 1955 के नक्शे पर आज की रेंज-सीमा के अंदर छपे हैं; धूसर बिंदु वे पड़ोसी गांव जो आज भी आबाद हैं। दोनों का यह बंटवारा ही बताता है कि कौन से गांव रेंज में गए।</p>
<p class="prose small muted" style="margin-top:.6rem">स्रोत: US Army Map Service 1:250,000, शीट NH 43-10, 43-13, 43-14 (1955, Survey of India 1913-48 से), हाथ से georeference, जगह ±1 किमी। सीमा: OpenStreetMap way 412765540 (ODbL)। गांवों की पहचान 1951 की जनगणना से; पूरी पद्धति "स्रोत" पन्ने पर।</p></section>
<section class="section"><div class="map">{svg}</div>
<p class="small muted" style="margin-top:.6rem">Phase 2 में यह नक्शा ज़ूम होने वाला (MapLibre) बनेगा: 1981 के गांव, 1987 के आवंटन चक 100–200 किमी पश्चिम में, और वे गांव जहां आज भी धमाके सुनाई देते हैं।</p></section>
<section class="section"><h2>1951 बनाम 2011: कौन से गांव ग़ायब हुए</h2>
<p class="prose" style="margin-top:.6rem">1951 की जनगणना में लूणकरणसर तहसील के 146 आबाद गांव थे। उनमें से 28 गांव, जिनमें 5,620 लोग और 1,070 परिवार रहते थे, 2011 की जनगणना में बीकानेर ज़िले में कहीं नहीं हैं, और उनका कुल क्षेत्रफल (लगभग 1,318 वर्ग किमी) आज की रेंज (1,364 वर्ग किमी) के लगभग बराबर है। <span class="badge b-ok">पक्का</span> सरकारी अभिलेख; गांव-वार मिलान <span class="badge b-one">हमारा विश्लेषण</span>।</p></section>
<section class="section"><h2>गांव के नाम, रेंज के नक्शे पर आज</h2>
<p class="prose" style="margin-top:.6rem">सेना के अभ्यासों की खबरों में पुराने गांवों के नाम रेंज की जगहों के रूप में मिलते हैं: चिड़ासर ग्रैंड स्टैंड, दुदेर ईस्ट कैंप, खानीसर और हाथूसर टैंक रेंज। यानी नाम ज़मीन पर बचे हैं, गांव नहीं। इसे अभी <span class="badge b-one">एक स्रोत</span> मानिए।</p></section>
<section class="section"><h2>किस गांव का स्थान पता है</h2><div class="tbl"><table><thead><tr><th>गांव</th><th>English</th><th>1955 की जगह (अक्षांश, देशांतर)</th><th>1951 आबादी</th><th>1951 कोड</th></tr></thead><tbody>{rows}</tbody></table></div></section>
</div>"""

    def page_samay(self, depth=0) -> str:
        items = []
        for e in self.timeline:
            label, cls = TL_STATUS.get(e["status"], (e["status"], "todo"))
            link = f' <a class="small" href="{esc(e["source"])}" rel="noopener">स्रोत</a>' if e.get("source") else ""
            items.append(f'<li class="{e["phase"]}"><div><span class="when">{esc(e["when"])}</span><span class="phase">{esc(TL_PHASE.get(e["phase"], ""))}</span> <span class="badge b-{cls}">{esc(label)}</span></div><b>{esc(e["title"])}</b><p class="small">{esc(e["text"])}{link}</p></li>')
        return f"""<div class="wrap">
<section class="section"><p class="eyebrow">समय-रेखा</p><h1>1938 से आज तक</h1>
<p class="prose" style="margin-top:.6rem">अधिग्रहण की तारीख पर सरकारी कागज़ (1982, 1983-84) और लोगों की याद (1984-85) अलग हैं। दोनों सही हैं: पहले कागज़ पर ज़मीन गई, फिर दो-तीन साल में घर छूटे। इसलिए समय-रेखा चार हिस्सों में है।</p>
<div class="phases" style="margin-top:1.2rem">
<div><b>कानूनी अधिग्रहण</b><span class="small muted">1981–1987: फाइल, अवार्ड, लोकसभा</span></div>
<div><b>विस्थापन</b><span class="small muted">1984–1986: परिवार निकले</span></div>
<div><b>पुनर्वास और मुकदमे</b><span class="small muted">1985–2024: आवंटन, वन विभाग, फर्ज़ीवाड़ा</span></div>
<div><b>आज</b><span class="small muted">2025–: 148 प्रकरण, रोज़ फायरिंग</span></div>
</div>
<div class="legend small"><span class="badge b-ok">पक्का</span> अदालत या सरकारी अभिलेख &nbsp; <span class="badge b-one">समाचार</span> अखबार &nbsp; <span class="badge b-one">समुदाय</span> लोगों की याद</div>
</section>
<section class="section"><ul class="tl">{"".join(items)}</ul></section>
<section class="section"><div class="callout warn"><b>एक आम गलती</b><p class="small">इंटरनेट पर घूमती तारीखें 'धारा 4 अधिसूचना 16.11.1982, अवार्ड 19.09.1983' किसी और फायरिंग रेंज (धन देवी बनाम भारत संघ, पंजाब-हरियाणा) की हैं, महाजन की नहीं। हम उन्हें इस्तेमाल नहीं करते।</p></div></section>
</div>"""

    def page_yaadein(self, depth=0) -> str:
        blocks = []
        for slug, vids in self.media.items():
            v = self.by_slug.get(slug)
            hi, en = unit_name(v) if v else (slug, slug)
            blocks.append(f'<h2 style="margin-top:1.6rem"><a href="{self.href("gaon/" + slug, depth)}">{esc(hi)}</a> <span class="small muted">{len(vids)} वीडियो</span></h2>')
            for vid in vids:
                r = self.records.get(slug, {})
                summary = ""
                for sid, s in (r.get("sources") or {}).items():
                    if vid["url"] and s.get("url", "").split("?")[0] and (vid["url"].rstrip("/").endswith(s.get("url", "").split("v=")[-1][:11]) or s.get("url") == vid["url"]):
                        summary = s.get("summary", "")
                        break
                blocks.append((f'<p class="prose small" style="margin:.4rem 0 .6rem">{esc(summary[:400])}{"…" if len(summary) > 400 else ""}</p>' if summary else "") + self.video_block(slug, vid, depth))
        return f"""<div class="wrap">
<section class="section"><p class="eyebrow">यादें</p><h1>जो लौटकर गए, उन्होंने क्या देखा</h1>
<p class="lede serif prose" style="margin-top:.8rem">परिवार अपने पुराने गांव जाते हैं, वीडियो बनाते हैं, फेसबुक और यूट्यूब पर डालते हैं। हमने {self.stats['videos']} वीडियो से {self.stats['stills']} तस्वीरें निकालकर हर एक का विवरण लिखा है। नीचे हर वीडियो से चुनी हुई तस्वीरें हैं; पूरी सूची शोध-भंडार में है।</p>
<div class="callout" style="margin-top:1rem"><b>अगला कदम: आवाज़ें</b><p class="small">बागड़ी में बुज़ुर्गों की बात मशीन नहीं पढ़ पाती। हमारी field team हर गांव के तीन-चार बुज़ुर्गों से तीन सवाल पूछकर रिकॉर्ड करेगी: गांव कैसा था, छोड़ने का दिन कैसा था, अब कौन कहां है। रिकॉर्डिंग 9:16 में, ताकि रील और वेबसाइट दोनों पर चले।</p></div>
</section>
<section class="section">{"".join(blocks)}</section>
</div>"""

    def page_asar(self, depth=0) -> str:
        rows = []
        for i in self.incidents:
            st = "पक्का" if i.get("status") == "confirmed" else "जांच बाकी"
            cls = "ok" if i.get("status") == "confirmed" else "todo"
            rows.append(f'<tr><td>{esc(i["date"])}</td><td>{esc(i["place"])}</td><td class="num">{esc(i["killed"])}</td><td class="num">{esc(i["injured"])}</td><td>{esc(i["victim_type"])}</td><td>{esc(i["details"])} <a class="small" href="{esc(i["source"])}" rel="noopener">स्रोत</a></td><td><span class="badge b-{cls}">{st}</span></td></tr>')
        killed = sum(int(i["killed"] or 0) for i in self.incidents if i.get("status") == "confirmed")
        return f"""<div class="wrap">
<section class="section"><p class="eyebrow">रेंज का असर</p><h1>ज़मीन गई, खतरा रह गया</h1>
<p class="prose" style="margin-top:.6rem">रेंज के आस-पास के गांवों में जिंदा गोले मिलते रहते हैं, कबाड़ में फटते हैं, और रोज़ की फायरिंग 25–30 किमी तक सुनाई देती है। नीचे वह है जो अखबारों में दर्ज है। असली गिनती इससे ज़्यादा है, और वही गिनती हम समुदाय की मदद से बनाना चाहते हैं।</p></section>
<section class="section"><div class="nums">
<div><b>{len(self.incidents)}</b><span>घटनाएं दर्ज, 2014–2026</span></div>
<div><b>{killed}</b><span>मौतें पुष्ट खबरों में (सैनिक और कबाड़ मज़दूर दोनों)</span></div>
<div><b>25–30 km</b><span>तक धमाके सुनाई देते हैं (पत्रिका, अप्रैल 2026)</span></div>
<div><b>148</b><span>बदले की ज़मीन के प्रकरण अभी लंबित</span></div>
</div></section>
<section class="section"><h2>घटना-पंजी</h2><div class="tbl" style="margin-top:.8rem"><table><thead><tr><th>तारीख</th><th>जगह</th><th>मृत</th><th>घायल</th><th>कौन</th><th>क्या हुआ</th><th>स्तर</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>
<section class="section"><div class="cols">
<div class="callout warn"><h3>अगर खेत में गोला मिले</h3><ul class="list small" style="margin-top:.5rem"><li>छुएं नहीं, हिलाएं नहीं, कबाड़ में न बेचें। पुराने गोले भी फट सकते हैं।</li><li>जगह याद रखें या फोन में फोटो लें, दूर से।</li><li>महाजन थाना या नज़दीकी थाना को बताएं; पुलिस सेना की टीम बुलाती है, जो गोला वहीं नष्ट करती है।</li><li>बच्चों और पशुओं को दूर रखें।</li></ul></div>
<div class="callout"><h3>ज़मीन का हक़</h3><p class="small" style="margin-top:.5rem">1985 का वादा: उतनी ही ज़मीन जितनी गई, 300 रुपये बीघा। 2025 में भी 148 प्रकरण लंबित, लगभग 350 किसान वन-भूमि के विवाद में। फरवरी 2025 में उच्च न्यायालय ने आठ हफ्ते में फैसले का आदेश दिया। पूरी कहानी <a href="{self.href('samay', depth)}">समय-रेखा</a> में।</p></div>
</div></section>
<section class="section"><p class="small muted">Phase 2 में यहां एक फॉर्म होगा: तारीख, जगह, फोटो, कौन घायल हुआ। यह वह आंकड़ा बनेगा जो आज किसी अखबार या दफ्तर के पास नहीं है।</p></section>
</div>"""

    def page_basera(self, depth=0) -> str:
        groups = {"confirmed": [], "press": [], "press+academic": [], "community": []}
        for s in self.resettle:
            groups.setdefault(s.get("status", "community"), []).append(s)
        def row(s):
            pop = f'{int(s["population_2011"]):,}' if s.get("population_2011") else ""
            src = f' <a class="small" href="{esc(s["source"])}" rel="noopener">स्रोत</a>' if s.get("source", "").startswith("http") else ""
            return f'<tr><td>{esc(s["site"])}</td><td>{esc(s["tehsil"])}, {esc(s["district"])}</td><td class="num">{pop}</td><td>{esc(s["evidence"])}{src}</td></tr>'
        tables = []
        for key, label, cls in (("confirmed", "अदालत या जनगणना से पक्का", "ok"), ("press", "अखबार से", "one"), ("press+academic", "अखबार और शोध से", "one"), ("community", "समुदाय के इतिहास से", "one")):
            if groups.get(key):
                tables.append(f'<h3 style="margin:1.2rem 0 .5rem"><span class="badge b-{cls}">{label}</span></h3><div class="tbl"><table><thead><tr><th>जगह</th><th>तहसील</th><th>आबादी 2011</th><th>सबूत</th></tr></thead><tbody>{"".join(row(s) for s in groups[key])}</tbody></table></div>')
        return f"""<div class="wrap">
<section class="section"><p class="eyebrow">नया बसेरा</p><h1>परिवार कहां गए</h1>
<p class="prose" style="margin-top:.6rem">बदले की ज़मीन इंदिरा गांधी नहर के इलाके में मिली, पुराने गांवों से 100–200 किमी पश्चिम: खाजूवाला, पूगल, छत्तरगढ़ के चक, रणजीतपुरा, बाजू। कुछ परिवार महाजन, शेरपुरा और लूणकरणसर में ही बसे। बारानी दुनिया से नहर की दुनिया में एक पीढ़ी में जाना पड़ा।</p></section>
<section class="section">{"".join(tables)}</section>
<section class="section"><div class="callout"><b>आपका परिवार किस गांव से किस गांव गया?</b><p class="small">यही एक पंक्ति हमारे नक्शे पर एक रेखा बनेगी। <a href="{self.href('yogdan', depth)}">यहां बताइए</a>।</p></div></section>
</div>"""

    def page_chaupal(self, depth=0) -> str:
        return f"""<div class="wrap">
<section class="section"><p class="eyebrow">चौपाल</p><h1>गांव-गांव की बातचीत</h1>
<p class="prose" style="margin-top:.6rem">चौपाल Phase 3 में खुलेगी: हर गांव का अपना धागा, फोन नंबर से लॉगिन, हिंदी कीबोर्ड, और विस्थापित विकास समिति से जुड़े संचालक। तब तक बातचीत WhatsApp समूह में चलेगी।</p></section>
<section class="section"><div class="cols">
<div class="chat" aria-label="चौपाल का नमूना">
<div class="m"><small>बेरावाला · नमूना</small>हमारा घर तालाब के पास था, बड़ी खेजड़ी के नीचे। 7 जुलाई 1986 को निकले थे।</div>
<div class="m me"><small>आप</small>हम भी बेरावाला से हैं, अब शेरपुरा में। नानी कहती हैं मंदिर के पीछे वाला कुआं हमारा था।</div>
<div class="m"><small>कानोलाई</small>पीर जी महाराज के धाम पर हर साल जाते हैं, 2018 में जीर्णोद्धार हुआ।</div>
</div>
<div class="stack">
<div class="callout"><b>चौपाल में क्या होगा</b><ul class="list small" style="margin-top:.4rem"><li>गांव के हिसाब से धागे: कौन किसका पड़ोसी था, किसका कुआं कहां था</li><li>'यह कौन है?' : पुरानी तस्वीरों में लोगों की पहचान</li><li>34 गांव मिलन और होली-वापसी की सूचना</li><li>नियम: सार्वजनिक, सम्मानजनक, बिना राजनीति के</li></ul></div>
<p><a class="btn" href="{self.href('yogdan', depth)}">अभी WhatsApp से जुड़ें</a></p>
</div></div></section>
</div>"""

    def page_yogdan(self, depth=0) -> str:
        missing = [v for v in self.villages if v.get("unit_type") != "umbrella" and (not self.records.get(v["slug"]) or self.records[v["slug"]]["counts"]["accepted"] == 0)]
        names = ", ".join(v["names"]["hi"] for v in missing)
        return f"""<div class="wrap">
<section class="section"><p class="eyebrow">योगदान</p><h1>आपके पास जो है, वही इतिहास है</h1>
<p class="prose" style="margin-top:.6rem">कोई सरकारी दफ्तर इन गांवों की याद नहीं रखता। जो बचा है वह आपके घर में है: बुज़ुर्गों की बातें, ट्रंक में रखा पट्टा, एक पुरानी तस्वीर, या सिर्फ़ यह जानकारी कि आपका परिवार किस गांव से किस गांव गया।</p></section>
<section class="section"><div class="cols">
<div class="callout"><h3>1. अपना गांव बताइए</h3><p class="small" style="margin-top:.4rem">इन गांवों के लिए हमारे पास अभी सिर्फ़ नाम है: <b>{esc(names)}</b>। अगर आपका परिवार इनमें से किसी से है, तो एक संदेश काफ़ी है।</p></div>
<div class="callout"><h3>2. बुज़ुर्गों की आवाज़</h3><p class="small" style="margin-top:.4rem">फोन पर 10–15 मिनट का वीडियो (खड़ा, 9:16), शांत जगह पर। तीन सवाल: गांव कैसा था? छोड़ने का दिन कैसा था? अब कौन कहां है? हमारी टीम भी आकर रिकॉर्ड कर सकती है।</p></div>
<div class="callout"><h3>3. कागज़ और तस्वीरें</h3><p class="small" style="margin-top:.4rem">पट्टा, मुआवजे की रसीद, आवंटन आदेश, स्कूल का प्रमाणपत्र, शादी की तस्वीर। फोन से फोटो खींचकर भेजिए; मूल आपके पास रहेगा। हम व्यक्तिगत विवरण (आधार, खाता नंबर) कभी नहीं छापते।</p></div>
<div class="callout"><h3>4. जो छूट गया, उसे पूरा कीजिए</h3><p class="small" style="margin-top:.4rem">हर गांव के पन्ने के नीचे 'क्या छूटा है' की सूची है: कटा हुआ पाठ, बिना तारीख की तस्वीर, नाम जिनकी वर्तनी पक्की नहीं। जो जानते हों, बता दीजिए।</p></div>
</div></section>
<section class="section"><h2>कैसे भेजें</h2>
<p class="prose" style="margin-top:.6rem">WhatsApp या Google Drive का लिंक, TechnoTaau Team को। नंबर और फॉर्म Phase 1 के अंत तक यहां आएगा। तब तक फेसबुक पर सार्वजनिक पोस्ट का लिंक भी चलेगा।</p>
<div class="callout" style="margin-top:1rem"><b>सहमति</b><p class="small">जो भी आप भेजते हैं, वह इस वेबसाइट और 34 गांव के सामुदायिक अभिलेख में आपके नाम (या गांव के नाम) के श्रेय के साथ छपेगा। आप कभी भी हटाने को कह सकते हैं। दूसरों की तस्वीरें उनकी अनुमति से ही भेजें।</p></div>
</section>
</div>"""

    def page_srot(self, depth=0) -> str:
        st = self.stats
        # bibliography: accepted sources across all units, grouped by type
        by_type: dict[str, dict[str, dict]] = {}
        for slug, r in self.records.items():
            for sid, s in (r.get("sources") or {}).items():
                if s.get("resolution", {}).get("decision") != "accept":
                    continue
                url = s.get("url", "")
                if not url.startswith("http"):
                    continue
                key = url.split("#")[0]
                t = s.get("source_type", "other")
                by_type.setdefault(t, {})[key] = s
        bib = []
        order = ["government", "court", "news", "video", "social", "community", "encyclopedia", "academic", "book", "archive", "blog", "directory", "map", "other"]
        for t in order + [x for x in by_type if x not in order]:
            if t not in by_type:
                continue
            items = sorted(by_type[t].values(), key=lambda s: (s.get("published_date") or "9999"))
            bib.append(f'<h3 style="margin:1rem 0 .4rem">{esc(SOURCE_TYPE_HI.get(t, t))} <span class="small muted">({len(items)})</span></h3><ul class="srcs">' + "".join(
                f'<li><a href="{esc(s["url"])}" rel="noopener">{esc(s.get("title") or s["url"])}</a><div class="meta">{esc(s.get("platform",""))} · {esc(s.get("published_date") or "")}</div></li>' for s in items) + "</ul>")
        return f"""<div class="wrap">
<section class="section"><p class="eyebrow">स्रोत और तरीका</p><h1>हम कैसे जांचते हैं</h1>
<p class="prose" style="margin-top:.6rem">यह वेबसाइट अफ़वाह का बोर्ड नहीं, अभिलेख है। हर गांव के लिए हमने वेब, अखबार, अदालत के फैसले, सरकारी उत्तर, यूट्यूब-फेसबुक के वीडियो और समुदाय के लिखे इतिहास खोजे; हर स्रोत को यह जांच के बाद ही गांव से जोड़ा कि वह इसी बीकानेर वाले गांव की बात करता है (उसी नाम के गांव हरियाणा, हनुमानगढ़ और नोखा में भी हैं)। फिर हर दावे को स्रोतों की संख्या और भरोसे के हिसाब से एक स्तर दिया।</p>
<div class="legend" style="margin-top:1rem">{badge("verified")} सरकारी/अदालती अभिलेख, या दो स्वतंत्र मज़बूत स्रोत &nbsp; {badge("corroborated")} दो अलग स्रोत सहमत &nbsp; {badge("single-source")} अभी एक ही स्रोत &nbsp; {badge("unverified")} सिर्फ़ सूची या अनाम दावा &nbsp; {badge("conflicting")} स्रोत आपस में अलग</div>
</section>
<section class="section"><div class="nums">
<div><b>{st['units']}</b><span>गांव (शोध इकाइयां)</span></div>
<div><b>{st['sources']}</b><span>स्रोत देखे, {st['accepted']} सीधे जोड़े गए</span></div>
<div><b>{st['claims']}</b><span>दावे दर्ज</span></div>
<div><b>{st['verified'] + st['corroborated']}</b><span>पक्के या मिलान वाले</span></div>
<div><b>{st['conflicting']}</b><span>जहां स्रोत अलग कहते हैं</span></div>
<div><b>{st['videos']}</b><span>वीडियो, {st['stills']} तस्वीरें</span></div>
</div></section>
<section class="section"><h2>नियम जो हम नहीं तोड़ते</h2><ul class="list" style="margin-top:.6rem">
<li>सिर्फ़ सार्वजनिक सामग्री; निजी प्रोफ़ाइल या बंद समूह से कुछ नहीं।</li><li>हर तस्वीर के साथ उसके रचनाकार का नाम; परिवारों की तस्वीरें उनकी अनुमति से।</li><li>अधिग्रहण की तारीख या गांवों की गिनती जैसे विवाद छिपाए नहीं जाते, साथ-साथ दिखाए जाते हैं।</li><li>मौत या घटना का कोई आंकड़ा बिना स्रोत के नहीं।</li><li>जो छूटा, वह लिखा जाता है (हर गांव के पन्ने पर 'क्या छूटा है')।</li></ul></section>
<section class="section"><h2>संदर्भ-सूची</h2><p class="small muted">वे स्रोत जो किसी गांव या पूरे 34 गांव से सीधे जुड़े; प्रकार के हिसाब से।</p>{"".join(bib)}</section>
<section class="section"><h2>कौन</h2><p class="prose" style="margin-top:.6rem">TechnoTaau Team, संयोजक जाखड़ सिंह। शोध-प्रणाली और यह साइट खुले भंडार से बनती है; हर पन्ना डेटा से अपने आप बनता है, हाथ से नहीं लिखा जाता, इसलिए नया स्रोत जुड़ते ही पन्ना बदल जाता है। संपर्क और सुझाव: <a href="{self.href('yogdan', depth)}">योगदान</a> पन्ने से।</p></section>
</div>"""

    # ---- build ----------------------------------------------------------------
    def pages(self, depth_top=0) -> list[tuple[str, str, str, int]]:
        """(route, title, body, depth)"""
        out = [
            ("index", "घर", self.page_index(depth_top), depth_top),
            ("gaon", "गांव", self.page_gaon(depth_top), depth_top),
            ("naksha", "नक्शा", self.page_naksha(depth_top), depth_top),
            ("samay", "समय-रेखा", self.page_samay(depth_top), depth_top),
            ("yaadein", "यादें", self.page_yaadein(depth_top), depth_top),
            ("asar", "रेंज का असर", self.page_asar(depth_top), depth_top),
            ("basera", "नया बसेरा", self.page_basera(depth_top), depth_top),
            ("chaupal", "चौपाल", self.page_chaupal(depth_top), depth_top),
            ("yogdan", "योगदान", self.page_yogdan(depth_top), depth_top),
            ("srot", "स्रोत", self.page_srot(depth_top), depth_top),
        ]
        vd = depth_top + 1 if self.mode == "multi" else depth_top
        for v in self.villages:
            out.append((f"gaon/{v['slug']}", v["names"]["hi"], self.page_village(v["slug"], vd), vd))
        return out

    def build_multi(self) -> list[Path]:
        self.mode = "multi"
        self.out.mkdir(parents=True, exist_ok=True)
        self.images = Images(self.out, inline=False)
        written = []
        for route, title, body, depth in self.pages():
            path = self.out / (self.href(route, 0))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.layout(route, title, body, depth), encoding="utf-8")
            written.append(path)
        return written

    def build_single(self, name: str = "preview.html") -> Path:
        """One self-contained HTML (no <html> skeleton: suited to the Artifact host and to any browser)."""
        self.mode = "single"
        self.out.mkdir(parents=True, exist_ok=True)
        self.images = Images(self.out, inline=True)
        sections = []
        titles = {}
        for route, title, body, depth in self.pages():
            titles[route] = title
            sections.append(f'<section class="route" data-route="{esc(route)}" hidden>{body}</section>')
        nav_js = r"""
<script>
(function(){
  var secs=document.querySelectorAll('section.route');
  var links=document.querySelectorAll('nav.main a');
  function show(){
    var r=(location.hash||'#/index').replace(/^#\//,'')||'index';
    var found=false;
    secs.forEach(function(s){var on=s.dataset.route===r; s.hidden=!on; if(on)found=true;});
    if(!found){secs.forEach(function(s){s.hidden=s.dataset.route!=='index';}); r='index';}
    links.forEach(function(a){var t=a.getAttribute('href').replace(/^#\//,''); if(t===r.split('/')[0])a.setAttribute('aria-current','page'); else a.removeAttribute('aria-current');});
    window.scrollTo(0,0);
    var el=document.querySelector('section.route:not([hidden]) h1'); document.title=(el?el.textContent+' · ':'')+'34 गांव';
  }
  window.addEventListener('hashchange',show); show();
})();
</script>"""
        doc = f"""<title>34 गांव</title>
<meta name="description" content="{esc(TAGLINE)}">
{FONT_LINK}
<style>{CSS}
section.route[hidden]{{display:none}}
</style>
{self.topbar("index", 0)}
<main>{"".join(sections)}</main>
{self.footer(0)}
{nav_js}"""
        path = self.out / name
        path.write_text(doc, encoding="utf-8")
        shutil.rmtree(self.out / "_preview_cache", ignore_errors=True)
        return path


def build(out_dir: Path = SITE_DIR, single: bool = True) -> dict:
    s = Site(out_dir)
    files = s.build_multi()
    res = {"pages": len(files), "out": str(out_dir), "stats": dict(s.stats)}
    if single:
        p = s.build_single()
        res["preview"] = str(p)
        res["preview_bytes"] = p.stat().st_size
    return res
