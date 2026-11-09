# Changes relative to the pinned original

Baseline: `8cf0aba9efe0b4592f395d9a66e6cfff3cec9a26`.

| File / hunk | Specification / authorization | Purpose |
|---|---|---|
| `METHODS.md` (new file) | B1.2 | Preserve the supplied binding specification unchanged. |
| `AGENTS.md` (new file) | B15; user-supplied repository instructions | Preserve the supplied agent instructions unchanged. |
| `QUIRKS.md` (new file) | B10.4 | Record observed original behavior and explicit user decisions, including integer regeneration. |
| `simulation/persona/persona.py`: remove the obsolete constructor parameter and its arguments in the retrieval/storage constructor calls | B1.3 / B10.4, explicit user-authorized exception | Repair initialization signatures without changing retrieval or storage implementations. This is an exception to original-source fidelity, applying to every condition including replica. |
| `CHANGES.md` (new file) | B10.8 | Map each change to its source requirement or explicit exception. |
| `SETUP_AUDIT.md` (new file) | B1.1-5 / B10 | Record source behavior, the call inventory, setup checks, validation and unresolved decisions before implementing interventions. |
| `simulation/interventions.py` (new file) | B5 | Copy all seven exact intervention texts from the unchanged specification. |
| `tests/test_intervention_texts.py` (new file) | B9 | Compare all seven B5 constants character for character with their fenced specification texts. |
| `simulation/persona/cognition/act_prompts.py`: guard the original mayor line | B3, user clarification | Omit the line when `agent.act.drop_mayor_line` is enabled and the agenda is None, empty, or the original no-guidance sentinel; preserve it with the flag off. |
| `tests/test_mayor_prompt.py` (new file) | B9 | Execute the actual harvest user-prompt block and compare it against pinned source with absent/disabled/enabled flags and absent/real agendas, without model calls. |
| `simulation/intervention_randomness.py` (new file) | B6, approved N-specific opener interpretation | Define the ordered name pool and dedicated keyed draws, independent of the original random generators. |
| `tests/test_intervention_randomness.py` (new file) | B9 | Verify ordered names, horizon spread/ranges, repeatability, draw isolation and full-pool openers at larger N. |
| `constraints-macos.txt` (new file) | B1 / B10, explicit user authorization | Capture the Mac environment after the approved Transformers 4.51.0 compatibility resolution, preserving the default fixed pins and leaving original requirements files unchanged. |
| `simulation/persona/cognition/converse_prompts.py`: guard the disinformation/agenda line | B3 | Omit the specified truthfulness line only when its dedicated flag is on. |
| `simulation/persona/cognition/converse.py`: neutral announcement and seeded opener branches | B3 / B5 / B6 | Preserve public reporting, change framework identity/text only under the neutral flag, and select a keyed opener only under its own flag; retain original branches when disabled. |
| `simulation/phases/discussion.py`: optional seed/cycle arguments | B3 / B6 | Supply one-based cycle and experiment seed only when seeded openers are enabled. |
| `tests/stub_llm.py` (new file) | B9 | Provide deterministic canned transport responses through the original wrapper and Pathfinder parser, capturing actual request parameters without external calls. |
| `tests/test_simulation_stub.py` (new file) | B9, explicit user clarifications | Exercise six-cycle native simulation and public neutral-report behavior; expect original 8000/1000 token caps and the unchanged reflection-regex fallback. |
| `simulation/measurement_prompts.py` (new file) | B4.4 / B4.5 / B9 | Construct private prompts from the shared original utterance prefix plus the approved public-report context, parse once, and resolve names without storing results in memory. |
| `simulation/persona/cognition/converse.py`: measurement branches and final conversation metadata | B4.4 / B4.5 / B8 | Call instruments around agent discussion before reflection, and retain observational cycle/turn metadata outside prompt and memory construction. |
| `simulation/persona/cognition/utils.py`: name renderer and system/memory name formatting | B4.6 | Render current remaining-month tags in system-generated text; leave free text unchanged. Append the exact household instruction for stakes identities only. |
| `simulation/persona/cognition/utils.py`: v3 lake quantity parameters | B4.7 | Scale capacity, catch range and worked-example lake quantities while preserving N=8 text byte for byte. |
| `simulation/persona/cognition/leaders.py`: SVO_FISHERMAN_TASK and focal selection | B4.3 | Change only the specified opening phrase for the focal persona; preserve original SVO content elsewhere. |
| `simulation/persona/cognition/leaders.py`: report name rendering | B4.6 | Add current tags to system-generated report labels without changing requested-catch report semantics. |
| `simulation/persona/cognition/converse_prompts.py`: participant/nominee tags and stakes-only identity resolution | B4.6 | Display current tags, then strip them before stakes-only case/unique-prefix resolution; retain the original non-stakes select path and all original regexes. |
| `simulation/persona/cognition/store_prompts.py`: name placeholders only | B4.6 | Render system-generated perspective labels with current tags; preserve every other character and operation in these original prompts. |
| `simulation/tenure.py` (new file) | B4.6 / B6 | Precompute identity horizons, rebind fresh personas to existing household slots and rebuild references without rebuilding the environment. |
| `simulation/run.py`: focal SVO, scale, tenure and cycle hooks | B4.3 / B4.6 / B4.7 / B8 | Attach intervention state behind flags and invoke observational recording before/after existing phases. The original environment's allocation and regeneration generators remain unchanged. |
| `simulation/environment/concurrent_env.py`: threshold lookup | B4.7 | Read a configured scaled collapse threshold, defaulting to the original 5. |
| `simulation/main.py`: existing-path abort | B7 | Abort before deleting an existing run directory. |
| `simulation/study_config.py` and six condition YAMLs plus four values-seed YAMLs (new files) | B2 / B4 / B7 | Copy the original config, change specified fields only, set condition-specific group names and rotate the agenda through YAML persona goals. |
| `simulation/recording.py` (new file) | B8 / B10 | Observe existing retrieval outputs/scores, request/parse operations and cycle states, write compressed raw data, memory snapshots and final metadata, and redact secrets. |
| `simulation/budget.py` (new file) | B12 | Share actual spend, outstanding reservations and halt state across processes; reduce active seeds after persistent transient reservation failures. |
| `simulation/openrouter_handling.py` (new file) | B2 / B8 / B12 and approved wrapper interpretation | Pin routing, observe raw SDK results/HTTP errors, recover actual generation costs, honor retry delays and set shared halts; do not change original wrapper internals. |
| `tests/test_conditions.py`, `tests/test_measurements.py`, `tests/test_recording.py`, `tests/test_budget.py`, `tests/test_openrouter_handling.py` (new files) | B9 | Verify six-condition native runs, config goals, prompt fidelity, private-call isolation, raw logging, billing reservations and local simulated API error handling. |
| `DATA.md` (new file) | B8 | Document standardized files, units, raw-call and memory semantics, applicability of null fields and the data lifecycle. |

