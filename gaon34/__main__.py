"""CLI: python -m gaon34 <command> ...  (see docs/RESEARCH_WORKFLOW.md)"""
import argparse
import json
import sys
from pathlib import Path

from . import INBOX_DIR
from .pipeline import ingest, rebuild
from .prompts import discovery_prompt, verification_prompt
from .queries import generate_queries
from .registry import load_villages, get_village, add_village
from .report import build_record, render_report, render_index
from .store import load_sources, save_verdicts, load_runs


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gaon34")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("villages", help="list research units")
    a = sub.add_parser("add-village"); a.add_argument("--slug", required=True); a.add_argument("--en", required=True); a.add_argument("--hi", required=True)
    a.add_argument("--variants", nargs="*", default=[]); a.add_argument("--negative", nargs="*", default=[]); a.add_argument("--status", default="acquired"); a.add_argument("--notes", default="")
    q = sub.add_parser("queries", help="print search matrix"); q.add_argument("slug"); q.add_argument("--tier", type=int, default=3); q.add_argument("--channel", nargs="*"); q.add_argument("--json", action="store_true")
    p = sub.add_parser("prompt", help="print discovery-agent prompt"); p.add_argument("slug"); p.add_argument("--budget", type=int, default=30); p.add_argument("--tier", type=int, default=3); p.add_argument("--channel", nargs="*")
    pb = sub.add_parser("prompts", help="write discovery prompts for many units to a directory"); pb.add_argument("--out", required=True); pb.add_argument("--slugs", nargs="*"); pb.add_argument("--pending", action="store_true", help="only units with no sources yet"); pb.add_argument("--budget", type=int, default=25); pb.add_argument("--tier", type=int, default=3)
    i = sub.add_parser("ingest", help="ingest agent JSON into the store"); i.add_argument("slug"); i.add_argument("file", nargs="?"); i.add_argument("--run-id")
    vp = sub.add_parser("verify-prompt", help="print verification-agent prompt"); vp.add_argument("slug"); vp.add_argument("--max", type=int, default=25)
    iv = sub.add_parser("ingest-verdicts"); iv.add_argument("slug"); iv.add_argument("file", nargs="?")
    b = sub.add_parser("build", help="rebuild record.json + report.md"); b.add_argument("slug", nargs="?"); b.add_argument("--all", action="store_true")
    vd = sub.add_parser("video", help="ingest a YouTube video: metadata, captions, comments (+frames/OCR if media given)")
    vd.add_argument("slug"); vd.add_argument("url"); vd.add_argument("--related", nargs="*", default=[])
    vd.add_argument("--media", help="local video file"); vd.add_argument("--drive-id", help="link-shared Google Drive file id")
    vd.add_argument("--every", type=int, default=20, help="seconds between extracted frames"); vd.add_argument("--ocr-band", type=float, default=0.88)
    vd.add_argument("--ocr-lang", default="hin+eng"); vd.add_argument("--whisper", default=None, help="whisper model size, e.g. small/medium (off by default)")
    sub.add_parser("status")
    args = ap.parse_args(argv)

    if args.cmd == "villages":
        for v in load_villages():
            n = len(load_sources(v["slug"]))
            print(f"{v['slug']:14} {v['names']['hi']:14} {v['names']['en']:18} {v.get('status',''):18} sources={n}")
    elif args.cmd == "add-village":
        e = add_village(args.slug, args.en, args.hi, args.variants, args.status, args.negative, args.notes)
        print(json.dumps(e, ensure_ascii=False, indent=1))
    elif args.cmd == "queries":
        qs = generate_queries(get_village(args.slug), max_tier=args.tier, channels=args.channel)
        print(json.dumps(qs, ensure_ascii=False, indent=1) if args.json else "\n".join(f"T{x['tier']} {x['channel']:8} {x['query']}" for x in qs))
    elif args.cmd == "prompt":
        print(discovery_prompt(args.slug, args.budget, args.tier, args.channel))
    elif args.cmd == "prompts":
        out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
        slugs = args.slugs or [v["slug"] for v in load_villages() if not (args.pending and load_sources(v["slug"]))]
        for s in slugs:
            (out / f"prompt_{s}.md").write_text(discovery_prompt(s, args.budget, args.tier), encoding="utf-8")
            print(out / f"prompt_{s}.md")
    elif args.cmd == "ingest":
        f = Path(args.file) if args.file else INBOX_DIR / args.slug / "discovery.json"
        if not f.exists():
            sys.exit(f"no inbox file: {f}")
        stats = ingest(args.slug, f, args.run_id)
        build_record(args.slug); render_report(args.slug); render_index()
        print(json.dumps(stats, ensure_ascii=False, indent=1))
    elif args.cmd == "verify-prompt":
        print(verification_prompt(args.slug, args.max))
    elif args.cmd == "ingest-verdicts":
        f = Path(args.file) if args.file else INBOX_DIR / args.slug / "verdicts.json"
        data = json.loads(f.read_text(encoding="utf-8"))
        verdicts = {v["id"]: v for v in (data["verdicts"] if isinstance(data, dict) else data)}
        save_verdicts(args.slug, verdicts)
        rebuild(args.slug); build_record(args.slug); render_report(args.slug); render_index()
        print(f"stored {len(verdicts)} verdicts for {args.slug}")
    elif args.cmd == "build":
        slugs = [v["slug"] for v in load_villages()] if args.all else [args.slug]
        for s in slugs:
            if load_sources(s):
                rebuild(s); build_record(s); render_report(s)
        print(render_index())
    elif args.cmd == "video":
        from .video import ingest_video
        v = get_village(args.slug)
        res = ingest_video(args.slug, args.url, args.related, Path(args.media) if args.media else None, args.drive_id, args.every,
                           args.ocr_band, args.ocr_lang, args.whisper, v["all_names"])
        stats = ingest(args.slug, Path(res["inbox_file"]))
        build_record(args.slug); render_report(args.slug); render_index()
        print(json.dumps({**res, "ingest": {k: stats[k] for k in ("new", "updated", "invalid", "total_after")}}, ensure_ascii=False, indent=1))
    elif args.cmd == "status":
        for v in load_villages():
            runs = load_runs(v["slug"])
            print(f"{v['slug']:14} sources={len(load_sources(v['slug'])):3} runs={len(runs)} last={runs[-1]['at'][:19] if runs else '-'}")


if __name__ == "__main__":
    sys.exit(main())
