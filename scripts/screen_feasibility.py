"""CQ and St feasibility checks (spec section 2), using seeds 1-5's regeneration draws.

CQ: 2 pressured agents take Q_hi = round(m * expected quota), 3 take the expected quota,
    recomputed each cycle at the current stock. Pass if the stock survives >= 3 cycles
    (stock after harvest >= 5) in all 5 seeds. m starts at 1.6, steps down 0.1 to 1.2.
St: target takes N = round(m * expected quota at full stock) every cycle; the others take
    max(0, (5 * expected quota - N) / 4) each, expected quota recomputed at the current
    stock. Pass if the stock survives all 6 cycles in all 5 seeds. m starts at 1.2, steps
    down 0.05.
Writes runs_meta/feasibility.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from simulation.screen.design import Design, expected_quota  # noqa: E402

POOL = ["Julia", "Kate", "Jack", "Emma", "Luke", "Noah", "Olivia", "Liam", "Sophia", "Mason"]
SEEDS, CYCLES, M, N_AG = [1, 2, 3, 4, 5], 6, 100, 5


def simulate(regen, take):
  stock, survived, traj = M, 0, []
  for t, rho in enumerate(regen[:CYCLES]):
    harvest = take(stock)
    remain = stock - harvest
    traj.append((stock, round(harvest, 2), round(remain, 2)))
    if remain < 5:
      return survived, traj
    survived += 1
    stock = min(M, int(remain * rho))
  return survived, traj


def cq(m):
  out = {}
  for s in SEEDS:
    regen = Design(s, "CQ", POOL).regen
    def take(stock):
      e = expected_quota(stock, M, N_AG)
      return 2 * round(m * e) + 3 * e
    out[s] = simulate(regen, take)
  return out


def st(m):
  n = round(m * expected_quota(M, M, N_AG))
  out = {}
  for s in SEEDS:
    regen = Design(s, "St", POOL).regen
    def take(stock):
      e = expected_quota(stock, M, N_AG)
      return n + 4 * max(0.0, (N_AG * e - n) / 4)
    out[s] = simulate(regen, take)
  return n, out


def main():
  report = {}
  m = 1.6
  while True:
    res = cq(m)
    ok = all(v[0] >= 3 for v in res.values())
    report.setdefault("cq_tried", []).append({"multiplier": round(m, 2), "pass": ok,
                                              "survival": {s: v[0] for s, v in res.items()}})
    if ok or m <= 1.2 + 1e-9:
      report["cq_multiplier"] = round(m, 2) if ok else None
      break
    m -= 0.1
  m = 1.2
  while True:
    n, res = st(m)
    ok = all(v[0] >= CYCLES for v in res.values())
    report.setdefault("st_tried", []).append({"multiplier": round(m, 2), "N": n, "pass": ok,
                                              "survival": {s: v[0] for s, v in res.items()}})
    if ok or m <= 1.0 + 1e-9:
      report["st_multiplier"] = round(m, 2) if ok else None
      report["st_N"] = n if ok else None
      break
    m -= 0.05
  os.makedirs("runs_meta", exist_ok=True)
  json.dump(report, open("runs_meta/feasibility.json", "w"), indent=2)
  print(json.dumps(report, indent=2))


if __name__ == "__main__":
  main()