## Approved interpretations implemented

- B6 / B9: match non-replica N=8 openers by household slot; N=16 and N=32 choose reproducibly from their full participant lists.
- B2 / B10 / B12: preserve original wrapper internals and add required handling around them; provider-routing parameters are an explicit exception to original API-payload equality.
- B9 mechanics: expect `int(min(capacity, post_harvest_stock * regen_factor))`, preserving the original regeneration truncation.
- A10: use directed study influence graphs; leave AgentElect's original analysis untouched.
- B4.4: retain the public AgentElect report and repeat that public report in private measurement context; preserve the shared original prefix and allowlist the explicit added report context.
- B15: the user selected this Mac for experiment execution. Full Flash runs still require user launch in tmux under B11.
- B1 / B10: the user selected default Mac dependency pins plus Pathfinder's declared dependencies, with the repository's PyTorch 2.2.0 pin. Dependency declarations remain unchanged.
- B1 / B10: the user authorized Transformers 4.51.0 and compatible unpinned packages, preserving every selected fixed pin. Simulation import and `pip check` now pass.
- B4.5: ask all present agents, including those who never spoke.
- B7 / B11: skip validated completed seeds and restart failed seeds in fresh attempt directories, preserving original data.
- B12: the $90 guard counts all project API spending, including smoke tests, retries, failed attempts and later judge calls.
- B2 / B9 / B14: preserve original generation/importance caps of 8000/1000 and the original reflection-regex fallback; make tests explicitly expect both.
- A10 / B11: proposal matching uses 0.000001-ton tolerance, splitting credit among matches; no agreed numeric limit means undefined adoption. Validate inputs for post-experiment judging/embedding without making paid judge calls during checks.
- A10 / B11: record undefined eigenvector centrality explicitly if the directed graph has no unique result; retain degree, betweenness and airtime measures.

