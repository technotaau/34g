"""Video ingestion: YouTube URL (+ optional local/Drive media) -> source record, metadata, captions, frames, OCR.

Public metadata, captions and comments come from yt-dlp (mweb client, no media). Frames, burned-in subtitle OCR
and speech need the media file, which must be supplied (local path or a link-shared Google Drive file id);
YouTube blocks media downloads from datacenter addresses and we do not work around that.
"""
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from . import INBOX_DIR, RESEARCH_DIR, ROOT
from .normalize import canonical_url

MEDIA_DIR = RESEARCH_DIR / "media"
YTDLP_ARGS = ["--skip-download", "--no-warnings", "--ignore-no-formats-error",
              "--extractor-args", "youtube:player_client=mweb;max_comments=80,all,all,all;comment_sort=top", "--write-comments"]


def video_id(url: str) -> str:
    m = re.search(r"(?:v=|/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    if not m:
        raise ValueError(f"not a YouTube video URL: {url}")
    return m.group(1)


def fetch_meta(url: str) -> dict:
    out = subprocess.run(["yt-dlp", *YTDLP_ARGS, "-J", url], capture_output=True, text=True)
    if out.returncode != 0 or not out.stdout.strip():
        raise RuntimeError("yt-dlp metadata failed: " + out.stderr.strip()[-300:])
    return json.loads(out.stdout)


def fetch_captions(url: str, workdir: Path) -> dict:
    """Download caption tracks (manual first, then auto) as plain text. Returns {lang: text}."""
    workdir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["yt-dlp", "--skip-download", "--no-warnings", "--ignore-no-formats-error",
                    "--extractor-args", "youtube:player_client=mweb", "--write-subs", "--write-auto-subs",
                    "--sub-langs", "hi,en,hi-orig,en-orig,raj", "--sub-format", "vtt", "-o", str(workdir / "cap.%(ext)s"), url],
                   capture_output=True, text=True)
    caps = {}
    for f in sorted(workdir.glob("cap.*.vtt")):
        lang = f.name.split(".")[1]
        lines, last = [], ""
        for ln in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "-->" in ln or ln.startswith(("WEBVTT", "Kind:", "Language:")) or not ln.strip():
                continue
            t = re.sub(r"<[^>]+>", "", ln).strip()
            if t and t != last:
                lines.append(t)
                last = t
        caps[lang] = "\n".join(lines)
    return caps


def trim_meta(d: dict) -> dict:
    keep = ("id", "title", "webpage_url", "channel", "channel_id", "channel_url", "uploader_id", "upload_date", "duration",
            "view_count", "like_count", "comment_count", "tags", "location", "description", "thumbnail", "language")
    t = {k: d.get(k) for k in keep}
    t["subtitle_langs"] = list((d.get("subtitles") or {}).keys())
    t["auto_caption_langs"] = [k for k in (d.get("automatic_captions") or {}) if k in ("hi", "en", "hi-orig", "en-orig")]
    t["comments_public"] = [{"text": c.get("text"), "likes": c.get("like_count") or 0, "is_uploader": bool(c.get("author_is_uploader"))}
                            for c in (d.get("comments") or []) if c.get("text")]
    t["_note"] = "Public metadata via yt-dlp; commenter handles omitted; media not stored in the repository."
    return t


def _snip(text: str, n: int = 40) -> str:
    w = (text or "").split()
    return " ".join(w[:n]) + (" …" if len(w) > n else "")


def build_record(slug: str, meta: dict, captions: dict, related: list[str], village_names: list[str]) -> dict:
    vid = meta["id"]
    url = f"https://www.youtube.com/watch?v={vid}"
    desc = meta.get("description") or ""
    text_all = " ".join([meta.get("title", ""), desc, " ".join(meta.get("tags") or []), " ".join(c["text"] for c in meta["comments_public"])])
    matched = [n for n in village_names if n.lower() in text_all.lower()]
    ud = meta.get("upload_date") or ""
    snippets = [f"Title: {meta.get('title', '')}"]
    if desc:
        snippets.append("Description: " + _snip(desc))
    if meta.get("location"):
        snippets.append(f"Location field: {meta['location']}")
    naming = [c for c in meta["comments_public"] if any(n.lower() in c["text"].lower() for n in village_names)]
    top = sorted(meta["comments_public"], key=lambda c: -c["likes"])[:6]
    seen = set()
    for c in naming + top:
        if len(c["text"]) > 15 and not c["is_uploader"] and c["text"] not in seen:
            seen.add(c["text"])
            snippets.append("Viewer comment: " + _snip(c["text"], 30))
    hashtags = sorted(set(re.findall(r"#([\wऀ-ॿ]+)", desc + " " + " ".join(meta.get("tags") or []))))
    dur = meta.get("duration") or 0
    return {
        "village": slug, "url": url, "title": meta.get("title", ""), "platform": "youtube", "source_type": "video", "media_type": "video",
        "author": f"{meta.get('channel', '')} ({meta.get('uploader_id', '')})", "published_date": f"{ud[:4]}-{ud[4:6]}-{ud[6:]}" if len(ud) == 8 else ud,
        "language": "hi", "found_by_query": "video supplied by TechnoTaau Team",
        "summary": f"YouTube video '{meta.get('title', '')}' ({dur // 60}:{dur % 60:02d}) by {meta.get('channel', '')}. " + _snip(desc, 60),
        "topics": ["media_visual"], "period": "2016_present" if ud >= "2016" else "",
        "geo_mentions": [meta.get("location")] if meta.get("location") else [], "direct_mention": bool(matched),
        "name_form_matched": matched[0] if matched else "", "evidence_snippets": snippets,
        "entities": {"people": [], "places": [], "events": [], "organizations": [meta.get("channel", "")]},
        "license": "Standard YouTube licence (uploader's copyright); embed via YouTube player permitted",
        "attribution": f"{meta.get('channel', '')}, YouTube, {ud[:4] if ud else ''}, {url}",
        "is_primary": True, "related_villages": related, "claims": [],
        "media": {"channel": meta.get("channel", ""), "uploader": meta.get("uploader_id", ""),
                  "transcript_available": ("captions: " + ", ".join(captions)) if captions else "no caption tracks (manual or auto)",
                  "timestamps": f"{len(meta['comments_public'])} public comments; {meta.get('view_count')} views; hashtags: {' '.join(hashtags)[:200]}"},
        "notes": "Auto-built from public metadata by gaon34.video; claims to be added by a researcher or the discovery/verification agents after viewing.",
    }


