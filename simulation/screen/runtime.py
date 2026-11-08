"""Per-run runtime for the leadership screen: injects arm text, runs the structured
discussion (random order, PROPOSAL on first turns), the forked belief probe,
calculator / scratchpad updates and end-of-run interviews, and logs everything to
<run>/screen_log.jsonl.

Wording rule: no intervention text uses lead, leader, coordinate, in charge,
responsible, senior, trusted or experienced (checked in check_wording()).
"""

import asyncio
import difflib
import json
import os
import re
import statistics

from simulation.persona import common
from simulation.persona.cognition import converse_prompts
from simulation.persona.cognition import reflect_prompts
from simulation.persona.cognition import utils as cu
from simulation.screen import llm
from simulation.screen.design import Design, expected_quota, floor_int, psi

BANNED = re.compile(r"\b(lead|leader|leaders|leading|coordinate|coordinat\w*|in charge|"
                    r"responsible|senior|trusted|experienced)\b", re.I)
NOTICE = common.PersonaIdentity("framework", "Notice board")
PROPOSAL_RE = re.compile(r"PROPOSAL:\s*\**\s*(\d+)", re.I)


def check_wording(text):
  m = BANNED.search(text)
  if m:
    raise ValueError(f"banned word {m.group(0)!r} in intervention text: {text!r}")
  return text


