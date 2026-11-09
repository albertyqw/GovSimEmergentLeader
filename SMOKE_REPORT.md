# Neutral study smoke validation complete

All six seed-0, one-cycle Flash-Lite smokes passed `check_data.py` with 1000 null replicates on source commit `499f8d2`. Every run records the same start/end commit, `neutral_study: true`, correct participant counts, common paper settings, and fixed 16000/1000 caps. The initial full pilot and all earlier attempts remain preserved and superseded. No replacement full Flash pilot has started.

| Condition | Attempt | Calls | Seconds | Requested tons | Final stock | Cost USD | Length | 429 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| replica_N8 | seed0_attempt5 | 106 | 117.4 | 43 | 100 | 0.02361730 | 0 | 86 |
| baseline_N8 | seed0_attempt5 | 122 | 116.7 | 43 | 100 | 0.02436048 | 0 | 80 |
| values_N8 | seed0_attempt3 | 118 | 125.1 | 44 | 100 | 0.02493326 | 0 | 75 |
| stakes_N8 | seed0_attempt3 | 125 | 101.9 | 51 | 98 | 0.02654040 | 0 | 2 |
| coord_N16 | seed0_attempt3 | 236 | 216.7 | 101 | 198 | 0.05532190 | 0 | 14 |
| coord_N32 | seed0_attempt4 | 478 | 430.7 | 490 | 0 | 0.13889562 | 2 | 40 |

## Diagnostics

- All harvest decisions parsed numerically. Every applicable private instrument parsed at 100%; the replica intentionally has none.
- Nomination failures were zero except N32: **one of 16 (6.25%)**, flagged above the 3% reporting threshold. Jack nominated `Everyone` at zero-based turn 10. The recorded key `nominee_fallback|0|1|10` uniformly selected Tariq from all 32 offered identities. Applied status, candidate, options, raw invalid nomination and actual next speaker agree. Julia is no longer a fixed fallback.
- N32 Noah had two harvest length finishes (15940 and 15968 reported output tokens). The existing same-cap next-stage parser extracted option 300 from partial text. The group requested 490 tons from 400, exhausted the lake and collapsed. This is a preserved original numeric-parser consequence, not proof of a complete final model answer. No cap increase, new truncation retry or numeric-parser repair was made.
- The other five conditions survived their single smoke cycle. These are short Flash-Lite observations, not full-model study results.
- There were **297 recorded 429 events**, handled under the authorized retry policy, and zero 402 events. Concurrent smoke traffic produced substantial rate limiting; it affects runtime. The replacement pilot runs a single seed, and later-wave concurrency should be reviewed using full-model evidence. All attempts and actual costs remain counted.
- Original reflection/evidence quirks and parse defaults remain logged. None of the newly authored general/task text assigns leadership; model-generated utterances and memories remain unmodified.

## Verification, budget and handoff

All 42 tests passed. A separate stricter prompt audit checked all six six-cycle native stub runs, including successors, and found no leader/leadership/mayor wording in the canned-run prompts; every general agent prompt contained the correct N. Forced-invalid nomination tests passed at N8/N32 and with stakes tags, including raw evidence, applied labels, valid next-speaker routing and global-RNG isolation. Disabled study overrides remain byte-identical to the pinned original payload fixture.

Current six-smoke spending: **$0.29366896**. Cumulative project ledger: **$1.03935069**, including the superseded full pilot and every old smoke/retry/failed attempt. Pending reservations are zero, no halt is set, and the $90 guard remains active. Final authenticated GET reports usage $1.03935069, balance/limit_remaining $98.96064931 and key limit $100: exact agreement with the ledger to reported precision.

A final logging-only correction also carries fallback draw/status onto a separate parser follow-up request. Five recording tests passed, including a forced invalid follow-up. Every existing smoke turn was audited against its raw parse operations and already has the correct applied status; no accepted smoke data are affected. Request fixture hashes are rechecked unchanged.

Preserve `final-runs` at the old pilot source; tag the documentation-complete replacement source `final-runs-v2`. The user starts `./launch.sh replica_N8 0` in the existing govsim tmux shell; the changed resolved config allocates a fresh full attempt and preserves `runs/replica_N8/seed0`. Codex monitors the replacement pilot, reports under B11.2 and stops for review. No later seeds are started here.

---

# Preserved earlier smoke reports
# Fixed-cap smoke validation complete

All six one-cycle, seed-0 Flash-Lite smokes passed `check_data.py` with 1000 null replicates on commit `4fdcbb90f299a937140e7d68c2b9f30bc484745e`. Start and end commits match for every attempt. The common paper profile and `repository_parser_fixed_caps` policy were enabled. Generation/find caps stayed 16000; fresh importance caps stayed 1000. No full Gemini 2.5 Flash run has started.