def download_drive(file_id: str, dest: Path) -> Path:
    url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
    subprocess.run(["curl", "-sL", "-o", str(dest), url], check=True)
    head = dest.open("rb").read(64)
    if b"<html" in head.lower() or b"<!doctype" in head.lower():
        dest.unlink(missing_ok=True)
        raise RuntimeError("Drive returned a sign-in page: the file must be shared as 'Anyone with the link'")
    return dest


def extract_frames(media: Path, out_dir: Path, every: int, vid: str, source_url: str, credit: str) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(media)],
                               capture_output=True, text=True).stdout.strip() or 0)
    frames = []
    t = 2
    while t < dur:
        f = frames_dir / f"{t:04d}s.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(media), "-frames:v", "1", "-q:v", "3", "-y", str(f)])
        if f.exists():
            frames.append({"file": f"frames/{f.name}", "timestamp_s": t, "timestamp": f"{t // 60:02d}:{t % 60:02d}", "description": "", "tags": []})
        t += every
    # contact sheet for human annotation
    subprocess.run(["ffmpeg", "-v", "error", "-i", str(media), "-vf", f"fps=1/{every},scale=320:-1,drawtext=text='%{{pts\\:hms}}':fontsize=18:fontcolor=yellow:box=1:boxcolor=black@0.6:x=4:y=4,tile=5x{max(1, -(-len(frames) // 5))}",
                    "-frames:v", "1", "-y", str(out_dir / "contact_sheet.png")])
    manifest = {"video_id": vid, "source_url": source_url, "credit": credit, "extracted": date.today().isoformat(), "every_s": every,
                "rights": "Stills from a third-party video for research reference. Creator's copyright; consent of identifiable people needed before publication.",
                "count": len(frames), "frames": frames}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


def run_ocr(media: Path, out_json: Path, band: float, lang: str, whisper: str | None, speech_lang: str = "hi", ocr_every: float = 1.0) -> None:
    cmd = [sys.executable, str(ROOT / "scripts" / "video_extract.py"), str(media), "--out", str(out_json), "--lang", lang, "--band", str(band), "--every", str(ocr_every)]
    cmd += ["--whisper", whisper, "--language", speech_lang] if whisper else ["--no-whisper"]
    subprocess.run(cmd, check=False)


def local_meta(media: Path, title: str, credit: str, source_url: str) -> dict:
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(media)],
                               capture_output=True, text=True).stdout.strip() or 0)
    return {"id": re.sub(r"[^A-Za-z0-9_-]", "_", media.stem)[:40], "title": title, "channel": credit, "uploader_id": "", "upload_date": "",
            "duration": int(dur), "description": "", "tags": [], "location": None, "view_count": None, "comments_public": [],
            "webpage_url": source_url, "_note": "Local/Drive media, not a YouTube video; metadata from the file only."}