## Remaining B8–B12 implementation hunks

| File / hunk | Requirement | Purpose |
|---|---|---|
| `check_data.py`, `study_analysis.py` | A10 / B11 | Validate immutable inputs, calculate available measures, implement the user-defined nomination-chain and conditional-target nulls with separate recorded RNG keys, and validate deferred-analysis inputs without paid judging. Undefined directed eigenvectors are explicit. Full baseline seed 0 must pass the 97% instrument gate even on resume. |
| `run_study.py`, `launch.sh`, `tools/launch.py`, `tools/__init__.py` | B7 / B11 / B15 | Separate stub/smoke/full modes, retain native setup seeding, enforce clean source, store Hydra config, bound concurrency, preserve failed attempts and skip validated completions. Full Flash starts only from the user's tmux command. |
| `tools/with_tmux_key.py` | B0.4 / B1.4 / B15 | Read the user-provided key from tmux into process memory without printing or writing it. Network still requires ordinary approval. |
| `tools/manifest.py`, `tools/build_derived.py` | B8 / B13 | Checksum raw attempts and build the seven requested Parquet tables in a separate analysis environment. Calls index omits all completion/request text, including partial retry completions. |
| `tools/fixture_run.py`, `tools/build_fidelity.py`, `tests/golden/*`, `FIDELITY.md` | B9 / B10.9 | Reproducible pinned-reference API request comparison, all-condition diffs, payload hashes and actual rendered excerpts. Reference receives only the approved startup repair. |
| `tests/__init__.py`, `tests/test_analysis.py`, `tests/test_config_allowlist.py`, `tests/test_mechanics.py` | B9 / A10 | Make transport fixtures importable; test analysis rules, copied-YAML allowlist, native unseeded regeneration distribution and scaled collapse thresholds. |
| `simulation/measurement_prompts.py`: local end-of-text capture and parse observation | B4.4 / B4.5 / B8 | Capture complete new instrument answers without changing API payload parameters; attach structured parse outcome before flushing the chain. |
| `simulation/recording.py`: start/end commit, path-derived IDs, turn links, raw SDK capture | B7 / B8 | Prevent cross-root ledger ID collisions, detect source changes during runs, preserve SDK originals and unknown token counters, and link every turn to its transport calls. |
| `simulation/persona/cognition/converse.py`: offered nominee options and raw nominee | B8 / A10 user-defined nulls | Preserve actual options per turn for the nomination-chain null and record the raw nominated name separately from identity. |
| `simulation/openrouter_handling.py`: response journal, partial 429 accounting, metadata recovery | B8 / B12 | Preserve raw transport evidence immediately, count billed partial retries and halt on unreconciled spending or routing/length mismatches. |
| `tests/stub_llm.py`, `tests/test_recording.py`, `tests/test_openrouter_handling.py`: extra cases | B9 | Exercise stakes nominations with tags/bare names/case/partial names, instrument parse coverage, and partial-response retry costs. |
| `RUNBOOK.md`, `TEST_RESULTS.md` | B11 / B15 | Record validation commands, execution division of labor, resume semantics and STOP gates. |
| `.gitignore`: study run and derived paths | B8 | Keep write-once raw logs, budget database and derived output out of normal source commits pending the pilot storage decision. |

The A10 coordination nulls keep the recorded opener and utterance count for airtime, drawing each subsequent speaker uniformly from that turn's offered nominees. Influence fixes actual speakers and eligible mention/nomination counts and redraws targets among other present agents. The full-capacity efficiency benchmark sums `capacity * (factor - 1) / factor` over realized cycles. These implement the user's explicit clarifications; AgentElect supplied neither null comparison nor this efficiency calculation.

