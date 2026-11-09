"""ANALYSIS_PLAN.md B4 Phase 1 (free analyses) on validated v3 runs.

Reads runs/v3 read-only (see metrics.repo_root); writes only under analysis/.
Run from the folder that contains analysis/ (repo root):  PYTHONDONTWRITEBYTECODE=1 python3 analysis/phase1.py
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import metrics as M  # noqa: E402

ROOT = M.repo_root() / "runs" / "v3"
RES = HERE / "results"
FIG = HERE / "figures"
RES.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)
KEYS = M.KeyLog()

CONDITIONS = ["replica_N8", "baseline_N8", "values_N8", "stakes_N8", "coord_N16", "coord_N32"]
SEEDS = range(5)
NULL_DRAWS = 10_000
BOOT = 10_000
H2_DRAWS = 100_000
PHASES = ("whole", "opening", "nomination")


def se(x):
    x = np.asarray([v for v in x if v is not None], float)
    return float(np.std(x, ddof=1) / np.sqrt(len(x))) if len(x) > 1 else float("nan")


def authors_se(x):
    x = np.asarray([v for v in x if v is not None], float)
    return float(np.sqrt(((x - x.mean()) ** 2).sum()) / (len(x) - 1)) if len(x) > 1 else float("nan")


def boot_ci(values, measure, condition):
    v = np.asarray([x for x in values if x is not None and not np.isnan(x)], float)
    if len(v) < 2:
        return (float("nan"), float("nan"))
    rng = KEYS.rng(f"analysis|boot|{measure}|{condition}", BOOT)
    means = v[rng.integers(len(v), size=(BOOT, len(v)))].mean(axis=1)
    return tuple(map(float, np.percentile(means, [2.5, 97.5])))


# ---------------------------------------------------------------- load validated runs (B0.2)
def validated_runs():
    runs, missing = {}, []
    for cond in CONDITIONS:
        for s in SEEDS:
            d = ROOT / cond / f"seed{s}"
            check = ROOT / "checks" / cond / f"seed{s}.json"
            if not (d / "run_meta.json").exists() or not check.exists():
                missing.append((cond, s, "not complete" if d.exists() else "not started"))
                continue
            chk = json.loads(check.read_text())
            meta = json.loads((d / "run_meta.json").read_text())
            if not chk.get("valid") or meta.get("commit_hash") != "6dc545450dcc9100d1e504376b0baf5bb3e2e98f" \
                    or meta.get("run_kind") != "full":
                missing.append((cond, s, "not validated"))
                continue
            run = M.load_run(d)
            run["check"] = chk
            runs[(cond, s)] = run
    return runs, missing


def present(cycle):
    return [c["identity"] for c in cycle["catches"]]


def focal_identity(run):
    meta = run["meta"]
    if meta["condition"] == "values_N8":
        return meta["values_focal"]["identity"]
    if meta["condition"] == "stakes_N8":
        sched = [r for r in meta["stakes_schedule"] if r["horizon"] == 16]
        assert len(sched) == 1
        return sched[0]["identity"]
    return None


def cycle_turns(run, c):
    return [t for t in run["turns"] if t["cycle"] == c]


# ---------------------------------------------------------------- B1.3 regression
def regression(runs):
    rep = [runs[("replica_N8", s)] for s in SEEDS if ("replica_N8", s) in runs]
    totals = [sum(c["actual"] for cy in r["cycles"] for c in cy["catches"]) for r in rep]
    eq = []
    for r in rep:
        by_slot = defaultdict(float)
        for cy in r["cycles"]:
            for c in cy["catches"]:
                by_slot[c["slot"]] += c["actual"]
        eq.append(1 - M.gini(by_slot.values()))
    out = {"n_runs": len(rep), "total_catch_mean": float(np.mean(totals)), "total_catch_se": se(totals),
           "equality_mean": float(np.mean(eq)), "equality_se": se(eq)}
    out["matches_REPLICA_CHECK"] = (round(out["total_catch_mean"], 1) == 195.4 and round(out["total_catch_se"], 1) == 26.5
                                    and round(out["equality_mean"], 3) == 0.955 and round(out["equality_se"], 3) == 0.006)
    # same flags: all four A11 metrics above their bands
    bands = {"welfare": 155.402075, "survival_time": 5.9, "survival_rate": 0.9, "equality": 0.705564}
    surv = [len(r["cycles"]) for r in rep]
    rate = [not any(cy["collapse"] for cy in r["cycles"]) for r in rep]
    out["flags_all_high"] = (out["total_catch_mean"] - out["total_catch_se"] > 87.727925 and out["total_catch_mean"] > bands["welfare"]
                             and np.mean(surv) > bands["survival_time"] and np.mean(rate) > bands["survival_rate"]
                             and out["equality_mean"] > bands["equality"])
    return out


# ---------------------------------------------------------------- A7 data quality
def data_quality(runs):
    rows = []
    for (cond, s), r in sorted(runs.items()):
        harvest_fb = harvest_zero_parsed = harvest_fail = harvest_n = 0
        trunc = 0
        for call in M.load_calls(r["path"]):
            trunc += call["finish_reason"] == "length"
            if call["call_type"] == "harvest":
                harvest_n += 1
                for op in call.get("parse_operations", []):
                    if op["name"] == "option":
                        harvest_fail += op["status"] == "failed"
                        if op.get("fallback_applied"):
                            harvest_fb += 1
        for cy in r["cycles"]:
            harvest_zero_parsed += sum(c["requested"] == 0 for c in cy["catches"])
        src = Counter(t["nomination_source"] for t in r["turns"])
        chk = r["check"]
        pr = chk["parse_rates"]
        rows.append({
            "condition": cond, "seed": s, "status": r["meta"]["status"], "cycles": len(r["cycles"]),
            "utterances": len(r["turns"]), "truncations": trunc, "harvest_calls": harvest_n,
            "harvest_parse_failures": harvest_fail, "harvest_fallback_values": harvest_fb,
            "harvest_zero_requests_total": harvest_zero_parsed,
            "nominations_agent": src["agent"], "nominations_judge": src["judge"], "nominations_random": src["random"],
            "nominations_end": src["end"], "fixed_opening": src["fixed_opening"],
            "random_share_of_routed": src["random"] / max(1, src["agent"] + src["judge"] + src["random"]),
            "elicitation_parse_rate": pr.get("elicitation_success_rate"),
            "perceived_parse_rate": pr.get("perceived_leadership_success_rate"),
            "nominee_failure_rate": pr.get("nominee_failure_rate"),
            "count_429": chk["429_count"], "count_402": chk["402_count"], "cost_usd": chk["cost"],
        })
    df = pd.DataFrame(rows)
    df.to_csv(RES / "data_quality_by_run.csv", index=False)
    agg = df.groupby("condition").agg(
        runs=("seed", "count"), truncations=("truncations", "sum"), harvest_parse_failures=("harvest_parse_failures", "sum"),
        harvest_fallback_values=("harvest_fallback_values", "sum"), harvest_zero_requests=("harvest_zero_requests_total", "sum"),
        nominations_agent=("nominations_agent", "sum"), nominations_judge=("nominations_judge", "sum"),
        nominations_random=("nominations_random", "sum"), nominations_end=("nominations_end", "sum"),
        elicitation_parse_rate=("elicitation_parse_rate", "mean"), perceived_parse_rate=("perceived_parse_rate", "mean"),
        count_429=("count_429", "sum"), count_402=("count_402", "sum"), cost_usd=("cost_usd", "sum")).reset_index()
    agg["random_share_of_routed"] = agg.nominations_random / (agg.nominations_agent + agg.nominations_judge + agg.nominations_random)
    agg.to_csv(RES / "table3_data_quality.csv", index=False)
    return df, agg


# ---------------------------------------------------------------- A5 efficacy
def efficacy(runs):
    rows = []
    for (cond, s), r in sorted(runs.items()):
        c = r["check"]
        collapse_cycle = r["meta"].get("collapse_cycle")
        rows.append({"condition": cond, "seed": s, "welfare": c["total_catch"],
                     # primary (user decision 9 Nov 2026): cycles completed before collapse
                     "survival_time": (collapse_cycle - 1) if collapse_cycle else len(r["cycles"]),
                     "survival_time_check_data_legacy": c["survival_time"],
                     "survived": c["survived"], "equality": c["equality"], "efficiency": c["efficiency"],
                     "overusage": c["overusage"], "mean_regen_factor": c["mean_regen_factor"],
                     "final_stock": c["final_stock"]})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "efficacy_by_run.csv", index=False)
    metrics = ["welfare", "survival_time", "survival_time_check_data_legacy", "survived", "equality", "efficiency",
               "overusage", "mean_regen_factor"]
    table = []
    for cond, sub in df.groupby("condition", sort=False):
        row = {"condition": cond, "n": len(sub)}
        for m in metrics:
            v = sub[m].astype(float).tolist()
            row[f"{m}_mean"] = float(np.mean(v))
            row[f"{m}_se"] = se(v)
            row[f"{m}_authors_se"] = authors_se(v)
        table.append(row)
    t1 = pd.DataFrame(table)
    t1.to_csv(RES / "table1_efficacy.csv", index=False)
    tests = []
    groups = [g for _, g in df.groupby("condition")]
    for m in ["welfare", "equality", "efficiency", "overusage", "survival_time"]:
        vals = [g[m].astype(float).values for g in groups]
        try:
            kw = stats.kruskal(*vals)
            kw_h, kw_p = float(kw.statistic), float(kw.pvalue)
        except ValueError:
            kw_h = kw_p = float("nan")
        an = stats.f_oneway(*vals)
        tests.append({"metric": m, "kruskal_H": kw_h, "kruskal_p": kw_p, "anova_F": float(an.statistic),
                      "anova_p": float(an.pvalue)})
    pd.DataFrame(tests).to_csv(RES / "efficacy_tests.csv", index=False)
    tuk = []
    for m in ["welfare", "equality"]:
        conds = [c for c in df.condition.unique()]
        res = stats.tukey_hsd(*[df[df.condition == c][m].astype(float).values for c in conds])
        for i, a in enumerate(conds):
            for j, b in enumerate(conds):
                if i < j:
                    tuk.append({"metric": m, "a": a, "b": b, "diff": float(res.statistic[i, j]), "p": float(res.pvalue[i, j])})
    pd.DataFrame(tuk).to_csv(RES / "efficacy_tukey.csv", index=False)
    return df, t1


# ---------------------------------------------------------------- focal catch
def focal_catch(runs):
    rows = []
    for (cond, s), r in sorted(runs.items()):
        f = focal_identity(r)
        for cy in r["cycles"]:
            catches = {c["identity"]: c["actual"] for c in cy["catches"]}
            req = {c["identity"]: c["requested"] for c in cy["catches"]}
            el = cy.get("elicitation") or {}
            for name in catches:
                lim = (el.get(name) or {}).get("preferred_limit")
                rows.append({"condition": cond, "seed": s, "cycle": cy["cycle"], "identity": name,
                             "role": "focal" if name == f else "peer", "actual": catches[name], "requested": req[name],
                             "threshold": cy["sustainability_threshold"],
                             "over_threshold": req[name] > cy["sustainability_threshold"],
                             "preferred_limit": lim if isinstance(lim, (int, float)) else None,
                             "agreed_limit": cy["agreed_limit"]})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "catch_by_agent_cycle.csv", index=False)
    summ = (df.groupby(["condition", "role", "cycle"])
            .agg(mean_catch=("actual", "mean"), mean_requested=("requested", "mean"),
                 mean_pref_limit=("preferred_limit", "mean"), threshold=("threshold", "mean"), n=("actual", "size"))
            .reset_index())
    summ.to_csv(RES / "focal_catch_by_cycle.csv", index=False)
    # run-level manipulation check: focal minus peer mean catch and preferred limit
    mc = []
    for (cond, s), sub in df[df.condition.isin(["values_N8", "stakes_N8"])].groupby(["condition", "seed"]):
        fo, pe = sub[sub.role == "focal"], sub[sub.role == "peer"]
        mc.append({"condition": cond, "seed": s, "focal_mean_catch": fo.actual.mean(), "peer_mean_catch": pe.actual.mean(),
                   "focal_mean_pref_limit": fo.preferred_limit.mean(), "peer_mean_pref_limit": pe.preferred_limit.mean()})
    mc = pd.DataFrame(mc)
    mc.to_csv(RES / "manipulation_check_catch.csv", index=False)
    return df, mc


# ---------------------------------------------------------------- peer nominations (A5)
def peer_nominations(runs):
    rows, chi = [], []
    for (cond, s), r in sorted(runs.items()):
        if cond == "replica_N8":
            continue
        f = focal_identity(r)
        for cy in r["cycles"]:
            pl = cy.get("perceived_leadership") or {}
            votes = Counter(v["resolved_identity"] for v in pl.values())
            for name in present(cy):
                rows.append({"condition": cond, "seed": s, "cycle": cy["cycle"], "identity": name,
                             "slot": next(c["slot"] for c in cy["catches"] if c["identity"] == name),
                             "role": "focal" if name == f else "peer", "votes": votes.get(name, 0),
                             "self_vote": int((pl.get(name) or {}).get("resolved_identity") == name),
                             "no_one_votes_in_cycle": votes.get("no one", 0), "voters": len(pl)})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "peer_nominations_by_agent_cycle.csv", index=False)
    for cond, sub in df.groupby("condition"):
        by_slot = sub.groupby("slot").votes.sum()
        res = stats.chisquare(by_slot.values)
        named = sub.votes.sum()
        chi.append({"condition": cond, "named_votes": int(named),
                    "no_one_share": float(sub.groupby(["seed", "cycle"]).no_one_votes_in_cycle.first().sum()
                                          / sub.groupby(["seed", "cycle"]).voters.first().sum()),
                    "chi2_uniform_by_slot": float(res.statistic), "chi2_p": float(res.pvalue),
                    "focal_share": float(sub[sub.role == "focal"].votes.sum() / named) if (sub.role == "focal").any() else None,
                    "chance_share": 1 / sub.groupby(["seed", "cycle"]).size().iloc[0],
                    "top_agent_share_mean": float(sub.groupby(["seed", "cycle"]).votes.max().sum() / named)})
    pd.DataFrame(chi).to_csv(RES / "peer_nominations_tests.csv", index=False)
    return df


def peer_focal_test(peer_df, cent_df):
    """Exploratory: focal percentile rank in total peer votes per run, exact stratified
    enumeration (same logic as H1); plus per-run Spearman agreement of votes with
    run-level in-degree and adoption credit."""
    out, agree = {}, []
    for cond in ("values_N8", "stakes_N8", "baseline_N8"):
        sub = peer_df[peer_df.condition == cond]
        ranks, obs = [], []
        for s, rs in sub.groupby("seed"):
            v = rs.groupby("slot").votes.sum().to_dict()  # households/slots (stakes successors share a slot)
            pr = M.percentile_ranks(v)
            ranks.append(list(pr.values()))
            if cond != "baseline_N8":
                obs.append(pr[s % 8])
            deg = (cent_df[(cent_df.condition == cond) & (cent_df.seed == s) & (cent_df.phase == "whole")
                           & (cent_df.routing == "primary")].groupby("identity").in_degree.sum())
            vid = rs.groupby("identity").votes.sum()
            common = vid.index.intersection(deg.index)
            rho = stats.spearmanr(vid[common], deg[common]).statistic
            agree.append({"condition": cond, "seed": s, "spearman_votes_vs_in_degree": float(rho)})
        if obs:
            stat = float(np.mean(obs))
            p, n = M.exact_stratified_p(ranks, stat)
            out[cond] = {"focal_pct_votes_mean": stat, "p_exact_one_sided": p, "assignments": n,
                         "per_run_focal_pct": obs, "label": "exploratory"}
    pd.DataFrame(agree).to_csv(RES / "peer_votes_vs_centrality_spearman.csv", index=False)
    return out, pd.DataFrame(agree)


# ---------------------------------------------------------------- graph measures (B2)
def cycle_graph_rows(runs):
    rows = []
    for (cond, s), r in sorted(runs.items()):
        f = focal_identity(r)
        for cy in r["cycles"]:
            names = present(cy)
            turns = cycle_turns(r, cy["cycle"])
            opener = turns[0]["speaker_identity"] if turns else None
            for phase in PHASES:
                pt = M.phase_turns(turns, phase)
                for routing in M.ROUTING:
                    g = M.build_graph(names, pt, routing)
                    deg = M.in_degree(g)
                    bet = M.betweenness(g)
                    eig, reason = M.eigenvector(g)
                    pct = M.percentile_ranks(deg)
                    air = Counter(t["speaker_identity"] for t in pt)
                    for n in names:
                        rows.append({"condition": cond, "seed": s, "cycle": cy["cycle"], "phase": phase, "routing": routing,
                                     "identity": n, "role": "focal" if n == f else "peer", "focal_opened": opener == f if f else None,
                                     "in_degree": deg[n], "in_degree_pct": pct[n], "betweenness": bet[n],
                                     "eigenvector": eig[n] if eig else None, "eigen_reason": reason,
                                     "airtime": air.get(n, 0), "self_nominations": g.graph["self_nominations"],
                                     "self_mentions": g.graph["self_mentions"]})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "centrality_by_agent_cycle.csv", index=False)
    return df


def run_level_graph(r, routing="primary", exclude_focal_opened=False, phase="whole"):
    f = focal_identity(r)
    names = present(r["cycles"][0])
    turns = []
    for cy in r["cycles"]:
        ct = cycle_turns(r, cy["cycle"])
        if exclude_focal_opened and ct and ct[0]["speaker_identity"] == f:
            continue
        turns += M.phase_turns(ct, phase)
    return M.build_graph(names, turns, routing)


# ---------------------------------------------------------------- H1 values
def h1(runs, exclude_opened=False, routing="primary", use_pagerank=False):
    vals = [runs[("values_N8", s)] for s in SEEDS if ("values_N8", s) in runs]
    a_ranks, e_ranks, a_obs, e_obs, detail = [], [], [], [], []
    for r in vals:
        f = focal_identity(r)
        names = present(r["cycles"][0])
        credit, defined = defaultdict(float), 0
        for cy in r["cycles"]:
            ct = cycle_turns(r, cy["cycle"])
            if exclude_opened and ct and ct[0]["speaker_identity"] == f:
                continue
            limits = {n: (cy["elicitation"].get(n) or {}).get("preferred_limit") for n in names}
            ad = M.adoption(limits, cy["agreed_limit"])
            if ad is None:
                continue
            defined += 1
            for n in names:
                credit[n] += ad[n]
        rate = {n: credit[n] / defined for n in names} if defined else None
        g = run_level_graph(r, routing, exclude_opened)
        if use_pagerank:
            eig, reason = M.pagerank(g), None
        else:
            eig, reason = M.eigenvector(g)
        row = {"seed": r["meta"]["seed"], "focal": f, "cycles_with_agreement": defined, "eigen_reason": reason}
        if rate:
            pr = M.percentile_ranks(rate)
            a_ranks.append(list(pr.values()))
            a_obs.append(pr[f])
            row.update(focal_adoption_rate=rate[f], peer_mean_adoption_rate=float(np.mean([rate[n] for n in names if n != f])),
                       focal_adoption_pct=pr[f])
        if eig:
            pr = M.percentile_ranks(eig)
            e_ranks.append(list(pr.values()))
            e_obs.append(pr[f])
            row.update(focal_eigen=eig[f], peer_mean_eigen=float(np.mean([eig[n] for n in names if n != f])),
                       focal_eigen_pct=pr[f])
        detail.append(row)
    out = {}
    for name, ranks, obs in (("H1a_adoption", a_ranks, a_obs), ("H1b_eigenvector", e_ranks, e_obs)):
        if ranks:
            stat = float(np.mean(obs))
            p, n_assign = M.exact_stratified_p(ranks, stat)
            out[name] = {"statistic": stat, "p": p, "assignments": n_assign, "runs_used": len(ranks),
                         "effect": stat - 0.5, "ci": boot_ci(obs, name, "values_N8")}
        else:
            out[name] = {"statistic": None, "p": None, "runs_used": 0}
    out["H1b_eigenvector"]["runs_undefined"] = len(vals) - len(e_ranks)
    return out, pd.DataFrame(detail)


# ---------------------------------------------------------------- H2 stakes
def h2(runs, exclude_opened=False, routing="primary", measure="in_degree"):
    strata, obs, detail = [], [], []
    for s in SEEDS:
        r = runs.get(("stakes_N8", s))
        if r is None:
            continue
        f = focal_identity(r)
        for cy in r["cycles"]:
            ct = cycle_turns(r, cy["cycle"])
            if exclude_opened and ct and ct[0]["speaker_identity"] == f:
                continue
            names = present(cy)
            g = M.build_graph(names, ct, routing)
            if measure == "in_degree":
                v = M.in_degree(g)
            elif measure == "betweenness":
                v = M.betweenness(g)
            else:
                v, _ = M.eigenvector(g)
                if v is None:
                    continue
            pr = M.percentile_ranks(v)
            strata.append(np.array(list(pr.values())))
            obs.append(pr[f])
            detail.append({"seed": s, "cycle": cy["cycle"], "focal": f, "focal_value": v[f],
                           "peer_mean": float(np.mean([v[n] for n in names if n != f])), "focal_pct": pr[f]})
    if not strata:
        return {"statistic": None}, pd.DataFrame(detail)
    stat = float(np.mean(obs))
    key = f"analysis|perm|H2|0" + ("" if (routing, measure, exclude_opened) == ("primary", "in_degree", False)
                                    else f"|{routing}|{measure}|excl{int(exclude_opened)}")
    rng = KEYS.rng(key, H2_DRAWS * len(strata))
    sims = np.zeros(H2_DRAWS)
    for st in strata:
        sims += st[rng.integers(len(st), size=H2_DRAWS)]
    sims /= len(strata)
    p = float((np.sum(sims >= stat - 1e-12) + 1) / (H2_DRAWS + 1))
    runs_used = len({d["seed"] for d in detail})
    per_run = pd.DataFrame(detail).groupby("seed").focal_pct.mean().tolist()
    return {"statistic": stat, "p": p, "cycles_used": len(strata), "runs_used": runs_used, "effect": stat - 0.5,
            "ci": boot_ci(per_run, f"H2_{measure}_{routing}", "stakes_N8"), "key": key}, pd.DataFrame(detail)


# ---------------------------------------------------------------- H3 coordination
def h3_cycle_table(runs, conds=("replica_N8", "baseline_N8", "coord_N16", "coord_N32")):
    rows = []
    for (cond, s), r in sorted(runs.items()):
        if cond not in conds:
            continue
        for cy in r["cycles"]:
            names = present(cy)
            ct = cycle_turns(r, cy["cycle"])
            for phase in PHASES:
                pt = M.phase_turns(ct, phase)
                air = Counter(t["speaker_identity"] for t in pt)
                obs_air = M.gini([air.get(n, 0) for n in names])
                ka = f"analysis|null|airtime|{cond}|{s}|{cy['cycle']}|{phase}"
                null_air = M.airtime_null(names, ct, phase, KEYS.rng(ka, NULL_DRAWS), NULL_DRAWS)
                row = {"condition": cond, "N": len(names), "seed": s, "cycle": cy["cycle"], "phase": phase,
                       "utterances": len(pt), "silent_share": sum(air.get(n, 0) == 0 for n in names) / len(names),
                       "airtime_gini": obs_air, "airtime_null_mean": float(np.nanmean(null_air)),
                       "airtime_z": M.standardized(obs_air, null_air)}
                for routing in M.ROUTING:
                    g = M.build_graph(names, pt, routing)
                    obs_inf = M.gini(M.in_degree(g).values())
                    ki = f"analysis|null|influence|{cond}|{s}|{cy['cycle']}|{phase}" + ("" if routing == "primary" else f"|{routing}")
                    null_inf = M.influence_null(names, pt, KEYS.rng(ki, NULL_DRAWS), NULL_DRAWS, routing)
                    row[f"influence_gini_{routing}"] = obs_inf
                    row[f"influence_null_mean_{routing}"] = float(np.nanmean(null_inf)) if np.isfinite(null_inf).any() else None
                    row[f"influence_z_{routing}"] = M.standardized(obs_inf, null_inf)
                rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "h3_standardized_gini_by_cycle.csv", index=False)
    return df


def h3_test(df, column, phase, measure_name):
    sub = df[(df.phase == phase)]
    run = sub.groupby(["condition", "N", "seed"])[column].mean().reset_index()
    n8 = run[run.condition == "baseline_N8"][column].dropna().values
    n16 = run[run.condition == "coord_N16"][column].dropna().values
    n32 = run[run.condition == "coord_N32"][column].dropna().values
    undefined_cycles = int(sub[sub.condition.isin(["baseline_N8", "coord_N16", "coord_N32"])][column].isna().sum())
    if len(n32):
        stat, p, n_assign = M.jt_exact([n8, n16, n32])
        rng = KEYS.rng(f"analysis|boot|{measure_name}|N32_minus_N8", BOOT)
        diffs = n32[rng.integers(len(n32), size=(BOOT, len(n32)))].mean(1) - n8[rng.integers(len(n8), size=(BOOT, len(n8)))].mean(1)
        return {"statistic": stat, "p": p, "method": f"exact Jonckheere-Terpstra N8<N16<N32 ({n_assign} assignments)",
                "N8_mean_z": float(n8.mean()), "N16_mean_z": float(n16.mean()), "N32_mean_z": float(n32.mean()),
                "effect": float(n32.mean() - n8.mean()), "effect_label": "N32 minus N8 mean z",
                "ci": tuple(map(float, np.percentile(diffs, [2.5, 97.5]))), "runs_N8": len(n8), "runs_N16": len(n16),
                "runs_N32": len(n32), "undefined_cycles": undefined_cycles}, run
    res = stats.mannwhitneyu(n16, n8, alternative="greater", method="exact")
    rng = KEYS.rng(f"analysis|boot|{measure_name}|N16_minus_N8", BOOT)
    diffs = n16[rng.integers(len(n16), size=(BOOT, len(n16)))].mean(1) - n8[rng.integers(len(n8), size=(BOOT, len(n8)))].mean(1)
    return {"statistic": float(res.statistic), "p": float(res.pvalue), "method": "exact Mann-Whitney N16>N8 (trend untested)",
            "N8_mean_z": float(n8.mean()), "N16_mean_z": float(n16.mean()), "effect": float(n16.mean() - n8.mean()),
            "ci": tuple(map(float, np.percentile(diffs, [2.5, 97.5]))), "runs_N8": len(n8), "runs_N16": len(n16),
            "undefined_cycles": undefined_cycles}, run


# ---------------------------------------------------------------- matched-slot contrast
def matched_slot(runs, peer_df, cent_df):
    rows = []
    for cond in ("values_N8", "stakes_N8"):
        for s in SEEDS:
            if (cond, s) not in runs or ("baseline_N8", s) not in runs:
                continue
            slot = s % 8
            for arm in (cond, "baseline_N8"):
                pn = peer_df[(peer_df.condition == arm) & (peer_df.seed == s)]
                share = pn[pn.slot == slot].votes.sum() / max(1, pn.votes.sum())
                cd = cent_df[(cent_df.condition == arm) & (cent_df.seed == s) & (cent_df.phase == "whole")
                             & (cent_df.routing == "primary")]
                ident = {r["identity"]: c["slot"] for r in [None] for c in []}
                slot_ids = {c["identity"] for cy in runs[(arm, s)]["cycles"] for c in cy["catches"] if c["slot"] == slot}
                pct = cd[cd.identity.isin(slot_ids)].in_degree_pct.mean()
                rows.append({"contrast": cond, "seed": s, "arm": "intervention" if arm == cond else "baseline",
                             "slot": slot, "peer_nom_share": share, "in_degree_pct": pct})
    df = pd.DataFrame(rows)
    out = []
    for cond, sub in df.groupby("contrast"):
        w = sub.pivot(index="seed", columns="arm")
        for m in ("peer_nom_share", "in_degree_pct"):
            d = (w[m]["intervention"] - w[m]["baseline"]).values
            p = float(stats.wilcoxon(d, alternative="two-sided").pvalue) if np.any(d != 0) else 1.0
            out.append({"contrast": cond, "measure": m, "pairs": len(d), "mean_diff": float(d.mean()),
                        "wilcoxon_p_two_sided": p})
    df.to_csv(RES / "matched_slot_by_seed.csv", index=False)
    pd.DataFrame(out).to_csv(RES / "matched_slot_tests.csv", index=False)
    return pd.DataFrame(out)


# ---------------------------------------------------------------- convergence and speaking order
def convergence(runs):
    rows = []
    for (cond, s), r in sorted(runs.items()):
        if cond == "replica_N8":
            continue
        cyc = r["cycles"]
        for i, cy in enumerate(cyc):
            el = cy["elicitation"]
            plans = [v["plan"] for v in el.values() if isinstance(v.get("plan"), (int, float))]
            lims = [v["preferred_limit"] for v in el.values() if isinstance(v.get("preferred_limit"), (int, float))]
            nxt = [c["actual"] for c in cyc[i + 1]["catches"]] if i + 1 < len(cyc) else []
            agreed = cy["agreed_limit"]
            rows.append({"condition": cond, "seed": s, "cycle": cy["cycle"],
                         "plan_sd": np.std(plans, ddof=1) if len(plans) > 1 else None,
                         "plan_iqr": stats.iqr(plans) if plans else None,
                         "limit_sd": np.std(lims, ddof=1) if len(lims) > 1 else None,
                         "limit_iqr": stats.iqr(lims) if lims else None,
                         "next_catch_sd": np.std(nxt, ddof=1) if len(nxt) > 1 else None,
                         "limit_mean_abs_dist_to_agreed": float(np.mean([abs(l - agreed) for l in lims]))
                         if lims and isinstance(agreed, (int, float)) else None,
                         "agreed_limit": agreed})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "opinion_convergence_by_cycle.csv", index=False)
    summ = df.groupby("condition")[["plan_sd", "limit_sd", "next_catch_sd", "limit_mean_abs_dist_to_agreed"]].mean()
    summ.to_csv(RES / "opinion_convergence_summary.csv")
    return summ


def speaking_order(runs):
    """Distance from agreed limit to the opener's elicited limit vs a uniformly permuted position."""
    out = []
    for cond in ("baseline_N8", "values_N8", "stakes_N8", "coord_N16"):
        obs_d, sims = [], np.zeros(NULL_DRAWS)
        for s in SEEDS:
            r = runs.get((cond, s))
            if r is None:
                continue
            for cy in r["cycles"]:
                ag = cy["agreed_limit"]
                if not isinstance(ag, (int, float)):
                    continue
                ct = cycle_turns(r, cy["cycle"])
                dist = {n: abs(v["preferred_limit"] - ag) for n, v in cy["elicitation"].items()
                        if isinstance(v.get("preferred_limit"), (int, float))}
                op = ct[0]["speaker_identity"]
                if op not in dist:
                    continue
                obs_d.append(dist[op])
                vals = np.array(list(dist.values()))
                rng = KEYS.rng(f"analysis|perm|order|{cond}|{s}|{cy['cycle']}", NULL_DRAWS)
                sims += vals[rng.integers(len(vals), size=NULL_DRAWS)]
        if not obs_d:
            continue
        sims /= len(obs_d)
        stat = float(np.mean(obs_d))
        out.append({"condition": cond, "cycles": len(obs_d), "opener_mean_distance": stat,
                    "null_mean_distance": float(sims.mean()),
                    "p_one_sided_closer": float((np.sum(sims <= stat + 1e-12) + 1) / (NULL_DRAWS + 1))})
    df = pd.DataFrame(out)
    df.to_csv(RES / "speaking_order_opener.csv", index=False)
    return df


