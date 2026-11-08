"""Leader-emergence measures: summary CSV (one row per run), per-month CSV, plots.

  python scripts/emergence_analyze.py simulation/results/emergence/grid --out runs_meta/emergence_report

Primary
  1. Policy adoption: proposal p (month t) is adopted if a majority of the agents fishing in
     month t+1 request within +/-1 ton of p. If several numbers qualify, the one matched by
     the most agents wins (tie: first proposed). Credit: the agent who first proposed that
     number in month t (speaker taken from the utterance at the extracted turn).
     Per run: each agent's share of adoptable months; dominates = one agent holds > 50% of
     adopted months with >= 3 adopted months.
  2. Social graph: directed edge speaker -> named agent, +1 per name mention in an
     utterance (no nominations: random order after the opener). In-degree, PageRank, Gini
     over in-degree of the agents present; per month and per run.
Secondary: survival, efficiency vs harvesting the sustainable quota with the true draw
(oracle stock stays at 100, so oracle catch = 100 - 100/rho each month), information
collapse (distinct quotas and spread per month).
"""
import argparse
import collections
import csv
import glob
import json
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402

ARMS = ["0", "1", "2", "3a", "3b", "4a", "4b"]


def gini(xs):
  xs = sorted(xs)
  n, s = len(xs), sum(xs)
  if n == 0 or s == 0:
    return 0.0
  return sum((2 * (i + 1) - n - 1) * x for i, x in enumerate(xs)) / (n * s)


def pagerank(edges, nodes):
  g = nx.DiGraph()
  g.add_nodes_from(nodes)
  for (a, b), w in edges.items():
    g.add_edge(a, b, weight=w)
  if g.number_of_edges() == 0:
    return {n: 1 / len(nodes) for n in nodes}
  try:
    return nx.pagerank(g, weight="weight")
  except Exception:  # scipy missing
    from networkx.algorithms.link_analysis.pagerank_alg import _pagerank_python
    return _pagerank_python(g, weight="weight")


def mention_edges(utts, names):
  e = collections.Counter()
  for u in utts:
    for n in names:
      if n != u["speaker"] and re.search(rf"\b{re.escape(n)}\b", u["text"]):
        e[(u["speaker"], n)] += 1
  return e


def proposals_clean(m):
  """[(turn, speaker, per-person number)], speaker from the utterance at that turn.
  Group totals are converted to per-person by dividing by the number of agents present
  (rounded), and a turn stating the same per-person number twice counts once."""
  by_turn = {u["turn"]: u["speaker"] for u in m.get("utterances", [])}
  n = len(m["present"])
  out = set()
  for p in m.get("proposals", []):
    t = p.get("turn")
    if not isinstance(t, int) or t not in by_turn:
      continue  # moderator turn 0 or bad turn
    v = p["number"] / n if p.get("scope") == "group_total" else p["number"]
    out.add((t, by_turn[t], int(round(v))))
  return sorted(out)


def originators(months):
  """per-person number -> (month, agent) of its first proposal anywhere in the run."""
  first = {}
  for m in months:
    for t, s, p in proposals_clean(m):
      first.setdefault(p, (m["month"], s))
  return first


def adoption(months, all_months):
  """months: those with a discussion; all_months: every logged month (for next harvests)."""
  by_no = {m["month"]: m for m in all_months if m.get("harvest_requested")}
  rows = []
  for m in months:
    props = proposals_clean(m)
    nxt = by_no.get(m["month"] + 1)
    row = {"month": m["month"], "n_proposals": len(props), "distinct": len({p for _, _, p in props}),
           "spread": (max(p for *_, p in props) - min(p for *_, p in props)) if props else None,
           "adoptable": bool(nxt and props), "adopted_number": None, "adopted_proposer": None,
           "matched": None, "adopted_originator": None, "originated_month": None}
    if nxt and props:
      req = list(nxt["harvest_requested"].values())
      need = len(req) // 2 + 1
      best = None
      first = {}
      for t, s, p in props:
        first.setdefault(p, (t, s))
      for p, (t, s) in first.items():
        k = sum(abs(h - p) <= 1 for h in req)
        if k >= need and (best is None or (k, -t) > (best[0], -best[1])):
          best = (k, t, s, p)
      if best:
        o = originators(months)[best[3]]
        row.update(adopted_number=best[3], adopted_proposer=best[2], matched=best[0],
                   adopted_originator=o[1], originated_month=o[0])
    rows.append(row)
  return rows


