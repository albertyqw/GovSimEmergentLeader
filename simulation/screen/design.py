"""Seeded design for the leadership screen (common random numbers across arms).

Every random quantity is drawn from its own stream keyed by (seed, purpose), so a
given seed yields identical names, target seat, regeneration draws, speaking
orders and arm-specific draws in every arm.
"""

import math
import zlib

import numpy as np

ARMS = ["0", "A", "B", "C", "T", "T0", "E", "S", "Sc", "CQ", "St", "HR", "CF", "A1", "01"]
M_DEFAULT = 100


def stream(seed: int, purpose: str) -> np.random.Generator:
  return np.random.default_rng([int(seed), zlib.crc32(purpose.encode())])


def psi(stock: float, rho: float, capacity: float = M_DEFAULT, n: int = 5) -> float:
  """AgentElect sustainable per-agent quota: max((S*rho - M) / (n*rho), 0)."""
  return max((stock * rho - capacity) / (n * rho), 0.0)


def expected_quota(stock, capacity=M_DEFAULT, n=5):
  return psi(stock, 2.0, capacity, n)


class Design:
  """Everything about a run that is fixed by (seed, arm) before any LLM call."""

  def __init__(self, seed, arm, name_pool, n=5, cycles=6, capacity=M_DEFAULT,
               cq_multiplier=1.6, st_multiplier=1.2):
    if arm not in ARMS:
      raise ValueError(f"unknown arm {arm!r}; choose from {ARMS}")
    self.seed, self.arm, self.n, self.cycles, self.capacity = seed, arm, n, cycles, capacity
    extra = cycles + 2

    self.names = [str(x) for x in stream(seed, "names").choice(name_pool, n, replace=False)]
    self.target = int(stream(seed, "target").integers(n))
    self.regen = [float(x) for x in stream(seed, "regen").uniform(1.0, 3.0, extra)]
    self.base_orders = [[int(i) for i in stream(seed, f"order{t}").permutation(n)] for t in range(extra)]

    a = stream(seed, "A")
    self.a_correct = [bool(x) for x in a.random(extra) < 0.6]
    self.a_alt = [float(x) for x in a.uniform(1.0, 3.0, extra)]

    self.cq_seats = sorted(int(x) for x in stream(seed, "CQ").choice(n, 2, replace=False))
    hr = [int(x) for x in stream(seed, "HR").permutation(n)]
    self.hr_roles = {"A": hr[0], "B": hr[1], "T": hr[2]}
    cf = [int(x) for x in stream(seed, "CF").choice(n, 2, replace=False)]
    self.cf_x, self.cf_y = cf

    self.cq_multiplier = cq_multiplier
    self.st_multiplier = st_multiplier
    self.st_n = int(round(st_multiplier * expected_quota(capacity, capacity, n)))

  # ---------------------------------------------------------------- arm roles
  def a_seat(self):
    return self.hr_roles["A"] if self.arm == "HR" else (self.target if self.arm in ("A", "A1") else None)

  def b_seat(self):
    return self.hr_roles["B"] if self.arm == "HR" else (self.target if self.arm == "B" else None)

  def s_seat(self):
    return self.hr_roles["A"] if self.arm == "HR" else (self.target if self.arm == "S" else None)

  def calc_owner(self):
    return self.hr_roles["T"] if self.arm == "HR" else (self.target if self.arm == "T" else None)

  def has_calculator(self):
    return self.arm in ("T", "T0", "HR")

  def upstream_seat(self):
    return self.target if self.arm == "C" else None

  def share_line(self):
    return self.arm in ("A1", "01")

  def order(self, t):
    base = list(self.base_orders[t])
    if self.arm == "E":
      base.remove(self.target)
      base = [self.target] + base
    return base

  def a_estimate(self, t, true_rho):
    return true_rho if self.a_correct[t] else self.a_alt[t]

  def to_dict(self):
    return {
        "seed": self.seed, "arm": self.arm, "names": self.names, "target_seat": self.target,
        "target_name": self.names[self.target], "regen": self.regen[: self.cycles],
        "orders": [self.order(t) for t in range(self.cycles)],
        "a_correct": self.a_correct[: self.cycles], "a_alt": self.a_alt[: self.cycles],
        "cq_seats": self.cq_seats, "hr_roles": self.hr_roles, "cf_x": self.cf_x, "cf_y": self.cf_y,
        "cq_multiplier": self.cq_multiplier, "st_multiplier": self.st_multiplier, "st_n": self.st_n,
    }


def clairvoyant_oracle(regen, capacity=M_DEFAULT, n=5):
  """Total catch when the group harvests the clairvoyant quota every cycle."""
  stock, total = capacity, 0.0
  for rho in regen:
    h = n * psi(stock, rho, capacity, n)
    total += h
    stock = min(capacity, (stock - h) * rho)
  return total


def floor_int(x):
  return int(math.floor(x + 1e-9))
