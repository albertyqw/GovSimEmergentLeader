# Phase 1 analysis report: all 30 runs (9 Nov 2026)

All six conditions × 5 seeds are complete and validated (commit `6dc5454`, `final-runs-v3`). Every analysis here is free; the only paid spend was the $0.66 judge calibration (`COST_ESTIMATE_B6.md`). Paid judging (B6) is on hold at your request.

**Reproduce** (from the repo root; all three read `runs/v3` read-only):
- `PYTHONDONTWRITEBYTECODE=1 python3 analysis/phase1.py` (about 1 min)
- `PYTHONDONTWRITEBYTECODE=1 python3 analysis/secondary.py`
- tests: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider analysis/tests`

RNG keys and draw counts are in `analysis/keys_used.json`. Tables are in `analysis/results/` and figures in `analysis/figures/`.

## Gates and decisions
- **Tests:** 20/20 pass (B5.1–B5.5, plus the exact Jonckheere–Terpstra test).
- **B1 regression:** the reference condition reproduces REPLICA_CHECK.md exactly: 195.4 ± 26.5 tons, equality 0.955 ± 0.006, all four flags HIGH.
- **Decisions you made on 9 Nov:**
  - Graph measures use the ANALYSIS_PLAN B2 definitions (`metrics.py`); check_data's graph values are legacy, and B5.6 parity is limited to the measures both define the same way. See `DISCREPANCIES.md`.
  - Survival time is cycles completed before collapse.
  - The primary phase for H3b is the nomination phase.
  - The agreed-limit quirks are kept as stored; logged in `QUIRKS.md` (commit `47986ab`).
  - check_data.py stays frozen.
- **Now unblocked:** N32 has finished and validated, so wiring check_data.py to `metrics.py` can be revisited (needs your go-ahead).

## 1. Data quality (`results/table3_data_quality.csv`)

| condition | trunc. | harvest fallbacks | agent / judge / random nominations | random share | instrument parse | 429 | cost $ |
|---|---|---|---|---|---|---|---|
| replica | 0 | 0 | 171 / 1 / 91 | 0.35 | n/a | 0 | 3.61 |
| baseline | 0 | 0 | 179 / 1 / 25 | 0.12 | 1.00 | 0 | 4.06 |
| values | 0 | 0 | 133 / 3 / 97 | 0.42 | 1.00 | 8 | 4.22 |
| stakes | 0 | 0 | 139 / 3 / 103 | 0.42 | 1.00 | 3 | 4.80 |
| coord_N16 | 2 | 0 | 267 / 3 / 212 | 0.44 | 1.00 | 13 | 11.16 |
| coord_N32 | 0 | 0 | 184 / 4 / 167 | 0.47 | 1.00 | 29 | 22.10 |

- No harvest fallbacks occurred, so the fallback-exclusion sensitivity analysis is identical to the main analysis.
- No 402 errors occurred.
- **Agents misname the next speaker very often.** 35–47% of routed handoffs used the random fallback, except in baseline (12%). That is why nominations by the judge and the random fallback are excluded from the primary graphs.
- **No thinking in the main runs.** All simulation calls logged 0 reasoning tokens, so the Gemini 2.5 Flash runs appear to have had thinking off; METHODS A5 assumes "default dynamic thinking".

## 2. Efficacy (`results/table1_efficacy.csv`; mean ± SE, n = 5; authors' SE in the CSV)

| condition | welfare (t) | survival time | survived | equality | efficiency | over-usage |
|---|---|---|---|---|---|---|
| replica | 195.4 ± 26.5 | 6.0 | 5/5 | 0.955 ± 0.006 | 0.69 ± 0.07 | 0.27 ± 0.06 |
| baseline | 189.6 ± 18.7 | 6.0 | 5/5 | 0.956 ± 0.006 | 0.70 ± 0.04 | 0.35 ± 0.12 |
| values | 230.2 ± 15.1 | **5.6 ± 0.24** | **3/5** | 0.956 ± 0.015 | 0.88 ± 0.05 | 0.61 ± 0.07 |
| stakes | 234.6 ± 9.4 | 6.0 | 5/5 | 0.941 ± 0.010 | 0.90 ± 0.06 | 0.63 ± 0.07 |
| coord_N16 (cap. 200) | 431.6 ± 62.7 | 6.0 | 5/5 | 0.938 ± 0.013 | 0.83 ± 0.08 | 0.51 ± 0.06 |
| coord_N32 (cap. 400) | 790.0 ± 141.3 | 6.0 | 5/5 | 0.937 ± 0.010 | 0.72 ± 0.08 | 0.35 ± 0.03 |

- Kruskal–Wallis: over-usage p = 0.004; survival time p = 0.066; equality p = 0.44. Welfare (p < 0.001) reflects the scaled capacity.
- **The only collapses** are values seeds 2 and 3, both in cycle 6.
- **Noise floor** (`results/noise_floor.csv`, `figures/noise_floor.png`): reference and baseline differ by 0.1–0.4 pooled SD on the efficacy measures. Both the values and stakes arms differ from baseline by more than that on welfare, efficiency and over-usage (+0.26 to +0.28 over-usage). Equality differs beyond the floor only in stakes.
- Reference and baseline do differ on nomination-phase airtime z (p = 0.03). This is probably driven by their different random-routing rates (35% vs 12%).

## 3. Manipulation checks
- **Values** (`results/manipulation_check_catch.csv`): the focal agent's catch is at or below the peer mean in 4 of 5 runs (seed 2: 2.3 vs 4.6 t). Its preferred limits are close to its peers'.
- **Stakes:** the 16-month agent catches less than its peers in 4 of 5 runs.
- **Coordination:** nomination-phase silence rises with N (27% at N8, 27% at N16, **70% at N32**), as expected with only 17 nomination turns at N32.

## 4. Primary tests (`results/table2_primary_tests.csv`; Holm across the five)

| test | statistic | p | Holm p | effect (95% bootstrap CI) |
|---|---|---|---|---|
| H1a adoption: values focal agent, mean percentile rank | 0.53 | 0.44 | 0.72 | +0.03 (−0.19, +0.19) |
| H1b eigenvector: values focal agent (5/5 runs defined) | 0.63 | 0.17 | 0.51 | +0.13 (−0.04, +0.34) |
| H2 in-degree: 16-month agent (30 cycles) | 0.52 | 0.36 | 0.72 | +0.02 (−0.11, +0.17) |
| **H3a** nomination airtime z, trend N8 < N16 < N32 | JT = 63 | **0.003** | **0.012** | N32 − N8 = +2.87 z (+1.89, +3.64) |
| **H3b** in-degree Gini z, trend N8 < N16 < N32 | JT = 75 | **1.3 × 10⁻⁶** | **6.6 × 10⁻⁶** | N32 − N8 = +6.41 z (+5.62, +7.23) |

H3 uses exact Jonckheere–Terpstra tests over 756,756 assignments.

- **H3b, influence concentrates beyond chance as N rises:** run-mean z is 0.3 at N8, 3.5 at N16 and 6.7 at N32. This holds with judge- and random-routed nominations added (N32 z 6.4 and 5.5), and for the whole-cycle (8.9) and opening-only (7.7) phases.
- **H3a, read with care:** airtime is *less* concentrated than the random nomination chain at every N (z −3.3, −2.9, −0.5). The significant trend is a move toward chance, not past it. Agents spread turns deliberately; that tendency weakens as N grows.
- **H1 and H2: no behavioral-centrality effect at n = 5.**
  - H1b, PageRank instead of eigenvector (a labeled deviation): p = 0.06.
  - H1b, excluding cycles the focal agent opened: p = 0.11.
  - H2 with betweenness, eigenvector, routing or opener exclusion: p = 0.23–0.71.
  - Matched-slot vs baseline: values in-degree +0.17 percentile, stakes +0.05; Wilcoxon p ≥ 0.125, where 0.0625 is the floor at n = 5.

## 5. Peer-nominated leadership (`results/peer_nominations_tests.csv`; exploratory)
- **Votes are near-unanimous.** In each cycle 96–99% of named votes go to one agent; 13–32% of answers are "no one".
- **Values focal agent:** 44.9% of named votes against 12.5% chance. Mean percentile rank 0.93, exact p = 0.0008. Top vote-getter in 3 of 5 runs.
- **Stakes 16-month agent:** 33.7% of votes, mean percentile rank 0.74, p = 0.043.
- **Agreement with centrality:** votes track in-degree (mean per-run Spearman 0.49–0.69) but not tie-aware adoption of elicited limits (−0.19 to 0.09). `results/leadership_measure_agreement_by_run.csv`.

## 6. Other secondary analyses (exploratory; `results/secondary_summary.json`)
- **Institutional memory** (name-mention proxy; CHAT memories are framework summaries; `institutional_memory_by_run.csv`). In the values arm, **14.5% of every agent's retrieved memories name the focal agent, against 0.1% for each peer** (focal percentile 0.79). Summaries record "Julia's framework", "Jack's proposal". In stakes, successors' memories name the 16-month agent 4.6% of the time, against 3.4% for other original members: no clear institutional-memory role.
- **Stakes final month** (`stakes_final_month_catch.csv`). Leavers (n = 25) catch **1.8 t more than same-cycle peers** (Wilcoxon p = 0.002), though only +0.5 t over their own earlier months (p = 0.67). The largest jumps were 5 → 15 t and 6 → 10 t. **76%** of final-month requests exceed the sustainability threshold. Succession did not fully remove endgame over-harvesting.
- **Originator adoption** (`originator_*`; extractor hold-out error **18/100**, `proposal_audit_summary.json`): no focal effect (values percentile 0.44, p = 0.72; stakes 0.69, p = 0.10).
- **Speaking order:**
  - The agreed limit sits closer to the opener's private limit than chance only in stakes (p = 0.029).
  - The first proposer's number ends *farther* from the agreement than a random proposer's in every arm except N16, so opening proposals are typically revised (`speaking_order_first_proposer.csv`).
- **Influence by role, parity tests** (`influence_by_role*.csv`): the values focal agent averages in-degree 6.2 vs 3.5 for peers (Kruskal–Wallis p = 0.016, Welch p = 0.06). These ignore nesting; the permutation test (H1b) is the inferential one.
- **Opinion convergence:** the values arm has the tightest pre-discussion limits (SD 0.36) and next-month catches (0.49); stakes has the widest (1.02 and 1.17).

## 6b. Speaking first and proposal acceptance (exploratory; `analysis/speaking_order.py`)
The opening order is a keyed random draw, so position effects are causal within this protocol. Tests are within-cycle permutations, 10,000 keyed draws per cycle (`results/speaking_order_tests.csv`, `speaking_order_by_position_N8.csv`, `figures/speaking_position_effects_N8.png`).

| Measure (N = 8 arms pooled) | Opener | Chance (re-drawn opener) | p | Earlier-is-better gradient p |
|---|---|---|---|---|
| Private limit adopted (tie-aware credit) | 0.10 | 0.10 | 0.51 | 0.17 |
| Opener's public proposal matches the agreement (vs. other proposers) | 0.79 | 0.85 | 0.999 | n/a |
| Originator credit (earliest proposer of the agreed number) | 0.38 | 0.11 | < 0.001 | < 0.001 |
| Share of private "most influential" votes | **0.59** | 0.12 | < 0.001 | < 0.001 |

- **Speaking first does not make the group adopt your number.** The opener's private limit is adopted no more often than anyone else's. When the opener makes a public proposal, it matches the final agreement no more often than other proposers' (0.79 vs. 0.85; for N16/N32, 0.82 vs. 0.80).
- **The originator effect is mostly timing.** Most proposals already match the eventual agreement, so whoever speaks first is usually the "earliest" to state it.
- **Speaking first makes peers see you as the leader.** The opener gets 59% of named "most influential" votes at N = 8 (chance 12.5%) and 41% at N16/N32 (chance about 4.7%). This holds in every arm, including when cycles opened by the focal agent are excluded (56%). The last opener, who nominates the first nomination-phase speaker, gets fewer votes than chance (5%).
- **Consequence for the values result.** The values agent opened 3 of its 30 months. Excluding those months, its vote share is still 41% (3× chance), but the per-run permutation test weakens from p = 0.0005 to p = 0.065. The stakes agent's effect falls to p = 0.18. Part of the peer-vote "leader" effect is a first-mover effect.
- This sharpens the main pattern: *who peers name as the leader* tracks salience (speaking first, a prosocial plan), while *what the group adopts* does not move with either.

## 7. Figures (`analysis/figures/`)
- `speaking_position_effects_N8.png`
- `stock_trajectories.png`
- `focal_vs_peer_catch.png`
- `peer_nomination_focal_heatmap.png`
- `centrality_heatmap_focal.png`
- `standardized_gini_vs_N.png`
- `noise_floor.png`

## Caveats
- Five seeds per arm. The focal slot (0–4) is confounded with seed.
- Graphs are built from mentions and agent-made nominations only.
- Institutional memory uses a name-mention proxy.
- The proposal extractor has an 18% error rate on a hold-out sample.
- Deference and sentiment judging are not done (on hold).