| Condition | Attempt | Calls | Seconds | Cost (USD) | Truncations | 429s |
|---|---|---:|---:|---:|---:|---:|
| replica_N8 | seed0_attempt4 | 104 | 85.5 | 0.02162450 | 0 | 0 |
| baseline_N8 | seed0_attempt4 | 130 | 112.1 | 0.03789053 | 0 | 0 |
| values_N8 | seed0_attempt2 | 125 | 102.2 | 0.02958089 | 0 | 0 |
| stakes_N8 | seed0_attempt2 | 130 | 114.6 | 0.03534541 | 0 | 0 |
| coord_N16 | seed0_attempt2 | 232 | 173.0 | 0.05303556 | 0 | 3 |
| coord_N32 | seed0_attempt3 | 445 | 370.6 | 0.11822443 | 2 | 4 |

All six lakes collapsed in cycle 1 with final stock zero. This is an observed Flash-Lite result, not a data-validation failure or a full-model result. The first-stakes full-run early-collapse gate remains applicable to the later full study; these are smoke tests.

## Parsing and truncations

- Harvest option parsing succeeded for every agent. Every applicable pre-discussion and perceived-leadership answer parsed successfully, including answers from silent agents. Private-call memory isolation and actual-catch public reporting passed validation.
- Replica nomination parsing failed once in seven decisions (14.3%, above the 3% reporting flag). The original fallback selected Julia. Other conditions had zero nomination failures. No parser was repaired.
- N32 Yusuf had two harvest requests end on length: reported output counts 15893 and 15880. The original parser made its existing next-stage request after the first partial text and parsed option 40 from the second, also partial, response. This is original integer parsing, not proof that the model produced a complete final answer. Both partial responses, fixed caps, costs and length events are retained. No added continuation prompt or length retry loop was used.
- N16 and N32 each had one failed agreed-limit extraction and retained the original -1 fallback. Reflection evidence parsing also produced the original documented failures/defaults: 30, 32, 31, 33, 59 and 110 operations respectively in replica, baseline, values, stakes, N16 and N32. These are separate from harvest, nomination and instrument failure rates.
- Seven 429 events were handled by the existing authorized rate-limit policy; no 402 occurred. All token counters were present in every recorded call.

## Tokens, spend and next gate

The six current attempts total 1166 calls and $0.29570132: 1370024 input tokens, 408468 output tokens, 52092 cached input tokens (3.80% of input), and zero reported reasoning tokens. Reported reasoning zero is provider telemetry, not a claim that responses contain no reasoning text.

Cumulative project ledger spending is **$0.59763131**, including every earlier failed, interrupted and superseded attempt; pending reservations are zero. The $90 guard is active and no halt is set. Final authenticated account GET reports usage $0.59763131, balance and limit_remaining $99.40236869, and key limit $100. The initial $100 balance minus current balance matches the ledger to reported precision. All raw attempts remain preserved.

All 41 offline tests passed; original disabled-override payload fidelity and amended-profile stub/storage checks are documented in TEST_RESULTS.md and FIDELITY.md. The remaining changes before the pilot are documentation only. Tag the resulting frozen commit `final-runs`; the user starts only `./launch.sh replica_N8 0` in the existing govsim tmux shell. Codex monitors and delivers the B11.2 pilot report/transcript, then **STOP**. No replica seeds 1–4 are authorized by this smoke report.

The user has received the requested heads-up before the longer pilot. The Mac must stay awake and connected while it runs.

---

# Preserved historical reports
# Current policy update

The user approved continuing at fixed caps using repository parser behavior. Length finishes and individual parse failures are now logged rather than causing the prior study-wide stop. Original parser follow-up calls/defaults are unchanged, including explicit logging of zero fallbacks. All 41 tests pass. The historical stops below remain preserved evidence; fresh-policy smoke validation is in progress. No long Flash run has started.

---

# Current status: paper-first smoke stopped at 16,000 tokens

All 40 offline tests pass, including six-cycle native stubs for every condition, current prompt isolation, exact inverse-path ties, actual public reports under oversubscription, and disabled-override request fidelity. No long Flash run has started and no `final-runs` tag has been created.

After the user approved paper definitions and prompt alignment, the replica and baseline smokes on commit 7752799 completed without truncation. They are now superseded because their oversubscribed public reports still used requested catches. Actual-catch reporting was corrected and tested on commit 314aa61, leaving all old attempts intact. Those two smoke costs remain counted; replica nomination fallback was 14.3% in that superseded Flash-Lite attempt and is explicitly flagged, not silently repaired.

The largest group was then tested first on the final paper-first profile, to check the earlier blocker before repeating all conditions. `runs/smoke/coord_N32/seed0_attempt2` halted during harvest:

