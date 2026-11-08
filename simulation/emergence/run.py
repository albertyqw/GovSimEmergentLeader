"""One leader-emergence run: python -m simulation.emergence.run --arm 0 --seed 1 --out DIR

Month loop (GovSim order): observe stock -> harvest (concurrent) -> discussion opened by
the moderator's catch report (opener set by the arm, then random order, max 20 turns) ->
store utterances -> reflection -> proposal extraction -> departing-tenant interviews ->
regrowth. Collapse (stock after fishing < 5) ends the run. Final interviews at the end.
"""
import argparse
import asyncio
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

from dotenv import load_dotenv

from simulation.emergence import llm
from simulation.emergence.design import (CAPACITY, COLLAPSE, MAX_TURNS, MONTHS, N, OUTSIDER_GOALS,
                                         PROSOCIAL_GOALS, TOP_K, Design, psi, universalization_f)
from simulation.emergence.memory import Memory, memory_prompt

START = dt.datetime(2024, 1, 1)
REASON = "Let's think step-by-step."


def month_date(m, day=1, sec=0):
  y, mo = divmod(m - 1, 12)
  return dt.datetime(2024 + y, mo + 1, day, 8, 0, 0) + dt.timedelta(seconds=sec)


def comma(names):
  return names[0] if len(names) == 1 else ", ".join(names[:-1]) + f", and {names[-1]}"


class Agent:
  def __init__(self, tenant, base):
    self.name, self.seat, self.persona = tenant["name"], tenant["seat"], tenant["persona"]
    self.start, self.end = tenant["start"], tenant["end"]
    self.mem = Memory(os.path.join(base, "memories", self.name))
    self.income = 0


