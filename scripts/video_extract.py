#!/usr/bin/env python3
"""Extract research content from a video file: burned-in subtitles (OCR) and speech (Whisper).

Usage:
  python3 scripts/video_extract.py <video.mp4> --out research/inbox/<slug>/<id>.content.json [--lang hin+eng] [--every 1.0]
  [--band 0.72] [--whisper small] [--no-whisper] [--no-ocr]

Needs: ffmpeg, tesseract (+ tesseract-ocr-hin), pip install faster-whisper.
Output: JSON with timestamped OCR subtitle lines and Whisper segments, plus a Markdown sidecar (<out>.md).
The media file itself is never copied into the repository.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from difflib import SequenceMatcher
from pathlib import Path


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def duration_of(video: Path) -> float:
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)]).stdout.strip()
    return float(out)


def ocr_subtitles(video: Path, every: float, band: float, lang: str) -> list[dict]:
    """Sample one frame every `every` seconds, crop the bottom (1-band) of the frame, OCR it, collapse repeats."""
    tmp = Path(tempfile.mkdtemp(prefix="vx_"))
    # crop: keep bottom part of frame where burned-in subtitles live; upscale x2 to help tesseract
    vf = f"fps=1/{every},crop=iw:ih*{1 - band:.3f}:0:ih*{band:.3f},scale=iw*2:ih*2,format=gray,eq=contrast=1.6"
    run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", vf, str(tmp / "f_%05d.png")])
    lines, last = [], ""
    for i, png in enumerate(sorted(tmp.glob("f_*.png"))):
        t = i * every
        try:
            txt = run(["tesseract", str(png), "-", "-l", lang, "--psm", "6"]).stdout
        except subprocess.CalledProcessError:
            continue
        txt = " ".join(l.strip() for l in txt.splitlines() if len(l.strip()) > 1)
        txt = re.sub(r"\s+", " ", txt).strip()
        if len(re.sub(r"[^\w]", "", txt)) < 4:
            continue
        if SequenceMatcher(None, txt, last).ratio() > 0.8:
            lines[-1]["end"] = t + every
            continue
        lines.append({"start": round(t, 1), "end": round(t + every, 1), "text": txt})
        last = txt
    shutil.rmtree(tmp, ignore_errors=True)
    return lines


def transcribe(video: Path, model_size: str, language: str | None = None) -> dict:
    """Force `language` (e.g. 'hi') for Rajasthani/Marwari speech: auto-detect often picks Urdu and emits Arabic script."""
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(video), vad_filter=True, beam_size=5, language=language)
    segs = [{"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip()} for s in segments]
    return {"language": info.language, "language_probability": round(info.language_probability, 3), "segments": segs}


WORD = re.compile(r"^[\[(]?[A-Za-z0-9\u0900-\u097F][A-Za-z0-9\u0900-\u097F'’.,!?:;()\[\]-]*$")


def clean_line(text: str) -> str:
    """Keep only word-like tokens; drop lines that are mostly picture noise."""
    toks = text.split()
    good = [t for t in toks if WORD.match(t) and len(re.sub(r"[^A-Za-z0-9\u0900-\u097F]", "", t)) >= 2]
    real = [t for t in good if (len(t) >= 3 and re.search(r"[aeiouAEIOU\u0900-\u097F]", t) and not re.fullmatch(r"[A-Z]{3,}", t)) or re.search(r"\d", t)]
    if len(good) < 2 or len(good) / max(1, len(toks)) < 0.6 or len(real) < 2 or len(real) / len(good) < 0.5:
        return ""
    # trim leading junk before the first capitalised/bracketed word run
    out = " ".join(good)
    return out.strip()


def clean_lines(lines: list[dict]) -> list[dict]:
    cleaned, last = [], ""
    for l in lines:
        t = clean_line(l["text"])
        if not t:
            continue
        if cleaned and SequenceMatcher(None, t, last).ratio() > 0.75:
            cleaned[-1]["end"] = l["end"]
            if len(t) > len(cleaned[-1]["text"]):
                cleaned[-1]["text"] = t
            continue
        cleaned.append({"start": l["start"], "end": l["end"], "text": t})
        last = t
    return cleaned


def fmt(t: float) -> str:
    m, s = divmod(int(t), 60)
    return f"{m:02d}:{s:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--out", required=True)
    ap.add_argument("--lang", default="hin+eng"); ap.add_argument("--every", type=float, default=1.0)
    ap.add_argument("--band", type=float, default=0.72, help="fraction of frame height above the subtitle band")
    ap.add_argument("--whisper", default="small"); ap.add_argument("--no-whisper", action="store_true"); ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--reclean", help="re-filter an existing output JSON instead of processing the video")
    ap.add_argument("--language", default=None, help="force Whisper language code, e.g. hi")
    a = ap.parse_args()
    video, out = Path(a.video), Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if a.reclean:
        result = json.loads(Path(a.reclean).read_text(encoding="utf-8"))
        result["ocr_subtitles"] = clean_lines(result.get("ocr_raw") or result.get("ocr_subtitles") or [])
    else:
        result = {"video": video.name, "duration_s": duration_of(video), "ocr_subtitles": [], "ocr_raw": [], "speech": None,
                  "_note": "Derived research notes; quote sparingly and attribute to the uploader. Media not stored in repo."}
        if not a.no_ocr:
            result["ocr_raw"] = ocr_subtitles(video, a.every, a.band, a.lang)
            result["ocr_subtitles"] = clean_lines(result["ocr_raw"])
    if not a.no_whisper and not a.reclean:
        try:
            result["speech"] = transcribe(video, a.whisper, a.language)
        except Exception as e:  # model download or import failure should not lose the OCR result
            result["speech"] = {"error": str(e)}
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    md = [f"# Video content notes: {video.name}", f"Duration: {fmt(result['duration_s'])}", "", "## Burned-in subtitles (OCR)"]
    md += [f"- [{fmt(l['start'])}–{fmt(l['end'])}] {l['text']}" for l in result["ocr_subtitles"]] or ["_none detected_"]
    md += ["", "## Speech (Whisper)"]
    sp = result["speech"] or {}
    if sp.get("segments"):
        md.append(f"Language: {sp.get('language')} ({sp.get('language_probability')})")
        md += [f"- [{fmt(s['start'])}–{fmt(s['end'])}] {s['text']}" for s in sp["segments"]]
    else:
        md.append(f"_not available_ {sp.get('error', '')}")
    out.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"OCR lines: {len(result['ocr_subtitles'])}; speech segments: {len(sp.get('segments') or [])}; wrote {out} and {out.with_suffix('.md')}")


if __name__ == "__main__":
    sys.exit(main())
