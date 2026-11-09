"""Export the separately maintained running nomination-intervention table."""

import argparse
import csv
import json
import sqlite3
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=root / "runs/.control/nomination_judgments.sqlite")
    parser.add_argument("--output", type=Path, default=root / "runs/nomination_judgments.tsv")
    args = parser.parse_args()
    events = []
    if args.database.exists():
        with sqlite3.connect(f"file:{args.database}?mode=ro", uri=True) as db:
            events = [json.loads(row[0]) for row in db.execute("SELECT data FROM nomination_judgments ORDER BY rowid")]
    fields = ["timestamp", "event_id", "condition", "seed", "cycle", "position", "speaker_identity", "raw_nomination",
              "judge_answer", "judge_reason", "resolution_source", "resolved_identity", "random_key", "cost"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for event in events:
            writer.writerow({**event, "random_key": (event.get("random_fallback") or {}).get("key")})
    print(f"Exported {len(events)} intervention rows to {args.output}")


if __name__ == "__main__":
    main()