# ---------------------------------------------------------------- B5.6 parity with check_data
def parity(runs, cent_df):
    """Compare B2 degree (primary routing) with check_data's stored per-cycle degree."""
    rows = []
    for (cond, s), r in sorted(runs.items()):
        for cyc_chk in r["check"]["cycles"]:
            c = cyc_chk["cycle"]
            mine = cent_df[(cent_df.condition == cond) & (cent_df.seed == s) & (cent_df.cycle == c)
                           & (cent_df.phase == "whole") & (cent_df.routing == "primary")].set_index("identity")
            theirs = cyc_chk["centrality"]["degree"]
            diff = sum(abs(mine.in_degree[n] - theirs[n]) for n in theirs)
            eig_mine = mine.eigen_reason.iloc[0] is None or pd.isna(mine.eigen_reason.iloc[0])
            rows.append({"condition": cond, "seed": s, "cycle": c, "degree_abs_diff_total": diff,
                         "degree_equal": diff < 1e-9,
                         "eigen_defined_B2": bool(eig_mine),
                         "eigen_defined_check_data": cyc_chk["centrality"]["eigenvector_status"] == "ok",
                         "deg_gini_check_data": cyc_chk["centrality"]["gini"]["degree"]})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "parity_check_data_vs_B2.csv", index=False)
    return df


