"""Leadership screen analysis: metrics (spec section 5), pre-registered decision rules
(section 6) and the morning report (section 8).

Usage: python scripts/screen_analyze.py [results_group_dir] [--out runs_meta/report]
Committed before any screen data was collected; do not change rules after seeing data.
"""
import argparse
import collections
import glob
import json
import os
import re
import statistics
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from simulation.screen.design import clairvoyant_oracle, expected_quota  # noqa: E402

RNG = np.random.default_rng(12345)
N_SHUFFLE = 10_000
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0)}
TARGET_ARMS = ["0", "A", "B", "C", "T", "T0", "E", "S", "St", "A1", "01"]
COMPARISON = {"A": "0", "B": "S", "C": "S", "St": "S", "E": "0", "A1": "01"}


# ======================================================================== loading
def load_run(run_dir):
  rows = [json.loads(l) for l in open(os.path.join(run_dir, "screen_log.jsonl"))]
  by = collections.defaultdict(list)
  for r in rows:
    by[r["type"]].append(r)
  if not by["design"]:
    return None
  d = by["design"][0]
  run = {"dir": run_dir, "arm": d["arm"], "seed": d["seed"], "design": d, "names": d["names"],
         "target": d["names"][d["target_seat"]], "cycles": {}, "interviews": by["interview"],
         "writes": by["write"], "margins": by["margin"], "ended": bool(by["run_end"]),
         "final_stock": by["run_end"][0]["final_stock"] if by["run_end"] else None}
  for r in by["cycle_start"]:
    run["cycles"][r["cycle"]] = {"start": r, "utts": [], "proposals": None, "probe": None, "harvest": None,
                                 "failures": []}
  for r in by["utterance"]:
    run["cycles"][r["cycle"]]["utts"].append(r)
  for r in by["proposals"]:
    run["cycles"][r["cycle"]]["proposals"] = r["proposals"]
    run["cycles"][r["cycle"]]["failures"] = r["parse_failures"]
  for r in by["probe"]:
    run["cycles"][r["cycle"]]["probe"] = r["answers"]
  for r in by["harvest"]:
    run["cycles"][r["cycle"]]["harvest"] = r
  usage = os.path.join(run_dir, "api_usage.jsonl")
  run["cost"], run["calls"] = 0.0, 0
  if os.path.exists(usage):
    for l in open(usage):
      u = json.loads(l)
      p_in, p_out = PRICES.get(u["model"], (0, 0))
      run["cost"] += u["input_tokens"] * p_in / 1e6 + u["output_tokens"] * p_out / 1e6
      run["calls"] += 1
  return run


# ======================================================================== per-cycle metrics
def first_turn_proposals(c):
  """Proposals in speaking order: list of (name, value) with value not None."""
  out = []
  for u in sorted((u for u in c["utts"] if u.get("first_turn")), key=lambda u: u["turn"]):
    if u.get("proposal") is not None:
      out.append((u["speaker"], u["proposal"]))
  return out


def credit(c, use_calculator):
  """Credit shares for one cycle: {name or 'calculator': share}. Closest proposal to the
  median of the OTHER agents' collected harvests; ties split; calculator Y is a
  pseudo-agent that agents must strictly beat."""
  props = dict(first_turn_proposals(c))
  got = c["harvest"]["collected"]
  y = c["start"].get("calculator_y")
  dist, ydist = {}, {}
  for name, p in props.items():
    others = [v for n, v in got.items() if n != name]
    med = statistics.median(others)
    dist[name] = abs(p - med)
    if use_calculator and y is not None:
      ydist[name] = abs(y - med)
  eligible = {n: dd for n, dd in dist.items() if not use_calculator or y is None or dd < ydist[n]}
  if not eligible:
    return {"calculator": 1.0}
  best = min(eligible.values())
  winners = [n for n, dd in eligible.items() if dd == best]
  return {n: 1.0 / len(winners) for n in winners}


