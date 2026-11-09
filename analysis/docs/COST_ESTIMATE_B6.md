# B6 paid-analysis cost estimate (9 Nov 2026, 05:30 EST)

No paid calls were made. Item counts and text sizes come from the stored raw logs of the 25 validated runs, plus a projection for coord_N32, which is still running. Token counts assume about 4 characters per token. The counting scripts are `analysis/count_items.py` and `analysis/name_filter.py`.

## Prices (OpenRouter public models API, fetched today)
| Model | Input $/M | Output (incl. thinking) $/M |
|---|---|---|
| google/gemini-2.5-pro (≤200k prompt) | 1.25 | 10.00 |
| google/gemini-2.5-flash | 0.30 | 2.50 |
| google/gemini-2.5-flash-lite | 0.10 | 0.40 |

**Main uncertainty:** thinking tokens. The judge runs with default dynamic thinking, and Gemini 2.5 Pro cannot turn thinking off. The visible answer is about 25 tokens, so cost is driven almost entirely by how much the model thinks per item. None of our stored calls returned reasoning text, so there is no local measurement. The ranges below assume 300–1,000 thinking tokens per item on Pro and 200–800 on Flash.

## Budget headroom
- Ledger spend so far: **$40.82** (read-only from `runs/.control/spend.sqlite`; includes $12.06 already spent on coord_N32).
- N32 forecast: $30.77 for five runs (`reports/wave-a/n32_launch_projection.json`), so about $18.7 remains. That becomes $28.1 with the 50% contingency.
- Headroom under the $90 guard after N32: **about $30 central, or about $21 with the N32 contingency.**

## Per stage
| Stage | Items | Input tokens | Gemini 2.5 Pro | Gemini 2.5 Flash |
|---|---|---|---|---|
| 1 Deference: harvest + utterance completions + elicitation reasons | 5,500 now (1,441 + 2,859 + 1,200); about 8,700 with N32 | about 6.1M | **$34–95** | **$6–19** |
| 1 validation: second judge, 150 items | 150 | about 0.15M | ≤ $2 | ≤ $0.5 |
| 2 Stakes handoffs: final-month utterances | 46 | about 25k | < $0.50 | < $0.15 |
| 3 Sentiment/rhetoric: every utterance × 2 taxonomies, `max_tokens=500` | about 4,160 utterances → 8,300 calls | about 9.4M | **$45–53** (output capped at 500) | **$6–13** |
| 3 validation: 150 utterances | 300 calls | about 0.3M | ≤ $2 | ≤ $0.5 |
| 4 Embeddings | about 5,400 texts | about 1.4M | < $1 (embedding model not yet chosen) | |

Notes:
- **Stage 3 on Pro:** the 500-token cap includes thinking, so many calls will probably truncate. The plan says to STOP if more than 2% of the first 50 fail.
- **No reasoning items:** no separate reasoning items exist, because no call returned reasoning text (reasoning tokens = 0 in every run).
- **Turning thinking off:** Stage 1 on Flash with a thinking budget of 0 would cost about $2.5. That departs from "default thinking" for the judge and would need your approval.

## Options that fit
1. **Calibration first (recommended):** judge about 50 Stage 1 items each on Pro and Flash. Cost **< $1.50**. This measures real thinking tokens and turns the ranges above into point estimates. It needs B6 Stage 1 approval for this spend only.
2. **Stage 1 + 2 on Flash:** about $7–20 including validation. Fits.
3. **Stage 1 + 2 + 3, all on Flash:** about $13–33. Fits only at the low end, so decide after calibration.
4. **Stage 1 on Pro, as the plan's default:** likely exceeds the headroom at the upper end. **Stage 3 on Pro** does not fit alongside Stage 1.

In every option, the hand-labeled kappa check (50 items; threshold 0.6) is a gate before any results are used.

---

# Proposed amendment to ANALYSIS_PLAN B6: filtered and hybrid judging (not yet approved)

Status: **proposal only.** B6 currently specifies the full item sets judged on Gemini 2.5 Pro. Nothing below may run until you approve the amendment and the stage's cost gate. Scripts: `analysis/count_items.py` and `analysis/name_filter.py`. Run them from `GovSimEmergentLeader/` with `PYTHONDONTWRITEBYTECODE=1`; both read only.

## A1. Stage 1: free name pre-filter (deterministic; no model)
**Rationale.** Question 1 counts deference only to "another named participant". An item whose text names no other present participant can only be labeled `DEFERS_TO: none`. Filter: `metrics.mentioned_set(text, present) − {author}` is non-empty (same resolver as the graphs).

| Item type | Name another participant (25 runs) |
|---|---|
| Harvest completions | 116 / 1,441 (8%) |
| Utterance completions | 1,967 / 2,859 (69%) |
| Elicitation reasons | 13 / 1,200 (1%) |
| **Total** | **2,096 / 5,500 (38%)** |

- **Items judged:** about 3,300 including the N32 projection; filtered-out items are recorded as `none (no named participant; filtered)`.
- **Filter check:** the main judge labels a keyed random sample of 100 filtered-out items (key `analysis|audit|deference_filter`). If any is labeled as deferring to a named participant, **STOP** and report.
- **Exception:** `MENTIONS_TENURE` (stakes manipulation check) needs every stakes item: 963 items, judged unfiltered. Alternatively, use a regex for "months remaining"/tenure terms with a hand-checked sample.
- The existing validation still applies: second judge on 150 items, 50 hand labels, kappa ≥ 0.6.