def ingest_video(slug: str, url: str, related=None, media: Path | None = None, drive_id: str | None = None, every: int = 20,
                 ocr_band: float = 0.88, ocr_lang: str = "hin+eng", whisper: str | None = None, village_names=None,
                 title: str | None = None, credit: str | None = None, ocr_every: float = 1.0) -> dict:
    if not re.search(r"youtube\.com|youtu\.be", url):
        return ingest_local(slug, url, related, media, drive_id, every, ocr_band, ocr_lang, whisper, village_names, title or "", credit or "", ocr_every)
    vid = video_id(url)
    inbox = INBOX_DIR / slug
    inbox.mkdir(parents=True, exist_ok=True)
    scratch = Path("/tmp") / "gaon34_video" / vid
    scratch.mkdir(parents=True, exist_ok=True)
    raw = fetch_meta(url)
    meta = trim_meta(raw)
    captions = fetch_captions(url, scratch / "caps") if (raw.get("subtitles") or raw.get("automatic_captions")) else {}
    (inbox / f"yt_{vid}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if captions:
        for lang, text in captions.items():
            (inbox / f"yt_{vid}.captions.{lang}.txt").write_text(text, encoding="utf-8")
    rec = build_record(slug, meta, captions, list(related or []), village_names or [])
    result = {"video_id": vid, "title": meta["title"], "captions": list(captions), "comments": len(meta["comments_public"]), "frames": 0}
    if drive_id and not media:
        media = download_drive(drive_id, scratch / f"{vid}.mp4")
    if media:
        credit = f"{meta.get('channel', '')} (YouTube {vid})"
        man = extract_frames(Path(media), MEDIA_DIR / slug / vid, every, vid, rec["url"], credit)
        result["frames"] = man["count"]
        run_ocr(Path(media), inbox / f"{vid}.content.json", ocr_band, ocr_lang, whisper, "hi", ocr_every)
        rec["media"]["frames"] = f"{man['count']} stills in research/media/{slug}/{vid}/ (manifest.json, contact_sheet.png)"
        cj = inbox / f"{vid}.content.json"
        if cj.exists():
            c = json.loads(cj.read_text(encoding="utf-8"))
            lines = c.get("ocr_subtitles") or []
            segs = ((c.get("speech") or {}).get("segments")) or []
            rec["media"]["transcript_available"] += f"; burned-in subtitle OCR: {len(lines)} lines; speech segments: {len(segs)} in {cj.name}"
            result["speech_segments"] = len(segs)
            rec["evidence_snippets"] += [f"On-screen text {l['start']:.0f}s: {_snip(l['text'], 30)}" for l in lines[:12]]
            result["ocr_lines"] = len(lines)
    payload = {"village": slug, "agent_notes": f"gaon34.video ingest of {url} on {date.today().isoformat()}", "searches_used": 0, "sources": [rec]}
    (inbox / f"video_{vid}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    result["inbox_file"] = str(inbox / f"video_{vid}.json")
    return result


def ingest_local(slug, url, related, media, drive_id, every, ocr_band, ocr_lang, whisper, village_names, title, credit, ocr_every=1.0) -> dict:
    """A video that exists only as a file (e.g. a family clip shared via Drive). url = where it came from (Drive view URL)."""
    inbox = INBOX_DIR / slug
    inbox.mkdir(parents=True, exist_ok=True)
    scratch = Path("/tmp") / "gaon34_video" / re.sub(r"[^A-Za-z0-9]", "_", url)[-40:]
    scratch.mkdir(parents=True, exist_ok=True)
    if drive_id and not media:
        media = download_drive(drive_id, scratch / "media.mp4")
    if not media:
        raise ValueError("local ingest needs --media or --drive-id")
    media = Path(media)
    meta = local_meta(media, title or media.stem, credit or "unknown (supplied by TechnoTaau Team)", url)
    vid = meta["id"]
    (inbox / f"local_{vid}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    rec = build_record(slug, meta, {}, list(related or []), village_names or [])
    rec.update({"url": url, "platform": "google_drive" if "drive.google" in url else "local_file", "source_type": "video",
                "attribution": f"{meta['channel']}, video file '{media.name}'", "license": "unknown; obtain from the person who shot it",
                "found_by_query": "video file supplied by TechnoTaau Team", "notes": "Non-YouTube media; provenance recorded from file name and supplier."})
    man = extract_frames(media, MEDIA_DIR / slug / vid, every, vid, url, meta["channel"])
    run_ocr(media, inbox / f"{vid}.content.json", ocr_band, ocr_lang, whisper, "hi", ocr_every)
    rec["media"]["frames"] = f"{man['count']} stills in research/media/{slug}/{vid}/ (manifest.json, contact_sheet.png)"
    cj = inbox / f"{vid}.content.json"
    result = {"video_id": vid, "title": meta["title"], "captions": [], "comments": 0, "frames": man["count"]}
    if cj.exists():
        c = json.loads(cj.read_text(encoding="utf-8"))
        lines = c.get("ocr_subtitles") or []
        segs = ((c.get("speech") or {}).get("segments")) or []
        rec["media"]["transcript_available"] = f"OCR lines: {len(lines)}; speech segments: {len(segs)} in {cj.name}"
        rec["evidence_snippets"] += [f"On-screen text {l['start']:.0f}s: {_snip(l['text'], 30)}" for l in lines[:12]]
        result.update({"ocr_lines": len(lines), "speech_segments": len(segs)})
    payload = {"village": slug, "agent_notes": f"gaon34.video local ingest of {media.name} on {date.today().isoformat()}", "searches_used": 0, "sources": [rec]}
    (inbox / f"video_{vid}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    result["inbox_file"] = str(inbox / f"video_{vid}.json")
    return result
