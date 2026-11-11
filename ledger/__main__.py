"""Line-oriented ingestion, audit history and journal counts."""
import argparse
import json
from pathlib import Path
from .service import Ledger
from .model import ValidationError, ConflictError

def main():
    parser = argparse.ArgumentParser(prog="python -m ledger")
    parser.add_argument("--db", required=True)
    subs = parser.add_subparsers(dest="command", required=True)
    ingest = subs.add_parser("ingest")
    ingest.add_argument("file", help="UTF-8 JSONL event file")
    for name in ("events", "counts"):
        cmd = subs.add_parser(name)
        cmd.add_argument("--tenant", required=True)
    subs.add_parser("history")
    args = parser.parse_args()
    try:
        with Ledger(args.db) as ledger:
            if args.command == "ingest":
                values = [json.loads(line) for line in Path(args.file).read_text(encoding="utf-8").splitlines() if line.strip()]
                output = ledger.ingest(values)
            elif args.command == "history":
                output = ledger.history()
            else:
                output = getattr(ledger, args.command)(args.tenant)
        print(json.dumps(output, sort_keys=True, ensure_ascii=False))
        return 0
    except (ValidationError, ConflictError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": type(exc).__name__, "detail": str(exc)}))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
