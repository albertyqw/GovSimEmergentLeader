"""Per-agent dated memory, stored in GovSimElect's MEMORY.md format and retrieved with
GovSimElect's scoring (RetrieveComponent): score = 1 * recency + 3 * normalised importance,
always_include entries ranked first, top-k returned.

Two deliberate differences from upstream retrieve.py, both noted in EMERGENCE.md:
- upstream computes recency as 0.99**i over entries sorted OLDEST-first, so the oldest
  memory gets the highest recency score; here i counts from the newest entry.
- importance is rated by one batched call per agent per batch of new entries (same 1-10
  significance question as upstream store_prompts) instead of one call per entry.
"""
import datetime as dt
import os

from simulation.persona.memory.associative_memory import AssociativeMemory, Event

RECENCY_W, IMPORTANCE_W, DECAY = 1.0, 3.0, 0.99
FAR = dt.datetime(2099, 12, 31)


class Memory:
  def __init__(self, base_path):
    self.entries = []  # dicts: created, kind, text, importance, always, expires
    self.am = AssociativeMemory(base_path)
    self.am.init_memory_md()

  def add(self, created, kind, text, importance=5.0, always=False, expires=None):
    e = {"created": created, "kind": kind, "text": text, "importance": float(importance),
         "always": always, "expires": expires or FAR}
    self.entries.append(e)
    node = Event(len(self.entries), "", "", "", text, created, e["expires"])
    node.importance_score = e["importance"]
    node.always_include = always
    self.am.append_to_memory_md(node)
    return e

  def rewrite_md(self):
    self.am.init_memory_md()
    for i, e in enumerate(self.entries):
      node = Event(i + 1, "", "", "", e["text"], e["created"], e["expires"])
      node.importance_score = e["importance"]
      node.always_include = e["always"]
      self.am.append_to_memory_md(node)

  def live(self, now):
    # Unlike upstream, always_include entries also expire (the monthly stock observation and
    # universalization line are only valid for their month, as in GovSim).
    return sorted([e for e in self.entries if e["expires"] > now], key=lambda e: e["created"])

  def retrieve(self, now, k=10):
    es = self.live(now)
    n = len(es)
    scored = []
    for i, e in enumerate(es):
      rec = DECAY ** (n - 1 - i)  # newest = 1.0
      imp = (e["importance"] - 1) / 9
      scored.append([RECENCY_W * rec + IMPORTANCE_W * imp, e])
    top = max((s for s, _ in scored), default=0)
    for s in scored:
      if s[1]["always"]:
        s[0] = top + 1
    scored.sort(key=lambda x: -x[0])
    chosen = [e for _, e in scored[:k]]
    return sorted(chosen, key=lambda e: e["created"])

  def all_text(self, now):
    return self.live(now)


def memory_prompt(name, mems):
  res = "".join(f"- {e['created'].strftime('%Y-%m-%d')}: {e['text']}\n" for e in mems)
  return f"Key memories of {name} (format: YYYY-MM-DD: memory):\n{res}\n"