def cycle_metrics(run):
  out = []
  use_calc = run["arm"] in ("T", "T0", "HR")
  for t in sorted(run["cycles"]):
    c = run["cycles"][t]
    if c["harvest"] is None:
      continue
    props = first_turn_proposals(c)
    vals = [v for _, v in props]
    eq = c["start"]["expected_quota"]
    rng = (max(vals) - min(vals)) if len(vals) >= 2 else None
    med = statistics.median(vals) if vals else None
    err = abs(med - eq) / eq if (vals and eq > 0) else None
    anch = []
    for k in range(1, len(vals)):
      others = [abs(vals[k] - vals[j]) for j in range(len(vals)) if j != k]
      anch.append(abs(vals[k] - vals[k - 1]) - statistics.mean(others))
    probe_vals = [v for v in (c["probe"] or {}).values() if v is not None]
    prange = (max(probe_vals) - min(probe_vals)) if len(probe_vals) >= 2 else None
    group = sum(c["harvest"]["collected"].values())
    out.append({
        "cycle": t, "range": rng, "median": med, "eq": eq, "error": err, "contested": rng is not None and rng >= 2,
        "credit": credit(c, use_calc) if (rng is not None and rng >= 2) else {},
        "anchoring": statistics.mean(anch) if anch else None,
        "probe_range": prange, "gap": (prange - rng) if (prange is not None and rng is not None) else None,
        "conformity": prange is not None and rng is not None and prange >= 2 and rng <= 1,
        "group_catch": group, "over": group > 5 * eq, "stock_after": c["harvest"]["stock_after"],
        "y": c["start"].get("calculator_y"), "wanted": c["harvest"]["wanted"],
        "n_first": sum(1 for u in c["utts"] if u.get("first_turn")),
        "n_fail": sum(1 for f in c["failures"] if f["attempt"] == 2),
    })
  return out


# ======================================================================== per-run metrics
def run_metrics(run):
  cm = cycle_metrics(run)
  regen = run["design"]["regen"]
  total = sum(m["group_catch"] for m in cm)
  oracle = clairvoyant_oracle(regen)
  collapsed_at = next((m["cycle"] for m in cm if m["stock_after"] < 5), None)
  last = cm[-1] if cm else None
  if last is None or last["range"] is None:
    cls = "unknown"
  elif last["range"] <= 1 and last["error"] is not None and last["error"] <= 0.25:
    cls = "healthy"
  elif last["range"] <= 1:
    cls = "collapse"
  else:
    cls = "no convergence"
  lock = next((m for m in cm if m["range"] is not None and m["range"] <= 1), None)
  credits = collections.Counter()
  for m in cm:
    for n, s in m["credit"].items():
      credits[n] += s
  mentions = collections.Counter()
  for c in run["cycles"].values():
    for u in c["utts"]:
      for n in run["names"]:
        if n != u["speaker"]:
          mentions[n] += len(re.findall(rf"\b{n}\b", u["text"]))
  n_first = sum(m["n_first"] for m in cm)
  n_fail = sum(m["n_fail"] for m in cm)
  flags = []
  if len(cm) < 4:
    flags.append("<4 cycles")
  if n_first and n_fail / n_first > 0.10:
    flags.append("PROPOSAL parse failures >10%")
  if not run["ended"]:
    flags.append("did not finish")
  # silent upstream fallbacks (pathfinder parse failure -> default value, e.g. a 0-ton harvest)
  group = os.path.basename(os.path.dirname(run["dir"]))
  logf = os.path.join("runs_meta", "logs", group, os.path.basename(run["dir"]) + ".log")
  n_default = open(logf).read().count("An exception occured") if os.path.exists(logf) else None
  if n_default:
    flags.append(f"{n_default} silent default value(s)")
  return {
      "arm": run["arm"], "seed": run["seed"], "target": run["target"], "cycles": cm,
      "completed": len(cm), "survived": len(cm) == 6 and collapsed_at is None,
      "survival_time": collapsed_at if collapsed_at is not None else len(cm),
      "final_stock_frac": (run["final_stock"] or 0) / 100, "efficiency": total / oracle if oracle else None,
      "over_rate": statistics.mean(m["over"] for m in cm) if cm else None,
      "contested": sum(m["contested"] for m in cm), "credits": credits,
      "target_credits": credits.get(run["target"], 0.0), "class": cls,
      "lock_cycle": lock["cycle"] if lock else None, "lock_error": lock["error"] if lock else None,
      "anchoring": _mean([m["anchoring"] for m in cm]), "gap": _mean([m["gap"] for m in cm]),
      "conformity": any(m["conformity"] for m in cm), "mentions": mentions, "flags": flags,
      "parse_fail_rate": n_fail / n_first if n_first else None, "cost": run["cost"], "calls": run["calls"],
      "interviews": collections.Counter(i["answer"] or "unparsed" for i in run["interviews"]),
  }


