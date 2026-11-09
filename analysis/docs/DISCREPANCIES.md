# check_data.py / study_analysis.py vs ANALYSIS_PLAN.md B2

*Written during analysis in a separate working folder (`ClaudeAnalysis/`); file paths now refer to `analysis/` in this repository.*

**Resolution (user, 9 Nov 2026):** study results use the B2 definitions in `analysis/metrics.py`. check_data's graph values are legacy. Origin: check_data.py and study_analysis.py were written for this project (first commit `2e03446`, frozen in `final-runs-v3` at `6dc5454`). They follow the frozen METHODS.md, which predates the 9 Nov edge and eigenvector clarifications. The B5.6 parity test is limited to the measures both files define the same way. check_data.py stays frozen until coord_N32 completes and validates (user decision): run_study.py imports it, and its preflight requires a clean tracked checkout on final-runs-v3.

`CLAUDE.md` says: "If `check_data.py` and `ANALYSIS_PLAN.md` B2 define a measure differently, stop and report before changing either." Neither file has been changed. Everything below was found by reading `GovSimEmergentLeader/study_analysis.py` (which `check_data.py` imports) and `simulation/recording.py`. The impact was measured by `analysis/phase1.py` → `results/parity_check_data_vs_B2.csv`.

| # | Measure | check_data / study_analysis | ANALYSIS_PLAN B2 / METHODS_UPDATED A10 | Where |
|---|---|---|---|---|
| D1 | Mention edges | One edge per **occurrence**. `mentioned_identities` is a `re.findall` list, so repeated names count more than once | Each mentioned agent counted **once per utterance** (B2.1) | `recording.py:276`, `study_analysis.py:30` |
| D2 | Nomination routing | Every `nominee_resolved` counts, whether the agent, the judge or the random fallback chose it | Primary graph: `agent` only. Judge, then random, are sensitivity graphs (B2.1) | `study_analysis.py:31-33` |
| D3 | Self-nominations | Kept as self-loop edges; they inflate in-degree and the adjacency diagonal | Excluded from graphs and counted separately (B2.1) | `study_analysis.py:32` |
| D4 | Eigenvector undefined rule | Undefined only if the dominant eigenvector is not unique or not non-negative | Undefined if the graph is **not strongly connected**, with reason `not_strongly_connected` (B2.5) | `study_analysis.py:60-77` |
| D5 | Gini of all zeros | Returns `0.0` | Undefined (B2.7, A6) | `study_analysis.py:14-17` |
| D6 | Null RNG keys and draws | `analysis_airtime|cond|seed|cycle|replicate`, 1,000 draws, with no phase in the key | `analysis|null|airtime|{condition}|{seed}|{cycle}|{phase}`, 10,000 draws (B3, A4) | `study_analysis.py:95,113` |
| D7 | Influence null events | Redraws targets for every nomination, including judge- and random-routed ones | Uses the same events as the observed primary graph (agent nominations only) | follows from D2 |

**Measured impact on the 25 validated N8/N16 runs (150 cycle graphs, whole cycle):**
- In-degree vectors match exactly in only **26%** of cycle graphs.
- The eigenvector is defined in **81%** of cycle graphs under check_data but only **45%** under B2.
- D2 matters most. Of the routed nomination-phase handoffs, **42% came from the keyed random fallback** (505 random, 674 agent, 10 judge across all v3 runs). Under check_data's definition, those random draws count as influence.

**B5.6 status:** "the shared module and `check_data.py` give identical values for every shared measure" **fails** for degree, eigenvector status and the nulls. It passes for total catch, equality, efficiency, over-usage and tie-aware adoption, which are defined the same way in both.

**Also out of reach under the edit rule.** B2 says to make `check_data.py` call the shared module. B1.1 says to build `derived/` inside the repo. B7 says to write `analysis/` at the repo root and commit it. All three need writes outside `ClaudeAnalysis/`, so none was done. The shared module lives at `analysis/metrics.py`, and it reads the raw JSONL read-only.

## Original decision request (answered above)
1. Use the B2 definitions (as implemented in `metrics.py`) for every study result, and treat check_data's graph values as legacy? Or something else?
2. Should `check_data.py` be changed to call `metrics.py` (this needs your approval to edit outside ClaudeAnalysis), or should the parity test be scoped to the measures both files define the same way?