def special_agents(run):
  d = run["design"]
  sp = {}
  if d.get("prosocial"):
    sp["prosocial"] = d["prosocial"]
  for t in d["roster"]:
    if t["persona"] == "outsider":
      sp["newcomer"] = t["name"]
  if d.get("fixed_opener"):
    sp["fixed_opener"] = d["fixed_opener"]
  if run["config"]["arm"] == "4a":
    sp["permanent"] = [t["name"] for t in d["roster"] if t["seat"] == 0][0]
  return sp


def analyse(path):
  run = json.load(open(path))
  cfg, months = run["config"], run["months"]
  names = [t["name"] for t in run["design"]["roster"]]
  disc = [m for m in months if m.get("utterances")]
  ad = adoption(disc, months)
  adoptable = [r for r in ad if r["adoptable"]]
  adopted = [r for r in ad if r["adopted_proposer"]]
  cnt = collections.Counter(r["adopted_proposer"] for r in adopted)
  top, topn = (cnt.most_common(1)[0] if cnt else (None, 0))
  ocnt = collections.Counter(r["adopted_originator"] for r in adopted)
  otop, otopn = (ocnt.most_common(1)[0] if ocnt else (None, 0))
  # social graph
  run_edges = collections.Counter()
  monthly = []
  for m in disc:
    e = mention_edges(m["utterances"], names)
    run_edges.update(e)
    indeg = {n: sum(w for (a, b), w in e.items() if b == n) for n in m["present"]}
    pr = pagerank(e, m["present"])
    monthly.append({"month": m["month"], "gini_indegree": gini(list(indeg.values())),
                    "top_indegree": max(indeg, key=indeg.get) if any(indeg.values()) else None,
                    "top_pagerank": max(pr, key=pr.get), "indegree": indeg, "pagerank": pr})
  ever = sorted({n for m in months for n in m["present"] + m.get("fishers", [])})
  indeg_run = {n: sum(w for (a, b), w in run_edges.items() if b == n) for n in ever}
  pr_run = pagerank(run_edges, ever)
  # efficiency
  total = sum(sum(m.get("harvest", {}).values()) for m in months)
  oracle = sum(100 - 100 / r for r in run["design"]["regen"][:cfg["months"]])
  sp = special_agents(run)
  row = {"arm": cfg["arm"], "seed": cfg["seed"], "months_survived": run["end"]["months_survived"],
         "collapsed": run["end"]["collapsed"], "total_catch": total, "oracle_catch": round(oracle, 1),
         "efficiency": round(total / oracle, 3), "discussion_months": len(disc),
         "adoptable_months": len(adoptable), "adopted_months": len(adopted),
         "top_adopted_agent": top, "top_adopted_share": round(topn / len(adoptable), 3) if adoptable else None,
         "dominates": bool(adopted and topn / len(adopted) > 0.5 and len(adopted) >= 3),
         "top_originator": otop,
         "top_originator_share": round(otopn / len(adoptable), 3) if adoptable else None,
         "gini_indegree_run": round(gini([indeg_run[n] for n in ever]), 3),
         "top_pagerank_agent": max(pr_run, key=pr_run.get), "top_pagerank": round(max(pr_run.values()), 3),
         "mean_distinct_quotas": round(sum(r["distinct"] for r in ad) / len(ad), 2) if ad else None,
         "mean_quota_spread": round(sum(r["spread"] or 0 for r in ad) / len(ad), 2) if ad else None,
         "flags": len(run["flags"]), "cost_usd": run["usage"]["cost_usd"],
         "calls": run["usage"]["calls"], "runtime_s": run.get("runtime_s")}
  for role, n in sp.items():
    row[f"{role}_agent"] = n
    row[f"{role}_adopted_share"] = round(cnt.get(n, 0) / len(adoptable), 3) if adoptable else None
    row[f"{role}_pagerank"] = round(pr_run.get(n, 0), 3)
    row[f"{role}_indegree"] = indeg_run.get(n, 0)
  for role, n in sp.items():
    row[f"{role}_originated_share"] = round(ocnt.get(n, 0) / len(adoptable), 3) if adoptable else None
  per_agent = {n: {"adopted": cnt.get(n, 0), "originated": ocnt.get(n, 0), "indegree": indeg_run[n],
                   "pagerank": round(pr_run[n], 3)}
               for n in ever}
  return run, row, ad, monthly, per_agent


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("group_dir")
  ap.add_argument("--out", default="runs_meta/emergence_report")
  args = ap.parse_args()
  os.makedirs(args.out, exist_ok=True)
  rows, month_rows, per_arm = [], [], collections.defaultdict(list)
  for p in sorted(glob.glob(os.path.join(args.group_dir, "*", "run.json"))):
    run = json.load(open(p))
    if "end" not in run:
      print("skip unfinished", p)
      continue
    run, row, ad, monthly, per_agent = analyse(p)
    row["per_agent"] = json.dumps(per_agent)
    rows.append(row)
    per_arm[row["arm"]].append((row, ad, monthly))
    for a, g in zip(ad, monthly):
      month_rows.append({"arm": row["arm"], "seed": row["seed"], **{k: v for k, v in a.items()},
                         "gini_indegree": round(g["gini_indegree"], 3), "top_indegree": g["top_indegree"],
                         "top_pagerank": g["top_pagerank"]})
  keys = []
  for r in rows:
    keys += [k for k in r if k not in keys]
  with open(os.path.join(args.out, "summary.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys)
    w.writeheader()
    w.writerows(rows)
  if month_rows:
    with open(os.path.join(args.out, "per_month.csv"), "w", newline="") as f:
      w = csv.DictWriter(f, fieldnames=list(month_rows[0]))
      w.writeheader()
      w.writerows(month_rows)
  plots(per_arm, args.out)
  print(f"{len(rows)} runs -> {args.out}/summary.csv, per_month.csv, plots")


def plots(per_arm, out):
  arms = [a for a in ARMS if a in per_arm]
  if not arms:
    return
  # 1. adoption: top-agent share and special-agent share by arm
  fig, ax = plt.subplots(figsize=(7, 3.6))
  for i, a in enumerate(arms):
    tops = [r["top_adopted_share"] for r, *_ in per_arm[a] if r["top_adopted_share"] is not None]
    ax.scatter([i - 0.12] * len(tops), tops, color="#2a6fbb", s=28, label="most-adopted agent" if i == 0 else None)
    for role, c in (("prosocial", "#2e9e5b"), ("newcomer", "#c0392b"), ("fixed_opener", "#8e44ad"),
                    ("permanent", "#d68910")):
      v = [r.get(f"{role}_adopted_share") for r, *_ in per_arm[a] if r.get(f"{role}_adopted_share") is not None]
      if v:
        ax.scatter([i + 0.12] * len(v), v, color=c, marker="D", s=26, label=role.replace("_", " "))
  h, l = ax.get_legend_handles_labels()
  ax.legend(dict(zip(l, h)).values(), dict(zip(l, h)).keys(), fontsize=7, frameon=False, loc="upper right")
  ax.axhline(0.2, color="#999", lw=1, ls=":")
  ax.set_xticks(range(len(arms)), [f"arm {a}" for a in arms])
  ax.set_ylabel("share of adoptable months")
  ax.set_title("Policy adoption: whose quota was followed (dots = seeds; dotted = 1/5)", fontsize=9)
  ax.set_ylim(-0.03, 1.03)
  fig.tight_layout()
  fig.savefig(os.path.join(out, "adoption_by_arm.png"), dpi=150)
  plt.close(fig)
  # 2. social graph: Gini of in-degree per month, mean over seeds
  fig, ax = plt.subplots(figsize=(7, 3.6))
  cmap = plt.get_cmap("tab10")
  for i, a in enumerate(arms):
    by_m = collections.defaultdict(list)
    for _, _, monthly in per_arm[a]:
      for g in monthly:
        by_m[g["month"]].append(g["gini_indegree"])
    ms = sorted(by_m)
    ax.plot(ms, [sum(by_m[m]) / len(by_m[m]) for m in ms], color=cmap(i), lw=2, marker="o", ms=3, label=f"arm {a}")
  ax.set_xlabel("month")
  ax.set_ylabel("Gini of mention in-degree")
  ax.set_title("Social graph concentration per month (mean over seeds)", fontsize=9)
  ax.legend(fontsize=7, frameon=False, ncol=4)
  fig.tight_layout()
  fig.savefig(os.path.join(out, "graph_gini_by_month.png"), dpi=150)
  plt.close(fig)


if __name__ == "__main__":
  main()