def _mean(xs):
  xs = [x for x in xs if x is not None]
  return statistics.mean(xs) if xs else None


# ======================================================================== arm-level
def pooled_rate(rms):
  cont = sum(r["contested"] for r in rms)
  return (sum(r["target_credits"] for r in rms) / cont if cont else None), cont


def permutation_null(baseline_runs):
  runs = [(r["credits"], r["contested"], [n for n in r["names_all"]]) for r in baseline_runs]
  cont = sum(c for _, c, _ in runs)
  if not cont:
    return None, None
  sims = np.empty(N_SHUFFLE)
  for k in range(N_SHUFFLE):
    tot = 0.0
    for cr, _, names in runs:
      tot += cr.get(names[RNG.integers(len(names))], 0.0)
    sims[k] = tot / cont
  return float(sims.mean()), float(np.percentile(sims, 95))


def sc_correlation(runs, metrics):
  units = []
  for run, rm in zip(runs, metrics):
    vol = collections.Counter()
    for w in run["writes"]:
      vol[w["author"]] += w["chars"]
    units.append([(vol.get(n, 0), rm["credits"].get(n, 0.0)) for n in run["names"]])
  def corr(us):
    xs = [x for u in us for x, _ in u]
    ys = [y for u in us for _, y in u]
    if np.std(xs) == 0 or np.std(ys) == 0:
      return None
    return float(np.corrcoef(xs, ys)[0, 1])
  obs = corr(units)
  if obs is None:
    return None, None
  sims = []
  for _ in range(N_SHUFFLE):
    sh = []
    for u in units:
      xs = [x for x, _ in u]
      RNG.shuffle(xs)
      sh.append(list(zip(xs, [y for _, y in u])))
    c = corr(sh)
    if c is not None:
      sims.append(c)
  return obs, (float(np.percentile(sims, 95)) if sims else None)


def calculator_adherence(rm):
  hits = []
  for m in rm["cycles"]:
    if m["y"] is None:
      continue
    hits += [abs(w - m["y"]) <= 1 for w in m["wanted"].values()]
  return statistics.mean(hits) if hits else None


def a_disclosure(run, seat_name, key="r"):
  """First (cycle, turn) at which the named agent states its private estimate (or a number within 0.1)."""
  for t in sorted(run["cycles"]):
    c = run["cycles"][t]
    info = c["start"].get("a_info") or {}
    r = info.get(key)
    if r is None:
      continue
    for u in sorted(c["utts"], key=lambda u: u["turn"]):
      if u["speaker"] != seat_name:
        continue
      nums = [float(x) for x in re.findall(r"\d+\.\d+", u["text"])]
      if any(abs(x - r) <= 0.1 for x in nums):
        return {"cycle": t, "turn": u["turn"]}
  return None


