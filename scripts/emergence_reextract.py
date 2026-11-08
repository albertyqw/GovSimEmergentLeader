"""Re-run proposal extraction on a finished run's saved transcripts (no simulation).
Keeps the previous extraction as proposals_prev.  python scripts/emergence_reextract.py RUN_DIR"""
import asyncio
import json
import os
import sys

from dotenv import load_dotenv

from simulation.emergence import llm
from simulation.emergence.run import Run


async def main(d):
  path = os.path.join(d, "run.json")
  log = json.load(open(path))
  r = Run.__new__(Run)
  r.log = {"flags": []}
  months = [m for m in log["months"] if m.get("utterances")]
  convos = [[("Moderator", m["moderator_report"])] + [(u["speaker"], u["text"]) for u in m["utterances"]]
            for m in months]
  res = await asyncio.gather(*(r.extract(m["month"], c) for m, c in zip(months, convos)))
  for m, p in zip(months, res):
    m["proposals_prev"] = m.get("proposals")
    m["proposals"] = p
  log["flags"] += r.log["flags"]
  log["usage"] = llm.usage_summary(llm.USAGE_FILE)
  json.dump(log, open(path, "w"), indent=1, default=str)


if __name__ == "__main__":
  load_dotenv(os.path.abspath(".env"))
  d = sys.argv[1]
  llm.USAGE_FILE = os.path.join(d, "api_usage.jsonl")
  asyncio.run(main(d))