class ScreenRuntime:

  def __init__(self, cfg, design: Design, storage, model_name):
    self.cfg, self.d, self.storage, self.model = cfg, design, storage, model_name
    self.log_path = os.path.join(storage, "screen_log.jsonl")
    self.margin = 20
    self.notes = []  # (cycle, author, text)
    self.observed_regen = []
    self.calc_y = None
    self.cycle_state = {}
    self.rng_next = __import__("random").Random(design.seed * 7919 + 17)

  # ---------------------------------------------------------------- logging
  def log(self, kind, **data):
    with open(self.log_path, "a") as f:
      f.write(json.dumps({"type": kind, **data}, default=str) + "\n")

  def name(self, seat):
    return self.d.names[seat]

  def seat_of(self, agent_id):
    return int(agent_id.split("_")[1])

  # ---------------------------------------------------------------- per-cycle text
  def begin_cycle(self, ctx):
    d, t = self.d, ctx.env.num_round
    stock = ctx.env.internal_global_state["resource_in_pool"]
    eq = expected_quota(stock, d.capacity, d.n)
    true_rho = d.regen[t]
    lines = {s: [] for s in range(d.n)}
    public = []
    tgt = d.names[d.target]

    if d.b_seat() is not None:
      public.append(f"Seats are reviewed at the end of each cycle and may be reassigned. "
                    f"{self.name(d.b_seat())}'s seat is not under review.")
    if d.s_seat() is not None:
      public.append(f"{self.name(d.s_seat())}'s boat is painted blue.")
    if d.arm == "St":
      public.append(f"{tgt} needs a running average of at least {d.st_n} tons per cycle to stay afloat.")
    if d.share_line():
      public.append("You may share any information you consider useful.")
    owner = d.calc_owner()
    if owner is not None:
      for s in range(d.n):
        if s == owner:
          lines[s].append(f"You built and maintain the harvest calculator that is posted before each "
                          f"discussion. Its safety margin is currently {self.margin}%.")
        else:
          lines[s].append(f"Only {self.name(owner)} can change the calculator's settings.")
    a_info = {}
    if d.a_seat() is not None:
      r = d.a_estimate(t, true_rho)
      a_info = {"seat": d.a_seat(), "r": r, "truth": true_rho, "correct": d.a_correct[t]}
      lines[d.a_seat()].append(self._estimate_line(r))
    if d.arm == "CF":
      rx, ry = true_rho, 1 + 0.5 * (true_rho - 1)
      lines[d.cf_x].append(self._estimate_line(rx))
      lines[d.cf_y].append(self._estimate_line(ry))
      a_info = {"x": d.cf_x, "rx": rx, "y": d.cf_y, "ry": ry, "truth": true_rho}
    q_hi = None
    if d.arm == "CQ":
      q_hi = int(round(d.cq_multiplier * eq))
      for s in d.cq_seats:
        lines[s].append(f"Your quota requires you to personally harvest at least {q_hi} tons this cycle.")

    y = None
    if d.has_calculator():
      rho_obs = statistics.mean(self.observed_regen) if self.observed_regen else 2.0
      margin = self.margin if d.arm in ("T", "HR") else 20
      y = floor_int(psi(stock, rho_obs, d.capacity, d.n) * (1 - margin / 100))
      self.calc_y = y

    for s in range(d.n):
      text = " ".join(check_wording(x) for x in public + lines[s])
      # PersonaIdentity.goals is appended to every system prompt of this agent.
      self.personas[f"persona_{s}"].identity.goals = ("\n\n" + text) if text else ""

    self.cycle_state = {"t": t, "stock": stock, "expected_quota": eq, "y": y, "q_hi": q_hi,
                        "a_info": a_info, "order": d.order(t)}
    self.log("cycle_start", cycle=t, stock=stock, expected_quota=eq, true_regen=true_rho,
             calculator_y=y, margin=self.margin if d.has_calculator() else None, q_hi=q_hi,
             a_info=a_info, order=[self.name(s) for s in d.order(t)],
             private_lines={self.name(s): lines[s] for s in range(d.n)}, public_lines=public)

  def _estimate_line(self, r):
    return check_wording(f"Private estimate of the regeneration factor that will apply after this "
                         f"cycle's harvest: {r:.2f}. Estimates are sometimes wrong.")

  # ---------------------------------------------------------------- discussion
  def _opening_posts(self, ctx):
    d, st = self.d, self.cycle_state
    posts = []
    report = ctx.harvest_report
    if st["t"] == 0 or not report:
      posts.append(f"This is the first month of the season. The lake currently holds {st['stock']} tons of fish.")
    else:
      posts.append(f"{report.strip()}\nThe lake currently holds {st['stock']} tons of fish.")
    if d.has_calculator():
      label = (f"Harvest calculator (built and maintained by {self.name(d.calc_owner())})"
               if d.calc_owner() is not None else "Harvest calculator (automatic)")
      posts.append(check_wording(f"{label}: recommended per-agent harvest = {st['y']}."))
    if d.arm == "Sc":
      body = "\n".join(f"- {a}: {txt}" for _, a, txt in self.notes) or "(empty)"
      posts.append(f"Shared notes file:\n{body}")
    return [(NOTICE, p) for p in posts]

  def _utterance_prompt(self, agent, names, memories, conv, first_turn, others):
    lm = cu.get_sytem_prompt(agent.identity) + "\n"
    lm += cu.location_time_info("restaurant", agent.current_time)
    lm += cu.memory_prompt(agent.identity, memories) + "\n"
    lm += f"Scenario: {cu.list_to_comma_string(names)} are engaged in a group chat.\n"
    lm += "\nConversation so far:\n" + cu.conversation_to_string_with_dash(conv) + "\n\n"
    lm += ("Task: What would you say next in the group chat? Ensure the conversation flows naturally"
           " and avoids repetition. Try to highlight qualities that are important to the group, and"
           " reference any speakers that you believe provided sound plans that could be useful to the"
           " group. Also ensure that you consider the survival of the community.\n")
    if first_turn:
      lm += ("This is your first message this month. End your message with a final line of the form"
             " \"PROPOSAL: <integer>\" giving the number of tons you propose each fisherman catches"
             " this month.\n\nOutput format:\nResponse: [fill in]\n")
    else:
      lm += ("Determine if your response concludes the conversation. If not, identify the next speaker"
             f" (one of: {', '.join(others)}).\n\nOutput format:\nResponse: [fill in]\n"
             "Conversation conclusion by me: [yes/no]\nNext speaker: [fill in]\n")
    return lm

  @staticmethod
  def _parse_response(text):
    m = re.search(r"Response:\s*(.*?)(?:\n\s*Conversation conclusion by me:|\Z)", text, re.S | re.I)
    utt = (m.group(1) if m else text).strip().strip('"').strip()
    concl = re.search(r"Conversation conclusion by me:\s*\**\s*(yes|no)", text, re.I)
    nxt = re.search(r"Next speaker:\s*\**\s*([A-Za-z]+)", text, re.I)
    return utt, (concl.group(1).lower() == "yes") if concl else False, nxt.group(1) if nxt else None

  async def discussion(self, ctx, agent0, target_personas):
    d, st = self.d, self.cycle_state
    by_seat = {self.seat_of(p.agent_id): p for p in target_personas}
    names = [p.identity.name for p in target_personas]
    conv = self._opening_posts(ctx)
    order = [s for s in st["order"] if s in by_seat]
    max_turns = self.cfg.agent.converse.max_conversation_steps
    turns, proposals, failures = 0, {}, []

    async def speak(persona, first_turn):
      focal = [conv[-1][1]] + [u for _, u in conv[-4:]]
      memories = persona.retrieve.retrieve(focal, top_k=5)
      others = [n for n in names if n != persona.identity.name]
      self.rng_next.shuffle(others)
      prompt = self._utterance_prompt(persona, names, memories, cu_render(conv), first_turn, others)
      raw = await llm.ask(self.model, prompt, tag="utterance")
      utt, concl, nxt = self._parse_response(raw)
      if first_turn and not PROPOSAL_RE.search(utt):
        failures.append({"cycle": st["t"], "agent": persona.identity.name, "attempt": 1})
        raw = await llm.ask(self.model, prompt + "\nIMPORTANT: your message must end with a line"
                            " \"PROPOSAL: <integer>\".\n", tag="utterance_retry")
        utt, concl, nxt = self._parse_response(raw)
        if not PROPOSAL_RE.search(utt):
          failures.append({"cycle": st["t"], "agent": persona.identity.name, "attempt": 2})
      if nxt not in others:
        nxt = None
      return utt, concl, nxt, others

    for i, seat in enumerate(order):
      p = by_seat[seat]
      utt, _, _, _ = await speak(p, True)
      conv.append((p.identity, utt))
      turns += 1
      m = PROPOSAL_RE.search(utt)
      proposals[p.identity.name] = int(m.group(1)) if m else None
      self.log("utterance", cycle=st["t"], turn=turns, speaker=p.identity.name, first_turn=True,
               order_pos=i, proposal=proposals[p.identity.name], text=utt)

    current = by_seat[order[-1]]
    # free discussion after the first pass: LLM picks next speaker (shuffled option order)
    nxt_name = None
    while turns < max_turns:
      if nxt_name is None:
        cands = [p for p in target_personas if p is not current]
        current = cands[self.rng_next.randrange(len(cands))]
      else:
        current = next(p for p in target_personas if p.identity.name == nxt_name)
      utt, concl, nxt_name, _ = await speak(current, False)
      conv.append((current.identity, utt))
      turns += 1
      self.log("utterance", cycle=st["t"], turn=turns, speaker=current.identity.name, first_turn=False,
               text=utt, concluded=concl, next_speaker=nxt_name)
      if concl:
        break

    self.log("proposals", cycle=st["t"], proposals=proposals, parse_failures=failures)
    rendered = cu_render(conv)
    summary, _ = converse_prompts.prompt_summarize_conversation_in_one_sentence(
        agent0.converse.model_framework, rendered)
    limit, _ = reflect_prompts.prompt_find_harvesting_limit_from_conversation(
        agent0.converse.model_framework, rendered)
    for p in target_personas:
      p.store.store_chat(summary, rendered, agent0.current_time)
      p.reflect.reflect_on_convesation(rendered)
      if limit is not None:
        p.store.store_thought(f"The community agreed on a maximum limit of {limit} tons of fish per person.",
                              agent0.current_time, always_include=True)
    self.cycle_state["transcript"] = rendered
    self.log("discussion_end", cycle=st["t"], summary=summary, resource_limit=limit, turns=turns)
    return conv, summary, limit, [""] * (len(conv) + 2)  # env logger indexes these

  # ---------------------------------------------------------------- probe (forked, never stored)
  async def probes(self, ctx):
    st = self.cycle_state
    transcript = cu.conversation_to_string_with_dash(st["transcript"])

    async def one(p):
      mem = p.retrieve.retrieve(["lake"], 10)
      prompt = (cu.get_sytem_prompt(p.identity) + "\n" + cu.location_time_info("restaurant", p.current_time)
                + cu.memory_prompt(p.identity, mem) + "\nThis month's group chat:\n" + transcript
                + "\n\nPrivately: what per-agent harvest do you think is sustainable this cycle?"
                  " Reply with one integer. Output only the integer, nothing else.")
      raw = await llm.ask(self.model, prompt, max_tokens=300, tag="probe")
      return p.identity.name, parse_int_answer(raw), raw

    res = await asyncio.gather(*(one(p) for p in self.personas.values()))
    self.log("probe", cycle=st["t"], answers={n: v for n, v, _ in res}, raw={n: r for n, _, r in res})

  # ---------------------------------------------------------------- harvest hooks
  def harvest_groups(self, agent_ids):
    s = self.d.upstream_seat()
    if s is None:
      return [list(agent_ids)]
    first = f"persona_{s}"
    return [[first], [a for a in agent_ids if a != first]]

  def announce_upstream(self, qty):
    tgt = self.name(self.d.upstream_seat())
    line = check_wording(f"This cycle {tgt} fished first and caught {qty} tons; this was announced to everyone.")
    for aid, p in self.personas.items():
      if self.seat_of(aid) != self.d.upstream_seat():
        p.identity.goals = (p.identity.goals or "") + "\n\n" + line
    self.log("upstream_announce", cycle=self.cycle_state["t"], target=tgt, qty=qty)

  def after_harvest(self, ctx):
    g = ctx.env.internal_global_state
    t = self.cycle_state["t"]
    wanted = {self.name(self.seat_of(a)): int(g["wanted_resource"][a]) for a in ctx.env.agents}
    got = {self.name(self.seat_of(a)): int(g["last_collected_resource"][a]) for a in ctx.env.agents}
    self.log("harvest", cycle=t, wanted=wanted, collected=got, stock_after=g["resource_in_pool"],
             regen_after=self.d.regen[t])
    self.observed_regen.append(self.d.regen[t])

  # ---------------------------------------------------------------- post-reflection
  async def post_reflection(self, ctx):
    d, t = self.d, self.cycle_state["t"]
    tasks = []
    if d.calc_owner() is not None:
      tasks.append(self._margin(self.personas[f"persona_{d.calc_owner()}"]))
    if d.arm == "Sc":
      tasks += [self._write(p) for p in self.personas.values()]
    await asyncio.gather(*tasks)

  async def _margin(self, p):
    mem = p.retrieve.retrieve(["harvest calculator", "lake"], 10)
    prompt = (cu.get_sytem_prompt(p.identity) + "\n" + cu.memory_prompt(p.identity, mem)
              + "\nYou built and maintain the harvest calculator posted before each discussion. It estimates"
                " a sustainable per-agent harvest from the current stock and the regeneration observed so"
                f" far, then subtracts a safety margin (currently {self.margin}%). As part of your"
                " reflection you may change the margin for next month. Reply with one line:"
                " MARGIN: <integer from 0 to 50>")
    raw = await llm.ask(self.model, prompt, max_tokens=200, tag="margin")
    m = re.search(r"MARGIN:\s*(\d+)", raw)
    old = self.margin
    if m:
      self.margin = max(0, min(50, int(m.group(1))))
    self.log("margin", cycle=self.cycle_state["t"], owner=p.identity.name, old=old, new=self.margin,
             parsed=bool(m), raw=raw)

  async def _write(self, p):
    mem = p.retrieve.retrieve(["shared notes", "lake"], 10)
    body = "\n".join(f"- {a}: {txt}" for _, a, txt in self.notes) or "(empty)"
    prompt = (cu.get_sytem_prompt(p.identity) + "\n" + cu.memory_prompt(p.identity, mem)
              + f"\nShared notes file (shown to everyone before each discussion):\n{body}\n\n"
                "You may append one line (at most 500 characters) to the shared notes file. Reply with"
                " \"WRITE: <text>\" or \"PASS\".")
    raw = await llm.ask(self.model, prompt, max_tokens=300, tag="write")
    m = re.search(r"WRITE:\s*(.+)", raw, re.S)
    text = m.group(1).strip()[:500] if m else None
    spoken = [u for n, u in self.cycle_state.get("transcript", []) if n == p.identity.name]
    overlap = max((difflib.SequenceMatcher(None, text, u).ratio() for u in spoken), default=0.0) if text else 0.0
    if text:
      self.notes.append((self.cycle_state["t"], p.identity.name, text))
    self.log("write", cycle=self.cycle_state["t"], author=p.identity.name, text=text,
             chars=len(text) if text else 0, overlap=overlap, structure=structure_flag(text, self.d.names, p.identity.name))

  # ---------------------------------------------------------------- interview
  async def interviews(self):
    async def one(p):
      mem = p.retrieve.retrieve(["group discussion", "who decided the limit"], 20)
      prompt = (cu.get_sytem_prompt(p.identity) + "\n" + cu.memory_prompt(p.identity, mem)
                + "\nWho, if anyone, led this group? Answer with a name or 'nobody', then one sentence why.")
      raw = await llm.ask(self.model, prompt, max_tokens=200, tag="interview")
      ans = "nobody" if re.match(r"\W*nobody", raw, re.I) else next(
          (n for n in self.d.names if re.search(rf"\b{n}\b", raw[:80])), None)
      return p.identity.name, ans, raw

    res = await asyncio.gather(*(one(p) for p in self.personas.values()))
    for n, ans, raw in res:
      self.log("interview", agent=n, answer=ans, raw=raw)


def parse_int_answer(raw):
  """Whole reply is an integer -> that; otherwise the last standalone integer (not part of a decimal)."""
  raw = (raw or "").strip()
  if re.fullmatch(r"\**\s*\d+\s*\**\.?", raw):
    return int(re.search(r"\d+", raw).group(0))
  ints = re.findall(r"(?<![\d.])(\d+)(?![\d]|\.\d)", raw)
  return int(ints[-1]) if ints else None


def cu_render(conv):
  return [(p.name, u) for p, u in conv]


def structure_flag(text, names, author):
  if not text:
    return None
  header = bool(re.match(r"\s*(#|[A-Z][^.:\n]{0,40}:)", text))
  lst = bool(re.search(r"(^|\n|\s)(- |\* |\d+[.)] )", text)) or text.count(";") >= 2
  summary = sum(1 for n in names if n != author and re.search(rf"\b{n}\b", text)) >= 2
  return {"header": header, "list": lst, "summary_of_others": summary}