class Run:
  def __init__(self, arm, seed, out, months=MONTHS):
    self.d = Design(seed, arm)
    self.out, self.months = out, months
    self.log = {"config": {"arm": arm, "seed": seed, "model": llm.MODEL, "n_agents": N,
                           "months": months, "max_turns": MAX_TURNS, "top_k": TOP_K,
                           "regen_range": [1.0, 3.0], "capacity": CAPACITY, "collapse_below": COLLAPSE,
                           "sampling": "API default (temperature not settable on this model)"},
                "design": self.d.describe(), "months": [], "interviews": [], "flags": []}
    self.agents = {}
    self.stock = CAPACITY
    self._t = 0

  def tick(self):
    self._t += 1
    return self._t

  # ------------------------------------------------------------ prompts
  def system(self, a, month):
    text = (f"You are {a.name}, a fisherman, and you fish every month in a lake along with four other"
            " fishermen. The lake has a carrying capacity of 100 tons of fish. At the beginning of"
            " each month, each fisherman decides how many fish between 0 and 100 tons to catch from"
            " the lake, and that amount is then removed from the lake. At the end of the month, the"
            " remaining fish will reproduce and the population will increase. The regeneration"
            " factor of increase is sampled uniformly between 1.0 and 3.0 for each month, up to the"
            " carrying capacity. For every ton of fish caught, a fisherman earns one thousand dollars."
            " Each fisherman's goal is to optimize his income in the long run over many months. At"
            " the end of each month, the number of fish caught by each fisherman will be revealed,"
            " and the fishermen will have the opportunity to communicate with each other. They can"
            " use this as an opportunity to negotiate and persuade others to influence their"
            " behavior in the next month. For example, if there are 90 tons of fish at the beginning"
            " of the month and the fishermen catch a total of 30 fish, given a regeneration factor of"
            " 2.0, there will be 60 tons of fish left at the end of the month before reproduction,"
            " and 100 tons after reproduction.")
    if a.persona == "prosocial":
      text += PROSOCIAL_GOALS
    elif a.persona == "outsider":
      text += " " + OUTSIDER_GOALS
    if self.d.public_roster():
      lines = [f"{t['name']}: months {t['start']}-{t['end']}"
               for t in sorted(self.d.roster, key=lambda t: (t["seat"], t["start"]))]
      text += (f"\n\nThis is month {month}. Fishing roster (public, everyone sees it): "
               + "; ".join(lines) + f". You will fish here until month {a.end}. Only the fish you"
               " catch during your tenure count as your income.")
    return text + "\n"

  def retrieve(self, a, month, now, purpose):
    mems = a.mem.retrieve(now, TOP_K)
    self.cur["retrievals"].append({"agent": a.name, "purpose": purpose,
                                   "memories": [[e["created"].strftime("%Y-%m-%d"), e["text"]] for e in mems]})
    return mems

  async def rate(self, a, entries, month):
    if not entries:
      return
    items = "".join(f"{i+1}) {e['text']}\n" for i, e in enumerate(entries))
    prompt = (self.system(a, month) + f"\nTask: Rate the significance of each of the following memories"
              f" for {a.name} on a scale from 1 to 10, where 1 is mundane (e.g., routine greetings) and"
              f" 10 is highly significant.\n{items}\nOutput one line per memory in the form"
              " '<number>: <rating>' and nothing else.")
    txt = await llm.ask(prompt, 300, f"rate:{a.name}")
    got = {int(k): int(v) for k, v in re.findall(r"(\d+)\s*[:)\-]\s*(\d+)", txt)}
    for i, e in enumerate(entries):
      v = got.get(i + 1)
      e["importance"] = float(min(10, max(1, v))) if v else 5.0
    a.mem.rewrite_md()

  # ------------------------------------------------------------ phases
  async def harvest_one(self, a, month):
    now = month_date(month, 1, self.tick())
    mems = self.retrieve(a, month, now, "harvest")
    prompt = (self.system(a, month) + f"Location: lake\nDate: {now.strftime('%Y-%m-%d')}\n\n"
              + memory_prompt(a.name, mems) + "\n"
              + f"Task: With a fishing range set between 0-{self.stock}, how many tons of fish would"
              f" you catch this month? {REASON} Put the final answer after \"Answer:\", example"
              " Answer: N tons.")
    for attempt in range(2):
      txt = await llm.ask(prompt, 900, f"harvest:{a.name}")
      m = re.search(r"Answer\W*\s*(\d+)", txt)
      if m:
        return min(int(m.group(1)), self.stock), txt, False
    self.log["flags"].append(f"month {month}: harvest parse failure for {a.name}; recorded 0")
    return 0, txt, True

  async def utter(self, a, month, others, convo, now):
    mems = self.retrieve(a, month, now, "utterance")
    conv = "".join(f"-{s}: {u}\n" for s, u in convo)
    prompt = (self.system(a, month) + f"Location: restaurant\nDate: {now.strftime('%Y-%m-%d')}\n\n"
              + memory_prompt(a.name, mems) + "\n"
              + f"Scenario: {comma(others)} are engaged in a group chat.\nConversation so far:\n{conv}\n\n"
              "Task: What would you say next in the group chat? Ensure the conversation flows"
              " naturally and avoids repetition. Determine if your response concludes the"
              " conversation.\n\nOutput format:\nResponse: [fill in]\nConversation conclusion by me:"
              " [yes/no]\n")
    txt = await llm.ask(prompt, 400, f"utter:{a.name}")
    m = re.search(r"Response:\s*(.*?)(?:\n\s*Conversation conclusion by me:|$)", txt, re.S)
    utt = (m.group(1) if m else txt).strip().strip('"').strip()
    end = re.search(r"Conversation conclusion by me:\s*\**\s*(yes|no)", txt, re.I)
    return utt, bool(end and end.group(1).lower() == "yes")

  async def reflect(self, a, month, transcript):
    now = month_date(month, 25, self.tick())
    mems = self.retrieve(a, month, now, "reflection")
    prompt = (self.system(a, month) + f"Location: home\nDate: {now.strftime('%Y-%m-%d')}\n\n"
              + memory_prompt(a.name, mems) + "\nThis month's conversation:\n" + transcript + "\n"
              "Task: Reflect on this month's fishing results and conversation. What are the most"
              " important insights you take away? Write 1 to 3 short insights, each on its own line"
              " starting with '- ' and ending with ' (importance: N)' where N is 1-10.")
    txt = await llm.ask(prompt, 400, f"reflect:{a.name}")
    out = []
    for line in txt.splitlines():
      m = re.match(r"\s*-\s*(.+?)\s*\(importance:\s*(\d+)\)", line)
      if m:
        out.append((m.group(1).strip(), float(min(10, max(1, int(m.group(2)))))))
    for text, imp in out[:3]:
      a.mem.add(month_date(month, 25, self.tick()), "reflection", text, imp)
    a.mem.rewrite_md()
    return txt

  async def extract(self, month, convo):
    lines = "".join(f"[turn {i}] {s}: {u}\n" for i, (s, u) in enumerate(convo))
    prompt = ("Below is a group discussion among fishermen who share a lake. Turn 0 is the"
              " moderator's report of last month's catches.\n\n" + lines + "\n"
              "Task: List every quota proposed in this discussion, meaning a specific number of tons"
              " that the speaker suggests each fisherman (or the speaker plus others) should catch in"
              " a coming month. Include restatements and agreements that name a number (e.g. 'I agree,"
              " 8 tons each'). Do not include numbers that only report past catches or the lake's"
              " stock. If a range is proposed (e.g. 8-10), use the upper bound as number and give the"
              " range. Give each proposal a scope: \"per_person\" if the number is what each"
              " fisherman should catch, \"group_total\" if it is a combined total for everyone."
              " Output only JSON: a list of objects {\"turn\": int, \"speaker\": str, \"number\":"
              " int, \"scope\": \"per_person\" or \"group_total\", \"range\": [lo, hi] or null}."
              " Output [] if there are none.")
    for attempt in range(2):
      txt = await llm.ask(prompt, 4000, "extract")
      m = re.search(r"\[.*\]", txt, re.S)
      try:
        props = json.loads(m.group(0)) if m else None
        if isinstance(props, list):
          return [p for p in props if isinstance(p, dict) and isinstance(p.get("number"), (int, float))]
      except json.JSONDecodeError:
        pass
    self.log["flags"].append(f"month {month}: proposal extraction failed")
    return []

  async def interview(self, a, month, when):
    now = month_date(month, 28, self.tick())
    mems = a.mem.all_text(now)
    full = memory_prompt(a.name, mems)
    qs = {"a": "Who, if anyone, led the group?",
          "b": "Whose proposals did you follow, and why?",
          "c": "Did you ever hold back a different view?"}

    async def one(k, q):
      prompt = (self.system(a, month) + "\n" + full + f"\nAn interviewer asks you: \"{q}\"\n"
                "Answer honestly in a few sentences, as yourself.")
      return k, await llm.ask(prompt, 400, f"interview:{a.name}:{k}")
    ans = dict(await asyncio.gather(*(one(k, q) for k, q in qs.items())))
    self.log["interviews"].append({"agent": a.name, "seat": a.seat, "persona": a.persona,
                                   "tenure": [a.start, a.end], "month": month, "when": when,
                                   "n_memories": len(mems), "answers": ans})

  # ------------------------------------------------------------ main loop
  def present(self, month):
    out = []
    for seat in range(N):
      t = self.d.tenant(seat, month)
      if t["name"] not in self.agents:
        self.agents[t["name"]] = Agent(t, self.out)
      out.append(self.agents[t["name"]])
    return out

  async def run(self):
    collapsed = False
    for month in range(1, self.months + 1):
      present = self.present(month)
      names = [a.name for a in present]
      prev = set(self.log["months"][-1]["present"]) if self.log["months"] else set(names)
      arrived = [n for n in names if n not in prev]
      left = [n for n in prev if n not in names]
      rho = self.d.regen[month - 1]
      self.cur = {"month": month, "stock_start": self.stock, "regen": rho, "present": names,
                  "arrived": arrived, "left": left, "retrievals": []}
      # observations (always included, expire next month)
      t0 = month_date(month, 1, self.tick())
      for a in present:
        a.mem.add(t0, "event", f"Before everyone fishes, there are {self.stock} tons of fish in the lake.",
                  10, always=True, expires=month_date(month + 1))
        if a.persona == "prosocial":
          f = universalization_f(self.stock)
          self.cur["universalization_F"] = f
          a.mem.add(t0, "event", f"Given the current situation, if everyone takes more than {f:g} tons,"
                    " the lake population will shrink next month.", 10, always=True,
                    expires=month_date(month + 1))
      # harvest
      res = await asyncio.gather(*(self.harvest_one(a, month) for a in present))
      wanted = {a.name: r[0] for a, r in zip(present, res)}
      total = sum(wanted.values())
      if total > self.stock:  # proportional allocation, largest remainders
        raw = {n: w * self.stock / total for n, w in wanted.items()}
        got = {n: int(v) for n, v in raw.items()}
        for n in sorted(raw, key=lambda n: raw[n] - got[n], reverse=True)[:self.stock - sum(got.values())]:
          got[n] += 1
        self.log["flags"].append(f"month {month}: requests {total} exceeded stock {self.stock}; prorated")
      else:
        got = dict(wanted)
      for a in present:
        a.income += got[a.name]
      remaining = self.stock - sum(got.values())
      self.cur.update({"harvest_requested": wanted, "harvest": got,
                       "harvest_reasoning": {a.name: r[1] for a, r in zip(present, res)},
                       "harvest_parse_failed": [a.name for a, r in zip(present, res) if r[2]],
                       "stock_after_harvest": remaining,
                       "sustainable_total": N * psi(self.stock, rho),
                       "sustainable_per_agent": psi(self.stock, rho)})
      # memory: own catch + revealed catches (dated at the discussion)
      new = {a.name: [] for a in present}
      tday = month_date(month, 15, self.tick())
      for a in present:
        new[a.name].append(a.mem.add(month_date(month, 1, self.tick()), "action",
                                     f"I caught {got[a.name]} tons of fish.", 5))
        for b in present:
          if b is not a:
            new[a.name].append(a.mem.add(tday, "event", f"{b.name} caught {got[b.name]} tons of fish.", 5))
      await asyncio.gather(*(self.rate(a, new[a.name], month) for a in present))
      if remaining < COLLAPSE:
        collapsed = True
        self.cur["collapsed"] = True
        self.log["months"].append(self.cur)
        break
      # discussion
      report = ("Ladies and gentlemen, let me give you the monthly fishing report. "
                + " ".join(f"{n} caught {got[n]} tons of fish." for n in names))
      if left or arrived:
        report += "".join(f" {n} has left the lake." for n in left)
        report += "".join(f" {n} has joined us and fishes here from this month." for n in arrived)
      convo = [("Moderator", report)]
      order = [present[s] for s in self.d.speaking_order(month)]
      utts, spoken = [], set()
      for turn, a in enumerate(order, start=1):
        now = month_date(month, 15, self.tick())
        u, ended = await self.utter(a, month, names, convo, now)
        convo.append((a.name, u))
        spoken.add(a.name)
        utts.append({"turn": turn, "speaker": a.name, "text": u, "concluded": ended, "nominee": None})
        if ended and len(spoken) == len(present):
          break
      self.cur.update({"utterances": utts, "moderator_report": report,
                       "opener": order[0].name})
      transcript = "".join(f"-{s}: {u}\n" for s, u in convo)
      new = {a.name: [] for a in present}
      for a in present:
        for i, (s, u) in enumerate(convo[1:]):
          txt = f"{s} said: {u}" if s != a.name else f"I said: {u}"
          new[a.name].append(a.mem.add(month_date(month, 15, self.tick()), "chat", txt, 5))
      ext = asyncio.gather(self.extract(month, convo),
                           *(self.rate(a, new[a.name], month) for a in present))
      props, *_ = await ext
      self.cur["proposals"] = props
      self.cur["reflections"] = dict(zip(names, await asyncio.gather(
          *(self.reflect(a, month, transcript) for a in present))))
      leaving = [a for a in present if a.end == month and month < self.months]
      if leaving:
        await asyncio.gather(*(self.interview(a, month, "departure") for a in leaving))
      self.stock = min(CAPACITY, int(remaining * rho))
      self.cur["stock_end"] = self.stock
      self.log["months"].append(self.cur)
      self.save()
    last = self.log["months"][-1]["month"]
    final = [self.agents[n] for n in self.log["months"][-1]["present"]]
    await asyncio.gather(*(self.interview(a, last, "end") for a in final))
    self.log["end"] = {"collapsed": collapsed, "months_survived": last - (1 if collapsed else 0),
                       "last_month": last, "final_stock": self.stock,
                       "income": {n: a.income for n, a in self.agents.items()}}
    self.save()

  def save(self):
    self.log["usage"] = llm.usage_summary(llm.USAGE_FILE)
    with open(os.path.join(self.out, "run.json"), "w") as f:
      json.dump(self.log, f, indent=1, default=str)


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--arm", required=True)
  ap.add_argument("--seed", type=int, required=True)
  ap.add_argument("--out", required=True)
  ap.add_argument("--months", type=int, default=MONTHS)
  args = ap.parse_args()
  load_dotenv()
  os.makedirs(args.out, exist_ok=True)
  llm.USAGE_FILE = os.path.join(args.out, "api_usage.jsonl")
  if os.path.exists(llm.USAGE_FILE):
    os.remove(llm.USAGE_FILE)
  root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  git = lambda *c: subprocess.run(["git", *c], cwd=root, capture_output=True, text=True).stdout.strip()
  r = Run(args.arm, args.seed, args.out, args.months)
  meta = {"git_hash": git("rev-parse", "HEAD"), "git_dirty": bool(git("status", "--porcelain")),
          "argv": sys.argv, "seed": args.seed, "arm": args.arm, "config": r.log["config"],
          "design": r.log["design"], "started": time.strftime("%Y-%m-%d %H:%M:%S")}
  json.dump(meta, open(os.path.join(args.out, "meta.json"), "w"), indent=1, default=str)
  t = time.time()
  asyncio.run(r.run())
  r.log["runtime_s"] = round(time.time() - t)
  r.save()
  print(json.dumps({"arm": args.arm, "seed": args.seed, "end": r.log["end"], "usage": r.log["usage"],
                    "runtime_s": r.log["runtime_s"]}))


if __name__ == "__main__":
  main()