| Stage 1 cost | Pro | Flash |
|---|---|---|
| Unfiltered (current B6) | $34–95 | $6–19 |
| **Name-filtered** | **$12–35** | **$2–6** |
| Filter check (100 items) + stakes tenure items | ≤ $5 | ≤ $1.5 |

## A2. Stage 3: no label-based filtering; use one of two unbiased designs
Filtering on Flash's labels and sending only flagged utterances to Pro would mix the two judges' errors into the Cooperative Index denominator, so it is **not proposed**.

**Option 3a: Flash on all, Pro on a keyed random subset (recommended).**
- Flash judges all ~4,160 utterances with both taxonomies.
- Pro judges a random subset stratified by condition × role (focal/peer), about 450 utterances (key `analysis|sample|stage3_pro|{condition}|{role}`).
- Pro labels give AgentElect-parity estimates on the subset. Full-sample indices use prediction-powered inference: the Flash estimate on all items plus the mean Pro − Flash difference on the subset, with a bootstrap CI over runs.
- The Pro–Flash pairs double as the second-judge kappa check (binary cooperative label, dominant persuasion class), replacing the separate 150-utterance validation.
- Cost: Flash **$6–13** + Pro about **$6**.

**Option 3b: Pro only on a stratified sample.**
- All focal-agent utterances (values and stakes), plus a matched random peer sample, plus a random sample of other conditions; weighted back to full counts.
- About $13 per 1,000 utterances; lower precision for peer and condition-level estimates.

In either option, the B6 500-token cap and the 2% truncation STOP rule apply to every Pro call.

## A3. Combined plan that fits the headroom (~$21–30 after N32)
| Component | Cost |
|---|---|
| Calibration (50 Stage 1 items each on Pro and Flash) | < $1.5 |
| Stage 1, name-filtered, Flash (incl. filter check, tenure items, second-judge 150 on Pro) | about $4–10 |
| Stage 2, Pro | < $0.5 |
| Stage 3, option 3a | about $12–19 |
| **Total** | **about $18–31** |

The upper end touches the headroom limit. Calibration decides whether Stage 3 fits as specified, or needs a smaller Pro subset. Stage 4 (embeddings, < $1) waits until the rest is done.

**Decisions needed before any spend:**
1. Approve the amendment (A1, A2 option 3a or 3b).
2. Approve the calibration spend (< $1.5) under the B6 gate.

---

# Calibration results (approved and run 9 Nov 2026)

Run: `analysis/judge_calibration.py --live`. 50 name-filtered Stage 1 items (45 utterances, 5 harvests; key `analysis|calib|stage1`), each judged once by both models. Settings: temperature 0, `max_tokens` 16,000, provider pinned to Google AI Studio, no thinking budget set. All 100 calls reserved and settled through the shared ledger. Raw prompts, responses and costs are in `analysis/judge_cache/stage1_calibration.jsonl`; the summary is in `results/stage1_calibration_summary.json`. **Actual spend: $0.664** ($0.654 Pro, $0.011 Flash).

| | Gemini 2.5 Pro | Gemini 2.5 Flash |
|---|---|---|
| Mean input tokens | 545 | 545 |
| Mean output tokens (thinking) | 1,239 (1,226), max 2,585 | 19 (**0**) |
| Cost per item | **$0.0131** | **$0.00021** |
| Length finishes | 0 | 0 |
| Unparsed (no retry, per B6) | 0 / 50 | **6 / 50**: every one named several people (e.g. "Noah, Luke") despite "one participant name" |
| Named deference | 34 / 50 | 30 / 50 |
| Agreement with Pro, named vs none (44 parsed pairs) | | 86.4%, **kappa 0.70** (identity agreement also 86.4%) |

## What this changes
1. **Pro thinks more than assumed** (about 1,230 tokens, not 300–1,000). Stage 1 name-filtered on Pro is about **$43 + about $9 tenure items, roughly $50**: over the headroom.
2. **Flash did no thinking at all** (0 reasoning tokens), so it is far cheaper than estimated. Stage 1 name-filtered on Flash is about **$1**.
3. **The Stage 3 cap of 500 cannot work on Pro.** Pro's mean output of about 1,240 tokens is already over 500, so nearly every call would truncate and trigger the B6 2% STOP rule. Pro for Stage 3 needs either a higher cap (a departure from the `llm_judge` setting) or dropping Pro for Stage 3.
4. **Flash's 12% unparsed rate** comes from multi-name answers. Under the verbatim prompt and no-retry rule, these become `unparsed`. Recording "multiple named" as its own category would be a definition change.
5. **Side finding about the main runs:** every simulation call also logged 0 reasoning tokens (full coverage, all conditions). Gemini 2.5 Flash via OpenRouter appears to have run **without thinking**, although METHODS A5 assumes "default dynamic thinking". Pro under the same request shape does report thinking, so this is probably real rather than a reporting gap. It matters for comparability with AgentElect, which reports using thinking.

## Revised totals (headroom about $21–30 after N32)
| Plan | Approximate cost |
|---|---|
| Stage 1 Flash (filtered, plus tenure items) + 150-item Pro second judge + Stage 2 Pro + Stage 3 Flash on all | about **$7** |
| …plus Pro on a 450-utterance Stage 3 subset with the cap raised to 16,000 | about **$20** |
| Stage 1 on Pro (filtered) | about $50: does not fit |