# ---------------------------------------------------------------- figures
def figures(runs, focal_df, peer_df, h3_df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"replica_N8": "#7f7f7f", "baseline_N8": "#1f77b4", "values_N8": "#2ca02c", "stakes_N8": "#d62728",
              "coord_N16": "#9467bd", "coord_N32": "#8c564b"}
    # stock trajectories (fraction of capacity)
    conds = [c for c in CONDITIONS if any(k[0] == c for k in runs)]
    fig, axes = plt.subplots(1, len(conds), figsize=(3.2 * len(conds), 3), sharey=True)
    for ax, cond in zip(axes, conds):
        for s in SEEDS:
            r = runs.get((cond, s))
            if not r:
                continue
            cap = r["meta"]["resolved_config"]["experiment"]["env"]["initial_resource_in_pool"]
            ys = [r["cycles"][0]["stock_before_harvest"] / cap] + [cy["stock_after_harvest"] / cap for cy in r["cycles"]]
            ax.plot(range(len(ys)), ys, marker="o", ms=3, color=colors[cond], alpha=.7)
        ax.axhline(0.05, ls=":", color="k", lw=.8)
        ax.set_title(cond, fontsize=9)
        ax.set_xlabel("cycle (post-harvest)")
    axes[0].set_ylabel("stock / capacity")
    fig.tight_layout()
    fig.savefig(FIG / "stock_trajectories.png", dpi=150)
    plt.close(fig)

    # focal vs peer catch
    fig, axes = plt.subplots(1, 2, figsize=(8, 3), sharey=True)
    for ax, cond in zip(axes, ("values_N8", "stakes_N8")):
        sub = focal_df[focal_df.condition == cond]
        for role, ls in (("focal", "-"), ("peer", "--")):
            m = sub[sub.role == role].groupby("cycle").actual.mean()
            ax.plot(m.index, m.values, ls, marker="o", label=role, color=colors[cond])
        th = sub.groupby("cycle").threshold.mean()
        ax.plot(th.index, th.values, ":", color="k", label="threshold (mean)")
        ax.set_title(cond)
        ax.set_xlabel("cycle")
        ax.legend(fontsize=8)
    axes[0].set_ylabel("actual catch (tons)")
    fig.tight_layout()
    fig.savefig(FIG / "focal_vs_peer_catch.png", dpi=150)
    plt.close(fig)

    # peer nomination heatmap: share of named votes to focal by seed x cycle
    fig, axes = plt.subplots(1, 2, figsize=(8, 3))
    for ax, cond in zip(axes, ("values_N8", "stakes_N8")):
        sub = peer_df[peer_df.condition == cond]
        tot = sub.groupby(["seed", "cycle"]).votes.sum()
        foc = sub[sub.role == "focal"].groupby(["seed", "cycle"]).votes.sum()
        mat = (foc / tot.replace(0, np.nan)).unstack()
        im = ax.imshow(mat.values, vmin=0, vmax=1, cmap="viridis", aspect="auto")
        ax.set_xticks(range(mat.shape[1]), mat.columns)
        ax.set_yticks(range(mat.shape[0]), [f"seed {i}" for i in mat.index])
        ax.set_title(f"{cond}: focal share of named votes", fontsize=9)
        ax.set_xlabel("cycle")
        for (i, j), v in np.ndenumerate(mat.values):
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7, color="w" if v < .6 else "k")
    fig.colorbar(im, ax=axes, shrink=.8)
    fig.savefig(FIG / "peer_nomination_focal_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # standardized Gini vs N per phase
    fig, axes = plt.subplots(1, 2, figsize=(8, 3))
    for ax, col, title in ((axes[0], "airtime_z", "airtime"), (axes[1], "influence_z_primary", "influence (in-degree)")):
        for i, phase in enumerate(PHASES):
            run = h3_df[h3_df.phase == phase].groupby(["condition", "N", "seed"])[col].mean().reset_index()
            run = run[run.condition != "replica_N8"]
            ax.scatter(run.N + (i - 1) * 1.2, run[col], label=phase, s=18)
        ax.axhline(0, color="k", lw=.6)
        ax.set_xticks(sorted(run.N.unique()))
        ax.set_xlabel("N")
        ax.set_title(f"standardized Gini: {title}", fontsize=9)
    axes[0].set_ylabel("run mean z")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "standardized_gini_vs_N.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- main
def main():
    runs, missing = validated_runs()
    pd.DataFrame(missing, columns=["condition", "seed", "reason"]).to_csv(RES / "missing_runs.csv", index=False)
    summary = {"validated_runs": sorted(f"{c}/seed{s}" for c, s in runs), "missing": missing}

    summary["B1_regression"] = regression(runs)
    if not summary["B1_regression"]["matches_REPLICA_CHECK"]:
        (RES / "phase1_summary.json").write_text(json.dumps(summary, indent=1, default=str))
        raise SystemExit("STOP: B1 regression does not reproduce REPLICA_CHECK.md")

    _, dq = data_quality(runs)
    eff, t1 = efficacy(runs)
    focal_df, mc = focal_catch(runs)
    peer_df = peer_nominations(runs)
    cent_df = cycle_graph_rows(runs)
    summary["parity"] = parity(runs, cent_df)[["degree_equal", "eigen_defined_B2", "eigen_defined_check_data"]].mean().to_dict()

    primary = {}
    h1_res, h1_detail = h1(runs)
    h1_detail.to_csv(RES / "h1_values_by_run.csv", index=False)
    primary.update(h1_res)
    h2_res, h2_detail = h2(runs)
    h2_detail.to_csv(RES / "h2_stakes_by_cycle.csv", index=False)
    primary["H2_in_degree"] = h2_res
    h3_df = h3_cycle_table(runs)
    primary["H3a_airtime"], run_air = h3_test(h3_df, "airtime_z", "nomination", "H3a")
    # H3b phase = nomination (user decision 9 Nov 2026); other phases are sensitivity only
    primary["H3b_influence"], run_inf = h3_test(h3_df, "influence_z_primary", "nomination", "H3b")
    order = ["H1a_adoption", "H1b_eigenvector", "H2_in_degree", "H3a_airtime", "H3b_influence"]
    adj = M.holm([primary[k]["p"] for k in order])
    for k, a in zip(order, adj):
        primary[k]["p_holm"] = a
    t2 = pd.DataFrame([{"test": k, **{kk: (str(v) if isinstance(v, tuple) else v) for kk, v in primary[k].items()}} for k in order])
    t2.to_csv(RES / "table2_primary_tests.csv", index=False)
    summary["primary"] = primary

    sens = {}
    sens["H1_opener_excluded"] = h1(runs, exclude_opened=True)[0]
    sens["H1b_pagerank_DEVIATION"] = h1(runs, use_pagerank=True)[0]["H1b_eigenvector"]
    for routing in ("sens_judge", "sens_random"):
        sens[f"H1b_{routing}"] = h1(runs, routing=routing)[0]["H1b_eigenvector"]
        sens[f"H2_{routing}"] = h2(runs, routing=routing)[0]
        sens[f"H3b_{routing}"] = h3_test(h3_df, f"influence_z_{routing}", "nomination", f"H3b_{routing}")[0]
    sens["H2_opener_excluded"] = h2(runs, exclude_opened=True)[0]
    sens["H2_betweenness"] = h2(runs, measure="betweenness")[0]
    sens["H2_eigenvector"] = h2(runs, measure="eigenvector")[0]
    for phase in ("whole", "opening"):
        sens[f"H3b_{phase}_phase"] = h3_test(h3_df, "influence_z_primary", phase, f"H3b_{phase}")[0]
    sens["H3a_whole_phase"] = h3_test(h3_df, "airtime_z", "whole", "H3a_whole")[0]
    summary["sensitivity"] = sens

    pf, agree = peer_focal_test(peer_df, cent_df)
    summary["peer_nomination_focal_exploratory"] = pf
    summary["peer_votes_vs_in_degree_spearman_mean"] = agree.groupby("condition").spearman_votes_vs_in_degree.mean().to_dict()
    summary["matched_slot"] = matched_slot(runs, peer_df, cent_df).to_dict("records")
    summary["convergence"] = convergence(runs).reset_index().to_dict("records")
    summary["speaking_order"] = speaking_order(runs).to_dict("records")
    figures(runs, focal_df, peer_df, h3_df)
    KEYS.dump(HERE / "keys_used.json")
    (RES / "phase1_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps({k: summary[k] for k in ("B1_regression", "parity")}, indent=1, default=str))


if __name__ == "__main__":
    main()