# ======================================================================== report
def fmt(x, nd=2):
  if x is None:
    return "–"
  if isinstance(x, float):
    return f"{x:.{nd}f}"
  return str(x)


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("group_dir", nargs="?", default="simulation/results/screen_v7.0/screen")
  ap.add_argument("--out", default="runs_meta/report")
  args = ap.parse_args()
  os.makedirs(args.out, exist_ok=True)

  runs = [r for r in (load_run(d) for d in sorted(glob.glob(os.path.join(args.group_dir, "arm-*")))
                      if os.path.exists(os.path.join(d, "screen_log.jsonl"))) if r]
  metrics = []
  for r in runs:
    m = run_metrics(r)
    m["names_all"] = r["names"]
    metrics.append(m)
  by_arm = collections.defaultdict(list)
  for r, m in zip(runs, metrics):
    by_arm[r["arm"]].append((r, m))

  base = [m for _, m in by_arm.get("0", [])]
  null_mean, null95 = permutation_null(base)
  feas = json.load(open("runs_meta/feasibility.json")) if os.path.exists("runs_meta/feasibility.json") else {}
  meta0 = json.load(open(os.path.join(runs[0]["dir"], "meta.json"))) if runs else {}
  total_cost = sum(m["cost"] for m in metrics)

  rate = {a: pooled_rate([m for _, m in v]) for a, v in by_arm.items() if a in TARGET_ARMS}
  s_rate = rate.get("S", (None, 0))[0]
  salience_flag = s_rate is not None and null95 is not None and s_rate > null95

  # A-fallback trigger: target disclosed in fewer than 3 of 5 seeds
  a_disc = {r["seed"]: a_disclosure(r, r["target"]) for r, _ in by_arm.get("A", [])}
  fallback = len(a_disc) >= 5 and sum(v is not None for v in a_disc.values()) < 3

  # T vs T0
  t_same_seat = {}
  for arm in ("T", "T0"):
    rms = [m for _, m in by_arm.get(arm, [])]
    t_same_seat[arm] = {"rate": pooled_rate(rms)[0], "contested": pooled_rate(rms)[1],
                        "mentions": sum(m["mentions"].get(m["target"], 0) for m in rms),
                        "adherence": _mean([calculator_adherence(m) for m in rms]),
                        "efficiency": _mean([m["efficiency"] for m in rms]),
                        "calc_credit": sum(m["credits"].get("calculator", 0) for m in rms)}

  verdicts = {}
  for arm in TARGET_ARMS + ["T"]:
    if arm not in by_arm:
      continue
    r_, cont = rate.get(arm, (None, 0))
    if cont < 10:
      verdicts[arm] = "insufficient data (<10 contested)"
      continue
    if arm in COMPARISON:
      comp = rate.get(COMPARISON[arm], (None, 0))[0]
      ok = (r_ is not None and r_ >= 0.40 and null95 is not None and r_ > null95
            and comp is not None and r_ >= 2 * comp)
      v = "PROMISING" if ok else "not promising"
      if comp is None:
        v += " (comparison arm missing)"
      if arm in ("B", "C", "St") and salience_flag:
        v += " [salience flag]"
      verdicts[arm] = v
    elif arm == "T":
      tt, t0 = t_same_seat["T"], t_same_seat["T0"]
      adher_ok = (tt["adherence"] is not None and t0["adherence"] is not None
                  and abs(tt["adherence"] - t0["adherence"]) <= 0.10)
      rate_ok = tt["rate"] is not None and t0["rate"] is not None and tt["rate"] - t0["rate"] >= 0.15
      ment_ok = t0["mentions"] > 0 and tt["mentions"] >= 2 * t0["mentions"] or (t0["mentions"] == 0 and tt["mentions"] > 0)
      verdicts[arm] = ("PROMISING" if (rate_ok or ment_ok) and adher_ok else "not promising") + (
          "" if adher_ok else " (adherence differs >0.10)")
    elif arm == "S":
      verdicts[arm] = "salience above null 95th" if salience_flag else "salience at/below null"
    else:
      verdicts[arm] = "reference"

  sc_runs = [r for r, _ in by_arm.get("Sc", [])]
  sc_ms = [m for _, m in by_arm.get("Sc", [])]
  sc_corr, sc_null95 = sc_correlation(sc_runs, sc_ms) if sc_runs else (None, None)
  if sc_runs:
    verdicts["Sc"] = ("PROMISING" if sc_corr is not None and sc_null95 is not None and sc_corr > 0
                      and sc_corr > sc_null95 else "not promising")

  # ---------------------------------------------------------------- write report
  L = []
  L.append("# Overnight leadership screen — morning report\n")
  L.append("**This is a cheap screen. Nothing here is a finding until it replicates on fresh seeds (6–10).**\n")
  L.append("## Header\n")
  L.append("- **Cycle order deviation:** each cycle runs discussion → harvest → reflection "
           "(GovSim/AgentElect run harvest → discussion → reflection).")
  L.append("- **Sampling deviation:** temperature 0.7 was not used. `claude-haiku-5-5` rejects any non-default "
           "sampling parameter (API version 2026-10-21), so all calls use the API default sampling (stochastic).")
  L.append(f"- **Git hash:** `{meta0.get('git_hash', '?')}` (dirty: {meta0.get('git_dirty', '?')})")
  L.append(f"- **CQ multiplier used:** {feas.get('cq_multiplier')} · **St N used:** {feas.get('st_N')} "
           f"(multiplier {feas.get('st_multiplier')})")
  L.append(f"- **A-fallback triggered:** {'yes' if fallback else 'no'} "
           f"(target disclosed in {sum(v is not None for v in a_disc.values())} of {len(a_disc)} A seeds)")
  L.append(f"- **Runs analysed:** {len(runs)} · **total cost:** ${total_cost:.2f} · "
           f"**API calls:** {sum(m['calls'] for m in metrics):,}")
  flagged = [(m["arm"], m["seed"], m["flags"]) for m in metrics if m["flags"]]
  flag_txt = ", ".join("%s/s%s (%s)" % (a, s, "; ".join(f)) for a, s, f in flagged) or "none"
  L.append(f"- **Flagged runs:** {flag_txt}")
  L.append(f"- **Permutation null (baseline, random agent, {N_SHUFFLE:,} shuffles):** mean {fmt(null_mean)}, "
           f"95th pct {fmt(null95)}\n")

  L.append("## Main table\n")
  L.append("| Arm | Pooled target rate | Contested | Null 95th | Comparison (rate) | Verdict | Survival | "
           "Mean efficiency | Over-harvest | Classes (H/C/N) | Anchoring | Priv–pub gap | Conformity runs |")
  L.append("|" + "---|" * 13)
  for arm in ["0", "A", "B", "C", "T", "T0", "E", "S", "Sc", "CQ", "St", "HR", "CF", "A1", "01"]:
    if arm not in by_arm:
      continue
    rms = [m for _, m in by_arm[arm]]
    r_, cont = pooled_rate(rms) if arm in TARGET_ARMS else (None, sum(m["contested"] for m in rms))
    comp = COMPARISON.get(arm) or ("T0 (same seat)" if arm == "T" else None)
    comp_rate = rate.get(COMPARISON[arm], (None,))[0] if arm in COMPARISON else (
        t_same_seat["T0"]["rate"] if arm == "T" else None)
    cls = collections.Counter(m["class"] for m in rms)
    L.append(f"| {arm} | {fmt(r_)} | {cont} | {fmt(null95)} | {comp or '–'} ({fmt(comp_rate)}) | "
             f"{verdicts.get(arm, '–')} | {sum(m['survived'] for m in rms)}/{len(rms)} | "
             f"{fmt(_mean([m['efficiency'] for m in rms]))} | {fmt(_mean([m['over_rate'] for m in rms]))} | "
             f"{cls['healthy']}/{cls['collapse']}/{cls['no convergence']} | {fmt(_mean([m['anchoring'] for m in rms]))} | "
             f"{fmt(_mean([m['gap'] for m in rms]))} | {sum(m['conformity'] for m in rms)} |")
  L.append("\nRates are pooled target credits / pooled contested cycles. A cycle is contested when "
           "first-turn proposals span ≥ 2 tons. ~11 comparisons at this threshold: expect up to one false hit.\n")

  L.append("## Per-seed pairs (common random numbers)\n")
  for arm, comp in list(COMPARISON.items()) + [("T", "T0")]:
    if arm not in by_arm or comp not in by_arm:
      continue
    L.append(f"**{arm} vs {comp}** — target credits / contested cycles per seed\n")
    L.append("| Seed | " + arm + " | " + comp + " |")
    L.append("|---|---|---|")
    a_by = {m["seed"]: m for _, m in by_arm[arm]}
    c_by = {m["seed"]: m for _, m in by_arm[comp]}
    for s in sorted(set(a_by) | set(c_by)):
      f = lambda m: f"{m['target_credits']:.1f}/{m['contested']}" if m else "–"
      L.append(f"| {s} | {f(a_by.get(s))} | {f(c_by.get(s))} |")
    L.append("")

  L.append("## T vs T0 (calculator)\n")
  L.append("| Arm | Target rate | Contested | Target mentions | Adherence (±1 of Y) | Efficiency | Calculator credits |")
  L.append("|---|---|---|---|---|---|---|")
  for a in ("T", "T0"):
    x = t_same_seat[a]
    L.append(f"| {a} | {fmt(x['rate'])} | {x['contested']} | {x['mentions']} | {fmt(x['adherence'])} | "
             f"{fmt(x['efficiency'])} | {fmt(x['calc_credit'], 1)} |")
  L.append("")

  if sc_runs:
    L.append("## Sc (scratchpad)\n")
    L.append(f"- Correlation (write volume vs credits, pooled agent-runs): {fmt(sc_corr)}; "
             f"shuffle-null 95th: {fmt(sc_null95)} → {verdicts.get('Sc')}")
    st = collections.Counter()
    overlaps = 0
    for r in sc_runs:
      for w in r["writes"]:
        for k, v in (w.get("structure") or {}).items():
          st[k] += bool(v)
        overlaps += w["overlap"] > 0.9
    nw = sum(1 for r in sc_runs for w in r["writes"] if w["text"])
    L.append(f"- Writes: {nw}; structure flags — header {st['header']}, list {st['list']}, "
             f"summary of others {st['summary_of_others']}; writes overlapping speech >90%: {overlaps}\n")

  if "CQ" in by_arm:
    L.append("## CQ (conflicting quota, descriptive)\n")
    pres = unp = 0.0
    for r, m in by_arm["CQ"]:
      seats = set(r["design"]["cq_seats"])
      for n, s in m["credits"].items():
        if n == "calculator":
          continue
        if r["names"].index(n) in seats:
          pres += s
        else:
          unp += s
    cls = collections.Counter(m["class"] for _, m in by_arm["CQ"])
    L.append(f"- Credits: pressured (2 seats) {pres:.1f}, unpressured (3 seats) {unp:.1f}; run classes {dict(cls)}\n")

  if "St" in by_arm:
    shares = []
    for r, m in by_arm["St"]:
      for c in m["cycles"]:
        pass
      for t, c in r["cycles"].items():
        props = dict(first_turn_proposals(c))
        if r["target"] in props:
          shares.append(props[r["target"]] <= c["start"]["expected_quota"])
    L.append("## St (asymmetric stakes)\n")
    L.append(f"- Target rate {fmt(rate.get('St', (None,))[0])}; pro-social share (target proposals ≤ expected "
             f"quota) {fmt(_mean(shares))}, extractive share {fmt(1 - _mean(shares) if shares else None)}\n")

  if "HR" in by_arm:
    L.append("## HR (horse race) — credits by role\n")
    roles = collections.Counter()
    for r, m in by_arm["HR"]:
      role_of = {r["names"][s]: f"{k}-role" for k, s in r["design"]["hr_roles"].items()}
      for n, s in m["credits"].items():
        roles[role_of.get(n, "calculator" if n == "calculator" else "plain")] += s
    L.append("| Role | Credits |\n|---|---|")
    for k, v in roles.most_common():
      L.append(f"| {k} | {v:.1f} |")
    L.append("")

  L.append("## Interview tallies by arm\n")
  for arm, v in sorted(by_arm.items()):
    tal = collections.Counter()
    for r, m in v:
      for name, k in m["interviews"].items():
        tal["target" if name == r["target"] and arm in TARGET_ARMS else name] += k
    L.append(f"- **{arm}:** {dict(tal.most_common())}")
  L.append("")

  L.append("## A disclosure and CF\n")
  for s, v in sorted(a_disc.items()):
    L.append(f"- A seed {s}: {'disclosed at cycle %d turn %d' % (v['cycle'], v['turn']) if v else 'not disclosed'}")
  for r, _ in by_arm.get("CF", []):
    x, y = r["names"][r["design"]["cf_x"]], r["names"][r["design"]["cf_y"]]
    dx, dy = a_disclosure(r, x, "rx"), a_disclosure(r, y, "ry")
    L.append(f"- CF seed {r['seed']}: X ({x}) voiced: {'yes' if dx else 'no'}; Y ({y}) voiced: {'yes' if dy else 'no'}")
  L.append("")

  _plots(by_arm, args.out, L)

  L.append("## Transcript paths\n")
  promising = [a for a, v in verdicts.items() if v.startswith("PROMISING")]
  top = max((a for a in rate if rate[a][0] is not None), key=lambda a: rate[a][0], default=None)
  picks = []
  for arm in ([top] if top else []) + ["T"] + promising:
    picks += [(arm, r["dir"]) for r, _ in by_arm.get(arm, [])[:1]]
  picks += [("CQ", r["dir"]) for r, _ in by_arm.get("CQ", [])[:1]]
  picks += [("St", r["dir"]) for r, _ in by_arm.get("St", [])[:1]]
  picks += [(f"collapse {m['arm']}", r["dir"]) for r, m in zip(runs, metrics) if m["class"] == "collapse"]
  for label, p in dict.fromkeys(picks):
    L.append(f"- {label}: `{os.path.join(p, 'screen_log.jsonl')}`")

  open(os.path.join(args.out, "report.md"), "w").write("\n".join(L) + "\n")
  json.dump([{k: v for k, v in m.items() if k not in ("cycles",)} for m in metrics],
            open(os.path.join(args.out, "run_metrics.json"), "w"), default=str, indent=1)
  print("\n".join(L))


def _plots(by_arm, out, L):
  try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
  except Exception:
    return
  fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
  for arm, v in sorted(by_arm.items()):
    per = collections.defaultdict(lambda: ([], []))
    for _, m in v:
      for c in m["cycles"]:
        if c["range"] is not None:
          per[c["cycle"]][0].append(c["range"])
        if c["error"] is not None:
          per[c["cycle"]][1].append(c["error"])
    xs = sorted(per)
    axes[0].plot([x + 1 for x in xs], [_mean(per[x][0]) for x in xs], marker="o", label=arm)
    axes[1].plot([x + 1 for x in xs], [_mean(per[x][1]) for x in xs], marker="o", label=arm)
  axes[0].set(title="Proposal dispersion (range, tons)", xlabel="Cycle")
  axes[1].set(title="Convergence error |median − expected| / expected", xlabel="Cycle")
  axes[1].legend(ncol=2, fontsize=8)
  fig.tight_layout()
  p = os.path.join(out, "per_cycle.png")
  fig.savefig(p, dpi=130)
  L.append(f"## Per-cycle plots\n\n![per-cycle]({os.path.basename(p)})\n")


if __name__ == "__main__":
  main()
