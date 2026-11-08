"""Anthropic calls for the leader-emergence runs.

API-default sampling (claude-haiku-5-5 rejects temperature under API version 2026-10-21),
thinking disabled, a per-process concurrency cap, and patient retries on 429/overload so
parallel runs do not die on the org's tokens-per-minute limit. Usage goes to a JSONL file.
"""
import asyncio
import json
import os
import random

import anthropic

MODEL = "claude-haiku-5-5"
PRICES = {"claude-haiku-5-5": (0.10, 0.50)}
_client = None
_sem = None
USAGE_FILE = None


def _get():
  global _client, _sem
  if _client is None:
    _client = anthropic.AsyncAnthropic(max_retries=3)
    _sem = asyncio.Semaphore(int(os.environ.get("EMERGENCE_CONCURRENCY", "6")))
  return _client, _sem


async def ask(prompt: str, max_tokens: int = 600, tag: str = "") -> str:
  client, sem = _get()
  for attempt in range(30):
    try:
      async with sem:
        out = await client.messages.create(
            model=MODEL, max_tokens=max_tokens, thinking={"type": "disabled"},
            messages=[{"role": "user", "content": prompt}])
      break
    except (anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError):
      await asyncio.sleep(min(90, 10 + 5 * attempt) * (0.5 + random.random()))
  else:
    raise RuntimeError(f"gave up after 30 attempts: {tag}")
  if USAGE_FILE:
    with open(USAGE_FILE, "a") as f:
      f.write(json.dumps({"model": MODEL, "input_tokens": out.usage.input_tokens,
                          "output_tokens": out.usage.output_tokens,
                          "stop_reason": out.stop_reason, "tag": tag}) + "\n")
  if out.stop_reason == "refusal":
    return ""
  return "".join(b.text for b in out.content if b.type == "text")


def usage_summary(path):
  tot = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
  if path and os.path.exists(path):
    for l in open(path):
      u = json.loads(l)
      p_in, p_out = PRICES.get(u["model"], (0, 0))
      tot["calls"] += 1
      tot["input_tokens"] += u["input_tokens"]
      tot["output_tokens"] += u["output_tokens"]
      tot["cost_usd"] += u["input_tokens"] * p_in / 1e6 + u["output_tokens"] * p_out / 1e6
  tot["cost_usd"] = round(tot["cost_usd"], 4)
  return tot
