"""Two compact figures for the hackathon submission. From the folder that contains analysis/ (repo root):
PYTHONDONTWRITEBYTECODE=1 python3 analysis/paper_figures.py"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RES, FIG = HERE / "results", HERE / "figures"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})

# Figure 1: share of named peer votes received by the focal agent, per seed
peer = pd.read_csv(RES / "peer_nominations_by_agent_cycle.csv")
cent = pd.read_csv(RES / "centrality_by_agent_cycle.csv")
cent = cent[(cent.phase == "whole") & (cent.routing == "primary")]
fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.5), sharey=True)
for ax, cond, col, label in ((axes[0], "values_N8", "#2a7f62", "Values agent"), (axes[1], "stakes_N8", "#b5523b", "16-month agent")):
    sub = peer[peer.condition == cond]
    tot = sub.groupby("seed").votes.sum()
    vote_share = sub[sub.role == "focal"].groupby("seed").votes.sum() / tot
    c = cent[cent.condition == cond]
    deg_share = c[c.role == "focal"].groupby("seed").in_degree.sum() / c.groupby("seed").in_degree.sum()
    x = np.arange(5)
    ax.bar(x - 0.18, vote_share.values, 0.36, color=col, label="peer votes")
    ax.bar(x + 0.18, deg_share.values, 0.36, color=col, alpha=0.35, label="in-degree")
    ax.axhline(1 / 8, color="k", ls="--", lw=0.8)
    ax.text(-0.5, 1 / 8 + 0.015, "chance (1/8)", ha="left", fontsize=7)
    ax.set_xticks(x, [f"seed {s}" for s in x], fontsize=7)
    ax.set_title(label, fontsize=9)
axes[0].set_ylabel("focal agent's share")
axes[0].legend(fontsize=7, frameon=False, loc="upper right")
fig.tight_layout()
fig.savefig(FIG / "paper_fig1_focal_share.png", dpi=200)
plt.close(fig)

# Figure 2: standardized Gini (nomination phase) vs N
h3 = pd.read_csv(RES / "h3_standardized_gini_by_cycle.csv")
h3 = h3[(h3.phase == "nomination") & (h3.condition != "replica_N8")]
run = h3.groupby(["N", "seed"])[["airtime_z", "influence_z_primary"]].mean().reset_index()
fig, ax = plt.subplots(figsize=(4.2, 2.6))
for col, color, lab, dx in (("influence_z_primary", "#3b5ba5", "influence (incoming references)", -0.6),
                            ("airtime_z", "#d18f2b", "airtime (speaking turns)", 0.6)):
    for n in (8, 16, 32):
        v = run[run.N == n][col]
        ax.scatter(np.full(len(v), n + dx), v, color=color, s=14, alpha=0.8, label=lab if n == 8 else None)
        ax.plot([n + dx - 0.9, n + dx + 0.9], [v.mean()] * 2, color=color, lw=2)
ax.axhline(0, color="k", lw=0.8)
ax.text(11, 0.3, "chance", fontsize=7, ha="center")
ax.set_xticks([8, 16, 32])
ax.set_xlabel("group size N")
ax.set_ylabel("Gini vs. null (z)")
ax.legend(fontsize=7, frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig(FIG / "paper_fig2_concentration_vs_N.png", dpi=200)
plt.close(fig)
print("ok")
