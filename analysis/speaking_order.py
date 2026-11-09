"""Does speaking first (or earlier) in the compulsory opening round help an agent's proposal get adopted?

The opening order is a keyed random draw (opener|seed|cycle, then a keyed shuffle), independent of
the agents, so position effects are causal within this protocol. For each cycle with a numeric
agreed limit we score every present agent on:
  - adoption:   tie-aware credit for the agreed limit from its *private* pre-discussion limit (not replica)
  - originator: credit 1 to the earliest public proposer of the agreed number (proposal extractor; all arms)
  - votes:      share of the private "most influential" votes it received (not replica; all cycles)
Tests (exploratory, Monte Carlo permutation within cycle, 10,000 keyed draws per cycle):
  - Opener: mean credit of the first speaker vs. a uniformly re-drawn "opener" in the same cycle.
  - Last opener (who also nominates the first nomination-phase speaker): same test.
  - Position gradient: mean over cycles of sum_i credit_i * (pos_i - mean pos) / (N - 1); negative means
    earlier speakers get more credit. Null: positions shuffled within cycle.
Keys: analysis|perm|order|{condition}|{seed}|{cycle}|{measure}|{test}.
Run from the folder that contains analysis/ (repo root):  PYTHONDONTWRITEBYTECODE=1 python3 analysis/speaking_order.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import metrics as M  # noqa: E402
import proposals as P  # noqa: E402
import phase1 as P1  # noqa: E402

RES, FIG, KEYS = P1.RES, P1.FIG, P1.KEYS
DRAWS = 10_000
MEASURES = ("adoption", "originator", "votes")


def cycle_rows(runs):
    rows = []
    for (cond, s), r in sorted(runs.items()):
        focal = P1.focal_identity(r)
        for cy in r["cycles"]:
            turns = P1.cycle_turns(r, cy["cycle"])
            opening = [t["speaker_identity"] for t in turns if t.get("discussion_stage") == "opening"]
            names = P1.present(cy)
            assert sorted(opening) == sorted(names)
            pos = {n: i + 1 for i, n in enumerate(opening)}
            agreed = cy["agreed_limit"]
            el = cy.get("elicitation") or {}
            adopt = M.adoption({n: (el.get(n) or {}).get("preferred_limit") for n in names}, agreed) if el else None
            firsts = {}
            for t in turns:
                v = P.first_proposal(t["text"])
                if v is not None and t["speaker_identity"] not in firsts:
                    firsts[t["speaker_identity"]] = (t["position"], v)
            orig = M.originator({n: firsts.get(n, (10 ** 6, None)) for n in names}, agreed)
            pl = cy.get("perceived_leadership") or {}
            votes = pd.Series([v["resolved_identity"] for v in pl.values()]).value_counts() if pl else None
            n_named = int(votes.drop("no one", errors="ignore").sum()) if votes is not None else 0
            for n in names:
                rows.append({
                    "condition": cond, "N": len(names), "seed": s, "cycle": cy["cycle"], "identity": n,
                    "position": pos[n], "is_opener": pos[n] == 1, "is_last_opener": pos[n] == len(names),
                    "is_focal": n == focal, "focal_opened": opening[0] == focal if focal else False,
                    "agreed": agreed,
                    "adoption": adopt[n] if adopt is not None else np.nan,
                    "originator": orig[n] if orig is not None else np.nan,
                    "votes": (votes.get(n, 0) / n_named) if n_named else np.nan,
                    "private_limit": (el.get(n) or {}).get("preferred_limit") if el else None,
                    "public_first_proposal": firsts.get(n, (None, None))[1],
                })
    df = pd.DataFrame(rows)
    df.to_csv(RES / "speaking_order_by_agent_cycle.csv", index=False)
    return df


def permutation(df, measure, test, conds, exclude_focal_cycles=False):
    obs, null = [], np.zeros(DRAWS)
    used = 0
    for (cond, s, c), g in df[df.condition.isin(conds)].groupby(["condition", "seed", "cycle"]):
        if g[measure].isna().any() or (exclude_focal_cycles and g.focal_opened.any()):
            continue
        credit = g[measure].to_numpy(float)
        posn = g.position.to_numpy(float)
        n = len(g)
        rng = KEYS.rng(f"analysis|perm|order|{cond}|{s}|{c}|{measure}|{test}" + ("|exfocal" if exclude_focal_cycles else ""), DRAWS)
        if test in ("opener", "last_opener"):
            target = 1 if test == "opener" else n
            obs.append(credit[posn == target][0])
            null += credit[rng.integers(n, size=DRAWS)]
        else:  # gradient
            centred = (posn - posn.mean()) / (n - 1)
            obs.append(float((credit * centred).sum()))
            perm = np.argsort(rng.random((DRAWS, n)), axis=1)
            null += (credit[perm] * centred).sum(axis=1)
        used += 1
    if not used:
        return None
    stat = float(np.mean(obs))
    null /= used
    if test == "gradient":
        p = float((np.sum(null <= stat + 1e-12) + 1) / (DRAWS + 1))  # one-sided: earlier speakers favored
    else:
        p = float((np.sum(null >= stat - 1e-12) + 1) / (DRAWS + 1))  # one-sided: opener favored
    return {"measure": measure, "test": test, "conditions": "+".join(conds), "cycles": used,
            "statistic": stat, "null_mean": float(null.mean()), "p_one_sided": p,
            "exclude_focal_opened": exclude_focal_cycles}


def match_test(df, conds, label):
    """Timing-free: among agents with a public proposal in the cycle, is the opener's first proposal more
    likely to equal the agreed limit than a uniformly chosen proposer's? Also the same for private limits."""
    out = []
    for col, name in (("public_first_proposal", "public"), ("private_limit", "private")):
        obs, null, used = [], np.zeros(DRAWS), 0
        for (cond, s, c), g in df[df.condition.isin(conds)].groupby(["condition", "seed", "cycle"]):
            ag = g.agreed.iloc[0]
            if not isinstance(ag, (int, float)) or pd.isna(ag):
                continue
            vals = pd.to_numeric(g[col], errors="coerce")
            have = g[vals.notna()]
            if have.empty or not have.is_opener.any():
                continue
            match = (pd.to_numeric(have[col]).sub(ag).abs() <= 1e-6).to_numpy(float)
            obs.append(match[have.is_opener.to_numpy()][0])
            rng = KEYS.rng(f"analysis|perm|order|{cond}|{s}|{c}|{name}_match|opener", DRAWS)
            null += match[rng.integers(len(match), size=DRAWS)]
            used += 1
        if used:
            stat = float(np.mean(obs)); null /= used
            out.append({"measure": f"{name}_proposal_matches_agreed", "test": "opener_vs_other_proposers",
                        "conditions": label, "cycles": used, "statistic": stat, "null_mean": float(null.mean()),
                        "p_one_sided": float((np.sum(null >= stat - 1e-12) + 1) / (DRAWS + 1)),
                        "exclude_focal_opened": False})
    return out