- B8 smoke repair: `simulation/recording.py` matches observed retrieved text to node IDs using the original Markdown reader's empty-line normalization and stable duplicate order, without changing retrieval or storage. `tests/stub_llm.py` and `tests/test_recording.py` exercise multiline memory descriptions end to end. The first two paid smoke attempts are preserved and rerun in fresh directories; all costs remain in the shared ledger.

- B11 launcher audit: a halted first stakes attempt does not satisfy the first-completed-run gate. Keep its restart alone and apply the early-collapse STOP rule to the first finished attempt. Checked the actual gate block with temporary failed/collapsed metadata fixtures; no full worker was started.

- B12 final audit: an error completion with unknown actual cost halts and retains its worst-case reservation instead of assuming zero cost. The local SDK test verifies this conservative accounting path; paid smoke attempts have not exercised this error path.

- B11/B14: `SMOKE_REPORT.md` records accepted and interrupted Flash-Lite attempts, preserved raw-data paths, costs and the token-limit decision required before continuing. No caps, original prompts or simulation behavior were changed.

## User-approved methods amendment and paper audit

- A5 / A11 / B2 / B9 / B10 / B11 / B14: amend METHODS.md, at the user's explicit request, to specify 16000 generation/find/private-instrument tokens consistently across all conditions, retaining 1000 fresh importance ratings. Distinguish the study override from untouched original wrapper defaults and permit only that payload difference in fidelity checks. Rerun all six smokes after implementation; retain prior data and spending. The parent METHODS.md copy is synchronized, and exact B5 strings are unchanged.
- B1.3 / B10.4: extend SETUP_AUDIT.md with a primary-source paper/code cross-check and add newly observed original quirks to QUIRKS.md. Record threshold, centrality, recall, altruistic sampling, prompt and timing differences without changing their implementations or resolving new scientific choices automatically.
- This explicitly supersedes earlier "unchanged METHODS.md" and 8000-cap preservation statements only for the approved token-cap amendment. Historical smoke results, payload hashes and previous approvals remain records of their original states.

## Common paper-first profile (explicit user approval)

| Files / hunks | Requirement / authorization | Purpose |
|---|---|---|
| `METHODS.md` and parent copy | User paper-first hierarchy; B2/B9/B10/B14 amendment | Specify all five paper definitions, aligned prompt semantics, guard boundaries and exceptions; retain exact B5 texts and deliberate arms. |
| `simulation/paper_definitions.py` (new) | Amended B2/B6 | Paper threshold, isolated keyed SVO ranges and exact study instruction strings. Honesty is transcribed; deception/privacy are disclosed semantic paraphrases. |
| Ten study YAMLs | Amended B2/B7 | Enable common environment/agent paper flags and 16000 generation cap in every arm, including replica. |
| `concurrent_env.py` threshold guarded return | Amended B2 | Use the full-capacity equation without an extra floor; preserve original formula when disabled. |
| `leaders.py` optional sampling parameters and paper prompt branch; `run.py` flag/seed/identity setup; `tenure.py` successor properties | Amended B2/B6 | Use altruistic bounds through 90 with dedicated keys, add focal-only privacy, align SVO prose, and propagate common truthfulness/profile state to successors. No new study leaders are added. |
| `converse.py`, `measurement_prompts.py` recall branches | Amended B2/B4 | Request ten memories while retaining original retrieval internals and private-call isolation. |
| `act_prompts.py`, `converse_prompts.py`, private prefix; `utils.py` system branch | Amended B2 | Add common paper honesty to strategic prompts and remove only the extra fixed-doubling sentence, preserving original disabled branches and separate baseline leader-cue removal. |
| `simulation/study_models.py` (new), `recording.py` inheritance/effective metadata | Amended B2/B8 | Apply 16000 generation/find caps outside the untouched original wrapper; fresh importance selections remain 1000. Log profile and requested retrieval limits. |
| `study_analysis.py` | Amended A10/B2 | Use incoming degree and directed inverse-weight fractional betweenness, including exact rational ties and matching nulls; explicitly select legacy conventions for historical profiles. |
| `check_data.py`, `run_study.py` | B8/B11 | Check amended threshold/caps/recall and compare resolved config before skipping any old completion. Preserve all original attempts. |
| `tests/test_paper_definitions.py` (new), analysis/condition/measurement/config/stub tests | B9 | Verify boundary cases and both paths, exact tied-path credit, keyed bounds, semantic/private prompt changes, current instrument isolation and captured caps. |
| Fixture helpers, gold diffs and FIDELITY.md | B9/B10 | Prove disabled-override byte fidelity separately from approved study deviations; capture all six amended study payload sets. |
| DATA.md / RUNBOOK.md / SETUP_AUDIT.md / QUIRKS.md / TEST_RESULTS.md | B8/B10/B11 | Update current schemas, semantics, verification and historical-versus-current evidence. |