| Field | Value |
|---|---|
| Model | google/gemini-2.5-flash-lite |
| Provider | Google AI Studio, fallbacks disabled |
| Commit | 314aa61ee30262b5b8072298b49ad0bb205d3dfb |
| Affected agent / call | Yusuf / harvest |
| Requested max_tokens | 16000 |
| Reported output / reasoning tokens | 15893 / 0 |
| Finish reason | length |
| Response size | 49037 characters; no final Answer marker |
| Attempt cost | $0.02443260 |

This was a Flash-Lite smoke, not the study's intended Gemini 2.5 Flash model. It does not establish whether the production model would also truncate. The current cap and halt remain unchanged pending user review. A possible diagnostic is a separately authorized **one-cycle** N32 Flash check at the same cap; this would not start the six-cycle long run. The user subsequently clarified that caps stay fixed; the remaining decision is truncation handling, not another cap increase. See SETUP_AUDIT.md for original-repository continuation/default behavior.

Total project spending is **$0.30192999**, including all failed, interrupted and superseded attempts. Outstanding reservations are **$0.00**. Account balance and limit_remaining are **$99.69807001**, the key limit is **$100**, and reported usage is **$0.30192999**, matching the ledger. All raw data is preserved. Remaining smokes and the long pilot have not been started under this final profile.

The user requested a heads-up when preparing the long run so they can commute. That notice is still due once the smoke gate is cleared; the long run is **not ready** at this stop.

---

# Flash-Lite smoke review

All runs below use paid `google/gemini-2.5-flash-lite`, seed 0, one cycle, pinned Google AI Studio with fallbacks disabled. No full Flash pilot has started. Generation/fresh-importance caps remain 8000/1000.

| Condition | Attempt | Status | Calls | Cost (USD) | Result |
|---|---|---|---:|---:|---|
| replica_N8 | seed0 | collapsed | 126 | 0.04406774 | failed retrieval-node-ID validation |
| baseline_N8 | seed0 | halted | 78 | 0.02262374 | Completed run failed data validation; B11 requires review |
| replica_N8 | seed0_attempt2 | collapsed | 113 | 0.03321622 | validated |
| baseline_N8 | seed0_attempt2 | collapsed | 120 | 0.02619029 | validated |
| values_N8 | seed0 | collapsed | 118 | 0.02604069 | validated |
| stakes_N8 | seed0 | collapsed | 132 | 0.03599391 | validated |
| coord_N16 | seed0 | halted | 30 | 0.01605270 | Completion reached the length limit; review required under B11/B14 |
| coord_N32 | seed0 | halted | 32 | 0.02578620 | Completion reached the length limit; review required under B11/B14 |

## Accepted checks

Replica, baseline, values and stakes passed `check_data.py` with its default 1000 null replicates. Harvest and nominee failure rates are zero. Both private instruments parsed at 100% where applicable. All token counters were present. There were no 429/402 errors and no length-limit endings in accepted runs. All four lakes collapsed in cycle 1; this observed outcome was preserved.

## Required decision before continuing

The N=32 smoke had two harvest completions with `finish_reason: length`: Emma (7977 reported output tokens) and Henry (7978), both requesting the unchanged 8000 cap. Their prompts correctly specify the 0–400 fishing range. Both responses continued lengthy step-by-step discussion without reaching a final answer. The shared guard halted N=32 and the concurrent N=16 run. Both attempts and their complete raw responses are retained. No token cap or prompt was changed in response.

B2 fixes generation at 8000 tokens, and B14 reserves a decision to raise it across conditions for the user. The handler conservatively applies its no-truncation guard during smoke testing as well as the pilot. Review is needed before clearing this halt and retrying the interrupted smokes, or authorizing a consistent cap change. The `final-runs` tag has not been created and no full pilot command is ready to start.

## Spending and source

Total project smoke spending, including every failed/interrupted attempt: **$0.22997149**. Outstanding reservations: **$0.00000000**. The shared halt remains set. The initial account balance was $100; the key limit remains $100. The final account GET reports balance and limit_remaining of **$99.77002851**, limit **$100**, usage **$0.22997149**. The $100 initial balance minus the final balance matches the shared ledger exactly to reported precision.


The first logging-only failure was repaired by matching the original Markdown reader's empty-line normalization; native retrieval/storage stayed unchanged. Initial attempts were preserved. Final stub suite: 34 tests passed. The accepted N8 smoke commits are dc5d025 (replica/baseline) and 09ea3b2 (values/stakes); the interrupted larger smokes use 246d699. Later commits before the pilot changed only launcher/error safeguards and reports, with no full run performed. No condition has mixed full-run commits because no full runs exist.

