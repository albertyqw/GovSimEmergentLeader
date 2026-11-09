"""Remaining free secondary analyses (ANALYSIS_PLAN A5) on all validated v3 runs.

Run after phase1.py (reads its centrality and peer-nomination CSVs). From the folder that contains analysis/ (repo root):
  PYTHONDONTWRITEBYTECODE=1 python3 analysis/secondary.py
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
import proposals as P  # noqa: E402
import phase1 as P1  # noqa: E402  (reuse loaders and helpers; importing does not run main)

RES, FIG, KEYS = P1.RES, P1.FIG, P1.KEYS
N8_INSTRUMENTED = ["baseline_N8", "values_N8", "stakes_N8"]


# ---------------------------------------------------------------- originator adoption (A5; exploratory)
def originator(runs):
    rows, cyc_rows = [], []
    for (cond, s), r in sorted(runs.items()):
        f = P1.focal_identity(r)
        for cy in r["cycles"]:
            names = P1.present(cy)
            firsts = {}
            for t in P1.cycle_turns(r, cy["cycle"]):
                v = P.first_proposal(t["text"])
                if v is not None and t["speaker_identity"] not in firsts:
                    firsts[t["speaker_identity"]] = (t["position"], v)
            credit = M.originator({n: firsts.get(n, (None, None)) if n in firsts else (10 ** 6, None) for n in names},
                                  cy["agreed_limit"])
            first_any = min(firsts.values())[1] if firsts else None
            cyc_rows.append({"condition": cond, "seed": s, "cycle": cy["cycle"], "agreed": cy["agreed_limit"],
                             "proposers": len(firsts), "first_proposal_value": first_any,
                             "agreed_matches_any_proposal": credit is not None and any(v > 0 for v in credit.values()),
                             "originator": (max(credit, key=credit.get) if credit and any(credit.values()) else None)})
            if credit is None:
                continue
            for n in names:
                rows.append({"condition": cond, "seed": s, "cycle": cy["cycle"], "identity": n,
                             "role": "focal" if n == f else "peer", "originator_credit": credit[n],
                             "proposed": n in firsts})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "originator_adoption_by_agent_cycle.csv", index=False)
    cdf = pd.DataFrame(cyc_rows)
    cdf.to_csv(RES / "originator_by_cycle.csv", index=False)
    out = {}
    for cond in ("values_N8", "stakes_N8"):
        sub = df[df.condition == cond]
        ranks, obs, per = [], [], []
        for s, rs in sub.groupby("seed"):
            if cond == "stakes_N8":  # slots (households) for stakes; identities for values
                slot = {c["identity"]: c["slot"] for cy in runs[(cond, s)]["cycles"] for c in cy["catches"]}
                v = rs.assign(slot=rs.identity.map(slot)).groupby("slot").originator_credit.mean().to_dict()
                key = s % 8
            else:
                v = rs.groupby("identity").originator_credit.mean().to_dict()
                key = P1.focal_identity(runs[(cond, s)])
            pr = M.percentile_ranks(v)
            ranks.append(list(pr.values()))
            obs.append(pr[key])
            per.append({"seed": int(s), "focal_rate": v[key], "peer_mean_rate": float(np.mean([x for k, x in v.items() if k != key])),
                        "focal_pct": pr[key]})
        stat = float(np.mean(obs))
        p, n = M.exact_stratified_p(ranks, stat)
        out[cond] = {"focal_pct_mean": stat, "p_exact_one_sided": p, "assignments": n, "per_run": per,
                     "label": "exploratory; extractor hold-out error 19/100"}
    summ = cdf.groupby("condition").agg(cycles=("cycle", "size"),
                                        agreed_matches_some_proposal=("agreed_matches_any_proposal", "mean"),
                                        mean_proposers=("proposers", "mean")).reset_index()
    summ.to_csv(RES / "originator_summary.csv", index=False)
    return out, cdf


def first_proposer_order(runs):
    """Speaking order (A5): distance of agreed limit to the first proposer's number vs a uniformly
    chosen proposer in the same cycle. Key: analysis|perm|order|{condition}|{seed}|{cycle}|first_proposer."""
    out = []
    for cond in P1.CONDITIONS:
        obs, sims = [], np.zeros(P1.NULL_DRAWS)
        for s in P1.SEEDS:
            r = runs.get((cond, s))
            if r is None:
                continue
            for cy in r["cycles"]:
                ag = cy["agreed_limit"]
                if not isinstance(ag, (int, float)):
                    continue
                firsts = {}
                for t in P1.cycle_turns(r, cy["cycle"]):
                    v = P.first_proposal(t["text"])
                    if v is not None and t["speaker_identity"] not in firsts:
                        firsts[t["speaker_identity"]] = (t["position"], v)
                if len(firsts) < 2:
                    continue
                vals = np.array([abs(v - ag) for _, v in firsts.values()])
                obs.append(abs(min(firsts.values())[1] - ag))
                rng = KEYS.rng(f"analysis|perm|order|{cond}|{s}|{cy['cycle']}|first_proposer", P1.NULL_DRAWS)
                sims += vals[rng.integers(len(vals), size=P1.NULL_DRAWS)]
        if obs:
            sims /= len(obs)
            stat = float(np.mean(obs))
            out.append({"condition": cond, "cycles": len(obs), "first_proposer_mean_distance": stat,
                        "null_mean_distance": float(sims.mean()),
                        "p_one_sided_closer": float((np.sum(sims <= stat + 1e-12) + 1) / (P1.NULL_DRAWS + 1))})
    df = pd.DataFrame(out)
    df.to_csv(RES / "speaking_order_first_proposer.csv", index=False)
    return df


# ---------------------------------------------------------------- institutional memory (A5)
def institutional_memory(runs):
    """Name-mention proxy: CHAT memories are framework conversation summaries and THOUGHT memories
    are the agent's own notes, so the stored source field cannot attribute others' statements.
    For every retrieved CHAT/THOUGHT memory, count which other present agents it names."""
    rows = []
    for (cond, s), r in sorted(runs.items()):
        f = P1.focal_identity(r)
        present_by_cycle = {cy["cycle"]: P1.present(cy) for cy in r["cycles"]}
        everyone = sorted({n for v in present_by_cycle.values() for n in v})
        join = {a["identity"]: a["join_cycle"] for a in r["agents"]}
        for call in M.load_calls(r["path"]):
            me = call.get("agent_identity")
            if call["call_type"] not in ("harvest", "utterance", "elicitation") or me not in join:
                continue
            for mem in call["retrieved_memories"]:
                if mem["type"] not in ("CHAT", "THOUGHT"):
                    continue
                named = M.mentioned_set(mem["text"], everyone) - {me}
                rows.append({"condition": cond, "seed": s, "cycle": call["cycle"], "retriever": me,
                             "retriever_join_cycle": join[me], "memory_type": mem["type"],
                             "memory_creation_cycle": mem["creation_cycle"],
                             "names_focal": int(f in named) if f else None, "n_named": len(named),
                             "named": "|".join(sorted(named))})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "memory_retrieval_mentions.csv.gz", index=False, compression="gzip")
    out = []
    for (cond, s), sub in df.groupby(["condition", "seed"]):
        r = runs[(cond, s)]
        f = P1.focal_identity(r)
        counts = Counter(n for x in sub.named if x for n in x.split("|"))
        total = len(sub)
        names = sorted({n for cy in r["cycles"] for n in P1.present(cy)})
        share = {n: counts.get(n, 0) / total for n in names}
        row = {"condition": cond, "seed": s, "retrieved_chat_thought": total,
               "share_naming_any_other": float((sub.n_named > 0).mean()),
               "top_named_agent": max(share, key=share.get), "top_share": max(share.values()),
               "gini_of_name_shares": M.gini(share.values())}
        if f:
            row.update(focal_share=share[f], peer_mean_share=float(np.mean([v for k, v in share.items() if k != f])),
                       focal_pct=M.percentile_ranks(share)[f])
        if cond == "stakes_N8":
            succ = sub[sub.retriever_join_cycle > 1]
            row["successor_retrievals"] = len(succ)
            row["successor_share_naming_16mo"] = float(succ.names_focal.mean()) if len(succ) else None
            # compare with incumbents present when the successor joined (excluding the 16-month agent)
            inc = [n for n in P1.present(r["cycles"][0]) if n != f]
            row["successor_share_naming_mean_other_original"] = float(np.mean(
                [succ.named.fillna("").str.contains(rf"(?:^|\|){n}(?:\||$)").mean() for n in inc])) if len(succ) else None
        out.append(row)
    res = pd.DataFrame(out)
    res.to_csv(RES / "institutional_memory_by_run.csv", index=False)
    return res


# ---------------------------------------------------------------- stakes handoffs, numeric (A5)
def stakes_handoffs(runs):
    rows = []
    for s in P1.SEEDS:
        r = runs.get(("stakes_N8", s))
        if r is None:
            continue
        for cy in r["cycles"]:
            for c in cy["catches"]:
                if c["months_remaining"] == 1:
                    earlier = [x["actual"] for y in r["cycles"] if y["cycle"] < cy["cycle"]
                               for x in y["catches"] if x["identity"] == c["identity"]]
                    peers = [x["actual"] for x in cy["catches"] if x["identity"] != c["identity"]]
                    rows.append({"seed": s, "cycle": cy["cycle"], "identity": c["identity"], "slot": c["slot"],
                                 "final_month_catch": c["actual"], "final_month_requested": c["requested"],
                                 "own_earlier_mean": float(np.mean(earlier)) if earlier else None,
                                 "same_cycle_peer_mean": float(np.mean(peers)),
                                 "threshold": cy["sustainability_threshold"]})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "stakes_final_month_catch.csv", index=False)
    paired = df.dropna(subset=["own_earlier_mean"])
    d1 = (paired.final_month_catch - paired.own_earlier_mean).values
    d2 = (df.final_month_catch - df.same_cycle_peer_mean).values
    out = {"leavers": len(df), "with_earlier_months": len(paired),
           "mean_final_minus_own_earlier": float(d1.mean()),
           "wilcoxon_p_vs_own_earlier": float(stats.wilcoxon(d1).pvalue) if np.any(d1 != 0) else 1.0,
           "mean_final_minus_peers_same_cycle": float(d2.mean()),
           "wilcoxon_p_vs_peers": float(stats.wilcoxon(d2).pvalue) if np.any(d2 != 0) else 1.0,
           "final_month_over_threshold_share": float((df.final_month_requested > df.threshold).mean()),
           "biggest_final_month_jump": df.assign(j=df.final_month_catch - df.own_earlier_mean)
           .sort_values("j").tail(3)[["seed", "cycle", "identity", "final_month_catch", "own_earlier_mean"]].to_dict("records")}
    return out


# ---------------------------------------------------------------- influence by role (A5, AgentElect 4.5)
def influence_by_role(cent):
    whole = cent[(cent.phase == "whole") & (cent.routing == "primary")]
    rows, tests = [], []
    for cond, sub in whole.groupby("condition"):
        for metric in ("in_degree", "betweenness", "eigenvector"):
            for role, g in sub.groupby("role"):
                rows.append({"condition": cond, "metric": metric, "role": role, "mean": g[metric].mean(),
                             "n_agent_cycles": int(g[metric].notna().sum())})
            if sub.role.nunique() == 2:
                a = sub[sub.role == "focal"][metric].dropna()
                b = sub[sub.role == "peer"][metric].dropna()
                kw = stats.kruskal(a, b)
                tt = stats.ttest_ind(a, b, equal_var=False)
                tests.append({"condition": cond, "metric": metric, "kruskal_H": float(kw.statistic),
                              "kruskal_p": float(kw.pvalue), "welch_t": float(tt.statistic), "welch_p": float(tt.pvalue),
                              "label": "parity only (agents nested in runs)"})
    pd.DataFrame(rows).to_csv(RES / "influence_by_role.csv", index=False)
    pd.DataFrame(tests).to_csv(RES / "influence_by_role_tests.csv", index=False)
    g = []
    for (cond, s, c, ph), sub in cent[cent.routing == "primary"].groupby(["condition", "seed", "cycle", "phase"]):
        g.append({"condition": cond, "seed": s, "cycle": c, "phase": ph,
                  "gini_in_degree": M.gini(sub.in_degree), "gini_betweenness": M.gini(sub.betweenness),
                  "gini_eigenvector": M.gini(sub.eigenvector) if sub.eigenvector.notna().all() else None})
    gdf = pd.DataFrame(g)
    gdf.to_csv(RES / "centrality_gini_by_cycle.csv", index=False)
    return pd.DataFrame(rows), pd.DataFrame(tests), gdf


# ---------------------------------------------------------------- agreement among leadership measures (A5)
def agreement(runs, cent, peer, adopt_df):
    rows = []
    whole = cent[(cent.phase == "whole") & (cent.routing == "primary")]
    for cond in N8_INSTRUMENTED:
        for s in P1.SEEDS:
            r = runs.get((cond, s))
            if r is None:
                continue
            deg = whole[(whole.condition == cond) & (whole.seed == s)].groupby("identity").in_degree.sum()
            votes = peer[(peer.condition == cond) & (peer.seed == s)].groupby("identity").votes.sum()
            orig = adopt_df[(adopt_df.condition == cond) & (adopt_df.seed == s)].groupby("identity").originator_credit.sum()
            tie = defaultdict(float)
            for cy in r["cycles"]:
                ad = M.adoption({n: (cy["elicitation"].get(n) or {}).get("preferred_limit") for n in P1.present(cy)},
                                cy["agreed_limit"])
                for n, v in (ad or {}).items():
                    tie[n] += v
            tie = pd.Series(tie)
            idx = deg.index
            frame = pd.DataFrame({"votes": votes.reindex(idx, fill_value=0), "in_degree": deg,
                                  "tie_adoption": tie.reindex(idx, fill_value=0),
                                  "originator": orig.reindex(idx, fill_value=0)})
            rho = frame.corr(method="spearman")
            rows.append({"condition": cond, "seed": s,
                         **{f"rho_{a}_{b}": rho.loc[a, b] for a, b in
                            [("votes", "in_degree"), ("votes", "tie_adoption"), ("votes", "originator"),
                             ("in_degree", "tie_adoption"), ("in_degree", "originator"), ("tie_adoption", "originator")]}})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "leadership_measure_agreement_by_run.csv", index=False)
    return df.groupby("condition").mean(numeric_only=True).drop(columns="seed")


# ---------------------------------------------------------------- noise floor (A5)
def noise_floor(eff, h3, peer):
    """Reference vs baseline: run-to-run noise yardstick. Returns per-measure difference and
    the absolute difference of each intervention arm from baseline, in baseline-SD units."""
    meas = {}
    for m in ("welfare", "equality", "efficiency", "overusage", "survival_time"):
        meas[m] = eff.groupby("condition")[m].apply(list).to_dict()
    for col, ph in (("airtime_z", "nomination"), ("influence_z_primary", "nomination"), ("influence_z_primary", "whole")):
        sub = h3[h3.phase == ph].groupby(["condition", "seed"])[col].mean().reset_index()
        meas[f"{col}_{ph}"] = sub.groupby("condition")[col].apply(list).to_dict()
    rows = []
    for m, d in meas.items():
        if "replica_N8" not in d or "baseline_N8" not in d:
            continue
        ref, base = np.array(d["replica_N8"], float), np.array(d["baseline_N8"], float)
        pooled_sd = float(np.sqrt((np.var(ref, ddof=1) + np.var(base, ddof=1)) / 2))
        row = {"measure": m, "reference_mean": ref.mean(), "baseline_mean": base.mean(),
               "noise_floor_diff": float(base.mean() - ref.mean()), "pooled_sd": pooled_sd,
               "noise_floor_d": float((base.mean() - ref.mean()) / pooled_sd) if pooled_sd else None,
               "mwu_p_two_sided": float(stats.mannwhitneyu(ref, base, alternative="two-sided").pvalue)}
        for arm in ("values_N8", "stakes_N8", "coord_N16", "coord_N32"):
            if arm in d:
                a = np.array(d[arm], float)
                row[f"{arm}_minus_baseline"] = float(a.mean() - base.mean())
                row[f"{arm}_exceeds_noise_floor"] = bool(abs(a.mean() - base.mean()) > abs(base.mean() - ref.mean()))
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "noise_floor.csv", index=False)
    return df


# ---------------------------------------------------------------- figures
def figures(cent, nf):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    whole = cent[(cent.phase == "whole") & (cent.routing == "primary")].copy()
    whole["eigen_pct"] = np.nan
    for _, g in whole.groupby(["condition", "seed", "cycle"]):
        if g.eigenvector.notna().all():
            whole.loc[g.index, "eigen_pct"] = pd.Series(M.percentile_ranks(g.eigenvector.to_dict())).values
    whole["bet_pct"] = whole.groupby(["condition", "seed", "cycle"]).betweenness.rank(pct=False)
    for (c, s, cy), g in whole.groupby(["condition", "seed", "cycle"]):
        whole.loc[g.index, "bet_pct"] = pd.Series(M.percentile_ranks(g.betweenness.to_dict())).values
    conds = ["values_N8", "stakes_N8"]
    mat = np.array([[whole[(whole.condition == c) & (whole.role == "focal")][m].mean() for m in
                     ("in_degree_pct", "bet_pct", "eigen_pct")] for c in conds])
    fig, ax = plt.subplots(figsize=(5, 2.4))
    im = ax.imshow(mat, vmin=0, vmax=1, cmap="viridis")
    ax.set_xticks(range(3), ["in-degree", "betweenness", "eigenvector"])
    ax.set_yticks(range(2), conds)
    for (i, j), v in np.ndenumerate(mat):
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", color="w" if v < .6 else "k")
    ax.set_title("focal agent mean percentile rank per cycle (0.5 = chance)", fontsize=9)
    fig.colorbar(im, ax=ax, shrink=.8)
    fig.savefig(FIG / "centrality_heatmap_focal.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    sub = nf.dropna(subset=["pooled_sd"])
    fig, ax = plt.subplots(figsize=(7, 3.2))
    y = np.arange(len(sub))
    ax.barh(y, sub.noise_floor_diff / sub.pooled_sd, color="#bbbbbb", label="baseline − reference (noise floor)")
    for k, (arm, col) in enumerate((("values_N8", "#2ca02c"), ("stakes_N8", "#d62728"))):
        if f"{arm}_minus_baseline" in sub:
            ax.scatter(sub[f"{arm}_minus_baseline"] / sub.pooled_sd, y + (k - .5) * .25, color=col, label=f"{arm} − baseline", zorder=3)
    ax.axvline(0, color="k", lw=.6)
    ax.set_yticks(y, sub.measure, fontsize=8)
    ax.set_xlabel("difference in pooled-SD units (reference/baseline SD)")
    ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.01, 0.5))
    fig.tight_layout()
    fig.savefig(FIG / "noise_floor.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main():
    runs, _ = P1.validated_runs()
    cent = pd.read_csv(RES / "centrality_by_agent_cycle.csv")
    peer = pd.read_csv(RES / "peer_nominations_by_agent_cycle.csv")
    eff = pd.read_csv(RES / "efficacy_by_run.csv")
    h3 = pd.read_csv(RES / "h3_standardized_gini_by_cycle.csv")
    out = {}
    out["originator_focal_exploratory"], _ = originator(runs)
    adopt_df = pd.read_csv(RES / "originator_adoption_by_agent_cycle.csv")
    out["originator_summary"] = pd.read_csv(RES / "originator_summary.csv").to_dict("records")
    out["speaking_order_first_proposer"] = first_proposer_order(runs).to_dict("records")
    out["institutional_memory"] = institutional_memory(runs).to_dict("records")
    out["stakes_handoffs_numeric"] = stakes_handoffs(runs)
    _, tests, _ = influence_by_role(cent)
    out["influence_by_role_tests"] = tests.to_dict("records")
    out["leadership_measure_agreement_mean_rho"] = agreement(runs, cent, peer, adopt_df).reset_index().to_dict("records")
    nf = noise_floor(eff, h3, peer)
    out["noise_floor"] = nf.to_dict("records")
    figures(cent, nf)
    KEYS.dump(HERE / "keys_used.json")
    (RES / "secondary_summary.json").write_text(json.dumps(out, indent=1, default=str))
    print("ok")


if __name__ == "__main__":
    main()
