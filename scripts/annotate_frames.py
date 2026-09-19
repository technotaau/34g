"""Apply frame descriptions to a media manifest from a small ranges file.

Usage: python3 scripts/annotate_frames.py research/media/<slug>/<video_id>/manifest.json research/inbox/<slug>/annot_<video_id>.json

The ranges file: {"rights": "...optional override...", "ranges": [[start_s, end_s, "description (en)", "विवरण (hi)", ["tag", ...]], ...]}
A frame gets the first range whose start_s <= timestamp_s <= end_s. Frames left without a range keep their old text.
"""
import json
import sys
from pathlib import Path


def main(manifest: Path, ranges_file: Path) -> None:
    m = json.loads(manifest.read_text(encoding="utf-8"))
    a = json.loads(ranges_file.read_text(encoding="utf-8"))
    if a.get("rights"):
        m["rights"] = a["rights"]
    if a.get("credit"):
        m["credit"] = a["credit"]
    hit = 0
    for f in m["frames"]:
        t = f.get("timestamp_s", 0)
        for r in a["ranges"]:
            if r[0] <= t <= r[1]:
                f["description"], f["description_hi"], f["tags"] = r[2], r[3], r[4]
                hit += 1
                break
    manifest.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{manifest}: {hit}/{len(m['frames'])} frames described")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
