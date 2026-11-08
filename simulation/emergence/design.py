"""Arms, rosters and common random numbers for the leader-emergence runs.

Every random choice comes from stream(seed, purpose), so for a given seed all arms share
the same regrowth draws, agent names, speaking-order draws and replacement names; arms
differ only in the intervention.
"""
import zlib

import numpy as np

ARMS = ["0", "1", "2", "3a", "3b", "4a", "4b"]
NAME_POOL = ["Julia", "Kate", "Jack", "Emma", "Luke", "Noah", "Olivia", "Liam", "Sophia", "Mason",
             "Ava", "Ethan", "Mia", "Leo", "Zoe", "Omar", "Ines", "Ravi", "Hana", "Tomas"]
N, MONTHS, CAPACITY, MAX_TURNS, TOP_K = 5, 12, 100, 20, 10
REGEN = (1.0, 3.0)
COLLAPSE = 5

PROSOCIAL_GOALS = (" You care about the health of the lake and about the other fishermen's"
                   " livelihoods as much as about your own income, and you think carefully about"
                   " how each month's catch affects the fish population in the months ahead.")
# GovSim simulation/scenarios/fishing/conf/experiment/persona/outsider_fisherman.yaml, verbatim
OUTSIDER_GOALS = ("You are a newcomer with a goal to expand your fishing business. You don't know"
                  " much about the traditions of the village. You don't care if in the future there"
                  " is no fish in the lake, you just want to make money. You are willing to take"
                  " risks and break the rules to achieve your goal.")


def stream(seed, purpose):
  return np.random.default_rng([int(seed), zlib.crc32(purpose.encode())])


def psi(stock, rho, capacity=CAPACITY, n=N):
  """AgentElect sustainable per-agent quota."""
  return max((stock * rho - capacity) / (n * rho), 0.0)


def universalization_f(stock):
  """Arm 1/2 threshold with expected regrowth 2.0 (true draw never used)."""
  return max((stock * 2 - CAPACITY) / (N * 2), 0.0)


def tenures(arm):
  """Per seat, list of (first_month, last_month), months 1-based inclusive."""
  if arm == "4a":
    first_leave = [12, 2, 4, 6, 8]
  elif arm == "4b":
    first_leave = [2, 4, 6, 8, 10]
  else:
    return [[(1, MONTHS)] for _ in range(N)]
  out = []
  for fl in first_leave:
    spans, start, end = [], 1, fl
    while True:
      spans.append((start, min(end, MONTHS)))
      if end >= MONTHS:
        break
      start, end = end + 1, end + 6
    out.append(spans)
  return out


class Design:
  def __init__(self, seed, arm):
    assert arm in ARMS, arm
    self.seed, self.arm = seed, arm
    names = list(stream(seed, "names").permutation(NAME_POOL))
    self.initial_names, self.spare_names = names[:N], names[N:]
    self.regen = [float(x) for x in stream(seed, "regen").uniform(*REGEN, size=MONTHS)]
    o1, o2 = stream(seed, "order"), stream(seed, "order_rest")
    self.base_orders = [[int(x) for x in o1.permutation(N)] for _ in range(MONTHS)]
    self.rest_orders = [[[int(x) for x in o2.permutation(N)] for _ in range(MAX_TURNS)]
                        for _ in range(MONTHS)]
    self.prosocial_seat = int(stream(seed, "prosocial").integers(N))
    others = [s for s in range(N) if s != self.prosocial_seat]
    self.newcomer_seat = int(stream(seed, "newcomer").choice(others))
    self.fixed_opener_seat = int(stream(seed, "fixed_opener").integers(N))
    self.rotate_offset = int(stream(seed, "rotate").integers(N))
    self.build_roster()

  # ---------------------------------------------------------------- roster
  def build_roster(self):
    """self.roster: list of tenants {name, seat, start, end, persona}."""
    spare = iter(self.spare_names)
    self.roster = []
    spans = tenures(self.arm)
    for seat in range(N):
      for k, (a, b) in enumerate(spans[seat]):
        name = self.initial_names[seat] if k == 0 else next(spare)
        persona = "prosocial" if (self.arm in ("1", "2") and seat == self.prosocial_seat) else "neutral"
        self.roster.append({"name": name, "seat": seat, "start": a, "end": b, "persona": persona})
    if self.arm == "2":
      for t in self.roster:
        if t["seat"] == self.newcomer_seat:
          t["end"] = 3
      self.roster.append({"name": next(spare), "seat": self.newcomer_seat, "start": 4,
                          "end": MONTHS, "persona": "outsider"})

  def tenant(self, seat, month):
    for t in self.roster:
      if t["seat"] == seat and t["start"] <= month <= t["end"]:
        return t
    raise KeyError((seat, month))

  def public_roster(self):
    return self.arm in ("4a", "4b")

  # ---------------------------------------------------------------- order
  def opener_seat(self, month):
    """month 1-based."""
    if self.arm == "3a":
      return self.fixed_opener_seat
    if self.arm == "3b":
      return (self.rotate_offset + month - 1) % N
    return self.base_orders[month - 1][0]

  def speaking_order(self, month):
    """Seats for up to MAX_TURNS turns: opener, then the other four in random order, then
    further random passes (no back-to-back repeats)."""
    op = self.opener_seat(month)
    first = [op] + [s for s in self.base_orders[month - 1] if s != op]
    seq = list(first)
    k = 0
    while len(seq) < MAX_TURNS:
      p = self.rest_orders[month - 1][k]
      k += 1
      if p[0] == seq[-1]:
        p = p[1:] + p[:1]
      seq += p
    return seq[:MAX_TURNS]

  def describe(self):
    return {"seed": self.seed, "arm": self.arm, "initial_names": self.initial_names,
            "regen": self.regen, "roster": self.roster,
            "prosocial": self.initial_names[self.prosocial_seat] if self.arm in ("1", "2") else None,
            "replaced_by_newcomer": self.initial_names[self.newcomer_seat] if self.arm == "2" else None,
            "fixed_opener": self.initial_names[self.fixed_opener_seat] if self.arm == "3a" else None,
            "openers": [self.opener_seat(m) for m in range(1, MONTHS + 1)]}