No original reflection regex, retrieval scores, allocation algorithm, regeneration truncation or dependency pin was repaired or upgraded. The user-approved paper changes are common across all arms. Legacy files and raw attempts remain immutable; old validation reports do not establish success for the new profile.

- Paper-first / B2/B3/B8: `simulation/phases/harvesting.py` chooses actual allocations for the public renderer only under the common override, retaining native requested-catch statistics and original disabled behavior. `check_data.py` verifies every report line against actual catch; `tests/test_recording.py` exercises oversubscription. Earlier amended smokes that still reported requested catches are preserved and superseded, with all spending retained.

- B11/B14 review report: update SMOKE_REPORT.md and TEST_RESULTS.md with the final-profile N32 16000-token stop, preserved superseded attempts, parse-fallback flag and reconciled $0.30192999 total. Keep the halt and caps unchanged; no full run or pilot tag is created.

- B10/B14 fixed-cap review: document the original adapter's discarded finish reason, incidental parser continuation and zero fallback in SETUP_AUDIT.md / QUIRKS.md, and clarify the current smoke report. Three local fake-SDK cases used the unchanged original path at 8000 tokens per request; no model call or runtime-policy change occurred. Study caps remain 16000/1000.

## User-approved repository truncation behavior at fixed caps

- B2/B11/B12/B14: update METHODS.md and parent copy to keep 16000/1000 caps fixed, continue original parsing after length/parse failures, retain the native follow-up/default behavior, and preserve scheduled review and financial halts. No new truncation retry or prompt is added.
- `simulation/openrouter_handling.py`: replace only the added length halt with a logged type=length event, preserving raw response return, cost settlement and other error/routing safeguards.
- `simulation/recording.py`: record truncated flag, policy metadata and observed fallback values without changing returned parser results. `check_data.py`: accept length finishes, summarize length/parse/fallback counts. `run_study.py`: do not reuse prior-policy completions.
- `tests/test_truncation_behavior.py` (new): exercise unchanged adapter/parser with a local SDK double across all three continuation/fallback cases and verify fixed caps, billed-call counting, no halt, raw length evidence and labeled zero defaults.
- DATA.md / RUNBOOK.md / SETUP_AUDIT.md / QUIRKS.md / TEST_RESULTS.md / SMOKE_REPORT.md: distinguish the authorized continuing policy from historical length-stop attempts. All original raw attempts and costs remain preserved.

- B8/B10/B11: SMOKE_REPORT.md / TEST_RESULTS.md / RUNBOOK.md record all six validated fixed-cap smokes, original parse/default outcomes, cumulative spending, retained historical attempts and the user-started pilot handoff. This final preparation changes documentation only; simulation source remains the validated 4fdcbb9 source.

## B2/B5/B6/B10/B11 neutral study amendment (user approved after initial pilot)