def figure(df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 3, figsize=(8.4, 2.6), sharey=True)
    n8 = df[df.N == 8]
    for ax, m, lab in zip(axes, MEASURES, ("private-limit adoption credit", "originator credit", "share of peer votes")):
        g = n8.dropna(subset=[m]).groupby("position")[m]
        mean, se = g.mean(), g.std(ddof=1) / np.sqrt(g.count())
        ax.errorbar(mean.index, mean.values, yerr=se.values, fmt="o-", color="#3b5ba5", ms=4, capsize=2)
        ax.axhline(1 / 8, color="k", ls="--", lw=0.8)
        ax.set_xticks(range(1, 9))
        ax.set_xlabel("opening position (N = 8)")
        ax.set_title(lab, fontsize=9)
    axes[0].set_ylabel("mean per cycle")
    fig.tight_layout()
    fig.savefig(FIG / "speaking_position_effects_N8.png", dpi=180)
    plt.close(fig)


def main():
    runs, _ = P1.validated_runs()
    df = cycle_rows(runs)
    n8_instr = ["baseline_N8", "values_N8", "stakes_N8"]
    n8_all = ["replica_N8"] + n8_instr
    big = ["coord_N16", "coord_N32"]
    results = []
    for measure, conds in (("adoption", n8_instr), ("adoption", big), ("originator", n8_all), ("originator", big),
                           ("votes", n8_instr), ("votes", big)):
        for test in ("opener", "last_opener", "gradient"):
            results.append(permutation(df, measure, test, conds))
    for measure, conds in (("adoption", n8_instr), ("originator", n8_all), ("votes", n8_instr)):
        for test in ("opener", "gradient"):
            results.append(permutation(df, measure, test, conds, exclude_focal_cycles=True))
    for cond in ["replica_N8", "baseline_N8", "values_N8", "stakes_N8", "coord_N16", "coord_N32"]:
        for measure in MEASURES:
            r = permutation(df, measure, "opener", [cond])
            if r:
                results.append(r)
    results += match_test(df, n8_all, "+".join(n8_all)) + match_test(df, big, "+".join(big))
    out = pd.DataFrame([r for r in results if r])
    out.to_csv(RES / "speaking_order_tests.csv", index=False)
    # descriptive: mean credit by position, N8 pooled
    desc = (df[df.N == 8].groupby("position")[list(MEASURES)].mean().round(4))
    desc.to_csv(RES / "speaking_order_by_position_N8.csv")
    # does the opener's private limit move the agreement? (agreed vs opener's limit, regression across cycles)
    figure(df)
    KEYS.dump(HERE / "keys_used.json")
    print(out.round(4).to_string())
    print(desc.to_string())


if __name__ == "__main__":
    main()