- METHODS.md / parent copy: explicitly supersede inherited leadership cues and first-name fallback, specify exact count text and per-turn RNG key, preserve the old pilot/tag and require replacement smokes/pilot.
- All ten study YAMLs: `agent.neutral_study` enables the common amendment; original configs/disabled paths retain pinned behavior.
- `interventions.py`, `utils.py`, `run.py`, `tenure.py`: exact actual participant-count statement in general prompts, including successor identities.
- `act_prompts.py`, `leaders.py`, `converse.py`, `converse_prompts.py`: remove scripted mayor/leader roles, use the neutral report in replica too, and replace speaker-endorsement instructions with a neutral sustainability task. No agent-generated free text is rewritten.
- `discussion.py`, `intervention_randomness.py`, `converse_prompts.py`: pass seed/cycle to all neutral conditions and use uniform keyed fallback among originally offered names, including self; preserve parsing and valid nominations.
- `recording.py`, `check_data.py`: record/check neutral profile and nomination fallback key, options, candidate and applied status, preserving raw failure evidence.
- Stub transport, condition/config/exact-text/recording tests: verify all six six-cycle conditions, eight exact constants, neutral/count prompt isolation, stakes succession and forced invalid-nomination routing at N8/N32 without global RNG calls.
- `tools/build_fidelity.py`, regenerated golden diffs and FIDELITY.md: disclose new common overrides and retain byte-identical disabled-path control. DATA.md / RUNBOOK.md / QUIRKS.md / TEST_RESULTS.md / SMOKE_REPORT.md document the new schema, source version and preserved superseded results.

- B8/B10/B11: record six validated neutral-profile smokes and reconciled spending, the N32 partial-response 300-ton request/collapse, one applied random nominee fallback (Everyone to Tariq), and handled 429 counts. Preserve the initial pilot and original final-runs tag; prepare only the user-started replacement pilot.

- B8/B9: attach the same nomination fallback metadata after select when parsing creates a separate SDK request; extend forced-invalid tests to that follow-up case. Five recording tests pass; audit confirms all six existing paid smokes already have correct raw/fallback status, with no affected data or payload changes.

## B2/B5/B6/B8/B9/B10/B11 two-stage discussion and hidden contextual judge

- METHODS.md / parent copy: record the approved mandatory opening, final-opening handoff, hidden contextual judge, 50-total-message cap, separate running intervention table and stage-specific measures/nulls. Preserve prior attempts/tags; replacement source uses final-runs-v3.
- All ten study YAMLs: guarded `agent.round_robin_discussion` enables the protocol in every condition, including modified reference.
- `interventions.py`: four exact B5 stage/judge task constants. `intervention_randomness.py`: common keyed opener plus separately shuffled remaining household slots.
- `two_stage_discussion.py` (new), guarded entry in `converse_prompts.py`, turn loop in `converse.py`: guarantee each opening voice, ignore opening close attempts, enable last-opening nomination, retain valid-name patterns, and use a separately recorded judge chain before routing invalid nominees. Preserve native converse response logs.
- Judge may resolve intent or choose contextually; unclear/malformed/ineligible outputs use recorded uniform random choice. No judge material enters the conversation, agent context, memory or private instruments. Transport/financial safeguards and fixed caps remain.
- `recording.py`: new call type, metadata protocol flag, opening order/keys/handoff, stage/source turn fields, per-run intervention JSONL and append-only shared SQLite table. `tools/nomination_table.py` (new) exports a readable TSV snapshot.
- `study_analysis.py`, `check_data.py`: measure each phase separately, preserve mandatory turns in the null, redraw the initial nomination handoff, validate coverage/cap/routing/intervention call links, and report judge/random counts.
- Twelve-constant/config/legacy-profile tests, new `test_two_stage_discussion.py`, stub transport and fidelity generator/golden fixtures: verify opening coverage, cap, valid bypass, judge context/intent choices, random fallback, privacy, table append behavior and disabled-path byte fidelity.
- DATA.md / RUNBOOK.md / QUIRKS.md / TEST_RESULTS.md / SMOKE_REPORT.md describe protocol version, limits, new schemas and preserved historical evidence.

- B8/B10/B11: document all six validated two-stage smokes, 47 passing tests and original-path fidelity, initialized empty running intervention table, preserved N32 harvest truncations/collapse, handled 429s and exact $1.40327705 ledger/account reconciliation. Freeze v3 for a user-started replacement pilot; implementation stays identical to the paid-smoke source.
