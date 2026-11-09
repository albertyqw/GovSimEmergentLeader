# B1 source audit and setup status

## Verified setup

- Fork: `albertyqw/GovSimEmergentLeader`, parent `rfaulkner/GovSimElect`.
- Branch: `emergent-leadership`, based on `8cf0aba9efe0b4592f395d9a66e6cfff3cec9a26`.
- Initial commit `567703b` adds only unchanged `METHODS.md` and `AGENTS.md`; ancestry and byte comparisons passed, and the branch was pushed.
- `.env` is already ignored by the original `.gitignore`; no edit is needed.
- Execution host: the user selected this Mac, with working directory `/Users/yongqi/Documents/emergent_leaders/GovSimEmergentLeader`. The initial shell uses Python 3.10.11; the isolated `.venv` uses the available Python 3.11.16 interpreter.
- `OPENROUTER_API_KEY` is absent from this session's environment. No authenticated key/balance request or paid model call has been made.
- The user selected default Mac requirements plus Pathfinder's declared dependencies, retaining all default pins and the repository's PyTorch 2.2.0 / torchvision 0.17.0 / torchaudio 2.2.0 pins. After the recorded initial failure, the user authorized Transformers 4.51.0 and compatible versions of unpinned dependencies. The simulation now imports successfully, `pip check` passes, and all nine fixed pins are unchanged. Original dependency declarations remain unchanged; `constraints-macos.txt` captures the installed environment.

## Public OpenRouter catalog check

Both exact paid model IDs are listed. Public API responses were fetched read-only; sandbox DNS failures were followed by approved network escalation.

| Model | Standard input / million tokens | Standard output / million tokens | Listed upstream provider |
|---|---:|---:|---|
| `google/gemini-2.5-flash` | $0.30 | $2.50 | Google AI Studio |
| `google/gemini-2.5-flash-lite` | $0.10 | $0.40 | Google AI Studio |

Sources: `https://openrouter.ai/api/v1/models` and each model's `/endpoints` endpoint. The endpoint responses also list flex and priority variants with different prices. These are setup observations, not a serving guarantee or a finalized routing policy. Recheck before paid runs. The standard Flash input rate is higher than A12's approximate $0.19; use live endpoint rates and realized costs for projections.

## Cycle and model-call inventory

The runner builds phase objects from the YAML. Policy-making and election return immediately when `leader_candidates` is empty; none of their model calls execute for the no-leader population. The native environment uses zero-based rounds; B8's cycle numbering will need an explicit one-based mapping.

1. **Harvest:** all agents perceive the lake event, retrieve up to 10 memories, and make their private decisions concurrently. Each harvest prompt performs a `gen` for reasoning and a `find` for the numeric catch. Pathfinder can satisfy multiple parsing operations from one returned completion, so these operations are not necessarily separate API requests. Lake and personal catch events are `always_include` and bypass model-based importance scoring. Allocation and environment stepping happen sequentially after all desired catches have been collected. With zero fish, the original branch skips the harvest model call.
2. **Report:** the no-leader report is deterministic and uses no LLM. It is passed to the discussion and rendered as a framework utterance, not put in restaurant `current_context`. The original report contains requested catches, as noted in `QUIRKS.md`.
3. **Agent discussion:** the original opener is selected by global `random.choice`. Each turn retrieves up to 5 memories and performs `gen` for the utterance, `select` for ending, and, if continuing, `select` for the nominee. Those selections may consume the same completion. Framework messages count toward the 50-message cap, leaving at most 49 agent turns with the ordinary single no-leader announcement. The loop always executes at least one agent turn.
4. **Discussion framework calls:** after the turn loop, a summary `gen` and agreed-limit `gen`/`find` run on the framework wrapper. These occur inside the conversation component, before the environment is stepped to home.
5. **Discussion memory and reflection calls, for every participant:** chat importance rating (`select`), planning thought (`gen`) plus its importance rating (`select`), and memorization thought (`gen`) plus its importance rating (`select`). An agreed-limit memory is added with `always_include` and no importance model call. This processing already happens inside `converse_group`, before the separate home reflection phase. The B4.5 private leadership question must therefore be inserted before these per-agent reflections, rather than simply before `ReflectionPhase`.
6. **Home reflection:** all agents retrieve up to 10 memories for the focal point `harvesting`; insight generation makes a variable number of `gen` operations, with optional justification continuations. Each returned insight is stored after a model-based importance rating. Home reflection runs concurrently across agents, followed by sequential environment steps.
7. **Transition:** the last home step checks collapse on the post-harvest stock, increments the round, regenerates with `int(min(capacity, stock * factor))`, then draws the next factor and updates the sustainability threshold. Cycle 1 uses factor 2.0. The environment's own `RandomState(None)` is unseeded; it serves allocation and regeneration. Do not change its draws.

New B4.4 elicitation calls belong after the report and before agent discussion. New B4.5 calls belong after the turn loop and before conversation reflection. Each is one standalone call per eligible agent, with no storage or later prompt propagation. Eligibility for B4.5 still needs clarification for silent participants.

## Native storage and logging

- `simulation/main.py` builds a results path from experiment and run names and deletes an existing directory. B7's abort guard and condition-specific paths remain to implement.
- `consolidated_results.json` is newline-delimited JSON despite its extension. It logs initialization/config, persona identities and SVO information, harvest/round statistics and end status. In no-leader runs, the per-round election logging block is skipped and a final election-shaped record is still written.
- `responses.json` is also append-only JSON records despite its extension. It stores parsed harvest reasoning/options and discussion responses, ending flags and nominees.
- `log_env.json` is a JSON array produced from DataFrames, with requested and actual catches, before/after-harvest stock, conversation rows, extracted limits and HTML interactions.
- Persona memories are maintained in `MEMORY.md`; `memory.save()` is a no-op. In-memory nodes retain IDs, types, importance and expiry. Retrieval reads the Markdown, filters expiry, scores and deduplicates entries, returning only date/text tuples. Logging the richer B8 metadata requires observation before that information is discarded, without changing retrieval results.
- The original retriever ignores focal-point text. Its recency scores follow the existing entry order; preserve the algorithm.
- W&B tracks model-operation traces and game metrics. It is not a substitute for B8 raw HTTP request/response records. The original wrapper catches errors and returns defaults and labels some failed operations successful; B12 handling must act below that swallowing layer while preserving wrapper internals as approved.
- Pathfinder's OpenRouter adapter returns completion text and discards the rest of the response. B8 must capture raw completions, usage, costs, served provider/model and errors at the SDK request boundary. Count actual API attempts separately from local parsing operations.

## Analysis audit

- `social.py` reads native logs for six-cycle metrics but hardcodes paths, model choices, seeds and agent counts. Its social graphs are undirected, despite A10 describing directed graphs; see `QUIRKS.md`.
- Its harvest records originate from requested catches, with aggregate welfare capped by a reconstructed resource limit. B8 supplies actual allocations for this study's outcomes; the replica comparison must disclose reconstruction choices.
- `social.py` treats six observed harvest cycles as survival; a collapse on the sixth cycle needs explicit handling against actual collapse flags. Its standard-error formula differs from the usual sample-standard-deviation divided by square root of sample size.
- The dashboard modules (`app.py`, `group.py`, `details.py`, `preprocessing.py`, `plots.py`, `utils.py`) include legacy five-agent/twelve-month assumptions. They must not be run unchanged to establish this study's six-cycle outcomes. Original analysis code is not modified.
- `merge_social.py` aggregates hardcoded model/population outputs; it does not implement B8's cross-run derived tables.

## Approved initialization repair validation

Static validation derives signatures and caller arguments from the original and working Python ASTs and uses `inspect.Signature.bind` without importing simulation dependencies:

- Original: all 4 affected constructor call sites fail (2 agent creations, retrieval, storage).
- Working tree after the user-approved repair: all 4 calls bind successfully.
- Changed `persona.py` compiles successfully with Python's `compile` function.

This verifies argument compatibility, not a complete runtime or stub run. Full runtime validation remains pending the environment setup and B9 stub harness.

## Clarifications after the audit

- The user approved removing the mayor cue. Treat the no-leader sentinel as absent only behind the new `agent.act.drop_mayor_line` flag. Prompt-prefix checks against pinned source pass with the flag missing or off; enabling it removes only the specified line for None, empty, or sentinel agendas and retains genuine agendas.
- Retain the original public fishing report in the framework announcement. Repeat the same public report in private measurement context so elicitation has the required information before discussion; preserve the original shared prompt prefix.
- The user approved directed study influence graphs; original analysis code stays untouched.
- The user selected this Mac for experiment execution and default Mac dependency pins. User launch of full Flash runs and every STOP gate still apply.

## Initial implementation checks

- B5 constants were copied from `METHODS.md`, which remains byte-identical to the supplied file.
- `.venv/bin/python -m unittest discover -s tests -v`: all 10 focused tests passed (exact texts, three mayor-prompt fidelity cases and six randomness/name checks). These are focused checks, not the full B9 stub suite or API payload verification.

## Initial runtime import failure and approved resolution

- Installation of the approved dependency set succeeded, with no fixed pins changed. `pip check` reports no broken declared requirements.
- Import-only check: `import simulation.run` with W&B disabled. This neither starts a simulation nor instantiates the API model.
- Transformers 5.22.2 reports that PyTorch >=2.6 is required, disabling the installed PyTorch 2.2.0 integration. The subsequent sentence-transformers import fails with `NameError: name 'nn' is not defined` in Transformers' pipeline-parallel module.
- The failure was a runtime compatibility issue that package metadata resolution did not detect. Work paused until the user authorized the compatibility resolution.
- Installing Transformers 4.51.0 together with the original requirement sets and fixed pins resolved sentence-transformers 5.7.0, huggingface-hub 0.36.2 and tokenizers 0.21.4. No selected fixed pin changed. Importing `simulation.run` now passes.

## First actual stub-run results and approved original behavior

- The real runner, environment, agents, memory stores, prompt builders, wrapper and Pathfinder parser execute against a canned transport stub. No OpenRouter client or external model is used.
- A six-cycle N=8 replica stub completed, produced all 48 actual catches of 2 tons, and created native memory/log files. A strict assertion that every API request has an 8000-token cap failed: original fresh importance-rating requests use 1000.
- A separate one-cycle neutral-cue stub test passed: the report is public, its body is unchanged, the framework is Announcer, the opener matches the dedicated slot draw, and mayor/truthfulness cues are absent from captured prompts.
- One-cycle diagnostics: 45 requests at 8000 tokens and 32 importance-rating requests at 1000. Eight original insight-regex warnings were observed, caught by the original wrapper's fallback. Details are in `QUIRKS.md`.
- The user approved preserving both the original token caps and reflection-regex behavior. Tests now explicitly expect 8000-token generation, 1000-token fresh ratings and 48 original regex warnings in the six-cycle N=8 replica. No simulation cap or original reflection regex has been modified.

## Additional user decisions

- Ask every present agent the private leadership question, including silent agents.
- Resume the launcher by skipping validated completions and restarting failed seeds in fresh attempt directories, preserving failed originals.
- Count all project API spending toward $90, including smoke tests, retries, failed attempts and later judge calls.

Subsequent user answers resolved the analysis definitions; current acceptance evidence is in TEST_RESULTS.md.

## Subsequent implementation progress

- Private pre/post discussion calls are implemented. A controlled one-cycle comparison adds exactly 16 transport calls at N=8 and leaves every MEMORY.md byte-identical; silent agents are included.
- All six conditions complete six-cycle native stub runs. The values agenda rotates through seed-specific YAML; focal SVO and fisherman text are isolated. Coordination lake quantities scale, with N=8 system text checked byte for byte against pinned source.
- Stakes swaps personas between cycles while retaining the same environment and eight household slots. Successors start empty and all references are rebound. Remaining-month tags and the exact household instruction appear in system-generated prompts.
- Observational recording is implemented. Its six-cycle stakes test verifies every actual transport request is captured, 48 full memory snapshots exist, identity/household totals agree and the original parse failures are explicitly identified.
- Process-shared budget reservations, routing and SDK error handling pass local-double tests, including billed partial 429 retries. Paid smoke testing follows the source freeze.
- The user approved tie-aware adoption, deferring paid judge work until after the experiment, and explicit undefined eigenvector status. AgentElect contains no coordination random-allocation null implementation. The user specified a nomination-chain airtime null and conditional random-target influence null; both are implemented with recorded separate RNG keys.

- The final pre-smoke suite passes 33 tests. Fixed-state request comparison matches the original replica byte for byte; all six condition diffs are stored in tests/golden. Manifest and seven-table Parquet conversion work on stored stub data. See TEST_RESULTS.md and FIDELITY.md for reproducible evidence.


## Paper cross-check — 8 November 2026

Compared the main experimental specification, mathematical definitions, Tables 8–9 and Appendices B, C and E with pinned commit `8cf0aba9efe0b4592f395d9a66e6cfff3cec9a26`. Code line numbers below are working-tree navigation references; the relevant original functions were checked against `git show 8cf0aba:PATH`. The current paper is [arXiv v2, revised 20 April 2026](https://arxiv.org/abs/2604.11721v2); earlier token verification used v1. The relevant token statement and benchmark rows also occur in v2. This is a source audit, not evidence that the pinned commit generated the published results. That commit predates the paper; the exact experiment revision and serving settings remain unverified.

### Newly confirmed differences with practical consequences

| Item | Paper specification | Pinned implementation / current study consequence |
|---|---|---|
| Sustainability threshold | `max((S*rho - M)/(N*rho), 0)` — [Definition 3.2](https://arxiv.org/html/2604.11721v2#S3.SS3) | `simulation/environment/concurrent_env.py:228-238` computes `int(max((rho-1)*S/(N*rho),0))`. It preserves current stock, rather than necessarily refilling to capacity. At S=50, M=100, rho=2, N=8, these are 0 versus 3; at full stock, 6.25 versus 6 because of truncation. Current over-usage uses the native threshold. Changing the analysis definition needs review; original environment behavior is preserved. |
| Degree | Weighted incoming links — [§4.5.2](https://arxiv.org/html/2604.11721v2#S4.SS5.SSS2) | `simulation/analysis/social.py:528-550` adds each edge to both endpoints. `study_analysis.py:graph_measures` currently retains that endpoint convention even on the approved directed graph. Direction alone did not align this measure with the paper. |
| Betweenness | Fractional inverse-weight shortest paths — [§4.5.2](https://arxiv.org/html/2604.11721v2#S4.SS5.SSS2) | `social.py:553-575` calls unweighted `all_pairs_shortest_path`, choosing one path per pair. Passing the inverse-weight dictionary does not make that function use its weights. The study currently preserves that path-count convention, with direction added. This is a separate choice from graph direction and requires review. |
| Memory recall | Ten entries — [Appendix E.2.1, PDF p.24](https://arxiv.org/pdf/2604.11721v2#page=24) | Pinned `converse.py` requests five; harvesting and home reflection request ten. Deduplication can reduce returned counts further. `retrieve.py` ignores focal-point contents and scores earlier sorted entries more highly for recency. Current private instruments intentionally follow the five-entry utterance context. |
| Altruistic sampling | 57.15–90 degrees — [§3.1.1](https://arxiv.org/html/2604.11721v2#S3.SS1.SSS1) | `leaders.py:109-110` samples 57.15–75.0. This has no direct effect on the current prosocial-only values arm: its 22.45–57.15 range matches. Do not alter unrelated original leader sampling. |
| General task text | Stochastic growth — [Appendix E.2, PDF p.24](https://arxiv.org/pdf/2604.11721v2#page=24) | Pinned v3 text additionally says fish double once, before describing the uniform factor. The original contradiction is retained at N=8 and in scaled arms. This is already recorded in QUIRKS.md and is now verified against the appendix. |
| Depletion timing | Depletion at any point — [§3.2](https://arxiv.org/html/2604.11721v2#S3.SS2) | `concurrent_env.py:469-480` checks post-harvest stock only after discussion/reflection, before regeneration. A depleted lake therefore still generates that cycle's discussion and reflection. Treat this as a wording/implementation mismatch; it does not establish how unpublished experiment revisions behaved. |

Actual pinned metric functions were exercised without editing them or starting a model. For Julia→Kate weight 2 and Kate→Luke weight 1, pinned degree is Julia=2, Kate=3, Luke=1; incoming-only degree would be 0,2,1. On a triangle with inverse distances 0.1, 0.1 and 1, the pinned unweighted routine assigns no intermediary credit, while directed inverse-weight fractional betweenness assigns Kate one. These demonstrate that the differences can change leadership rankings.

### Previously known differences rechecked against the paper

| Item | Paper specification | Existing source finding / disposition |
|---|---|---|
| Output cap | At least 16K — [§4.1](https://arxiv.org/html/2604.11721v2#S4.SS1) | Original generation/find defaults are 8000 and fresh importance selections use 1000. The user now approved 16000 for study generation/find and private calls, consistently across conditions, retaining 1000 ratings. Both METHODS.md copies are amended. Runtime implementation and renewed smoke validation remain pending. |
| Truthfulness | General honesty/deception instructions — [Appendix E.1, PDF pp.23–24](https://arxiv.org/pdf/2604.11721v2#page=23) | Source uses agenda-crafting instructions instead; voters are hard-coded honest. Preserve replica source prompts and the approved removals elsewhere. |
| SVO privacy | Angle stays private — [Appendix B, PDF pp.20–21](https://arxiv.org/pdf/2604.11721v2#page=20) | No secrecy instruction exists in `SVO_LEADER_TASK`. The duplicated altruism sentence and missing space also remain. The values arm keeps the approved source-derived text with only the fisherman opening replacement. |
| Network direction | Directed edges — [Appendix C](https://arxiv.org/html/2604.11721v2#A3) | Original betweenness/eigenvector functions construct undirected graphs. Directed study graphs were previously approved; original analysis code remains unchanged. The paper's importance equation does not settle every adjacency-weight implementation choice. |
| Regeneration | Multiplicative capped stock — [§3.2](https://arxiv.org/html/2604.11721v2#S3.SS2) | Original stock is integer-truncated and cycle 1 fixes rho=2; later factors are unseeded uniform draws. Both code behaviors remain, as previously approved. |
| Public report | True harvest statistics — [§3.2](https://arxiv.org/html/2604.11721v2#S3.SS2) | Native report labels requested amounts as catches. Oversubscribed allocations can differ. Preserve the public report as approved; standardized logs record both values. |

### Replication ambiguities and additional source quirks

These are not all established paper contradictions; the publication does not specify enough to settle them.

- `social.py:180-181` labels any six recorded harvest cycles as survival, including a possible sixth-cycle collapse. The study uses explicit collapse flags. Both results should be disclosed when reconstructing A11 comparisons.
- `social.py:187-199,660-688` reconstructs welfare and inequality from requested-catch records, capping aggregate welfare by reconstructed stock. Our study uses actual allocations, including for household equality. The reconstruction can matter especially for inequality under oversubscription.
- `social.py:280-297` computes its reported standard-error helper as `sqrt(sum((x-mean)^2))/(n-1)`, rather than the usual sample standard deviation divided by `sqrt(n)`. The paper does not establish that this helper produced every published uncertainty. Keep publication error bars as reported; calculate this study's prespecified SE separately and label any legacy reproduction.
- The original insight/evidence regex fails and can store empty insights. Other conversation reflection calls still execute. Appendix memory examples cannot prove which code revision produced them. The user already chose to preserve this quirk.
- Original name matching/interaction parsing and graph aggregation include implementation conventions beyond the mathematical definitions. Our per-cycle graphs, silent-agent coverage, tenure handling and null comparisons are deliberate study choices, not direct replications of the original pooled leader analysis.
- The paper does not establish the exact integer behind 16K, a provider pin, a Gemini reasoning budget, or whether output caps differed for internal importance calls. Do not describe our 16000/1000 choice as exact recovery of all published request parameters.

### Confirmed agreements and deliberate study differences

The paper's Tables 8 and 9 match every value already copied into METHODS A11. Six cycles, eight agents, a 50-response discussion limit and temperature zero also agree. Our five seeds, one primary model, neutral baseline, private instruments, stakes succession, N16/N32 lake scaling and per-cycle leadership tests are intentional design changes, already documented in the methods. They should not be presented as accidental paper/code discrepancies.

Only the token-cap amendment was made to the binding methods in this review. No simulation, retrieval, reflection, threshold or centrality code was changed. Paid runs remain halted; the current runtime still uses the old caps until the approved override is implemented and validated. Review of threshold/centrality conventions is warranted before freezing primary outcomes.


## Approved paper-first implementation

The user resolved the source hierarchy in favor of paper definitions for all five audited choices, then explicitly approved aligning honesty/deception, SVO confidentiality and the contradictory general-system sentence. Author repository `main` was verified with `git ls-remote` as exactly `8cf0aba9efe0b4592f395d9a66e6cfff3cec9a26`; it does not resolve those paper/code discrepancies. No release tags were advertised. This section supersedes the earlier audit's pending dispositions.

- All study YAMLs now enable common guarded paper definitions and the 16000 generation override. Disabled overrides retain original request fidelity. The replica includes these disclosed common exceptions; it is not labeled unmodified pinned-code behavior.
- The environment logs the displayed paper threshold without an added floor. Allocation, integer regeneration and end-of-cycle transition mechanics remain original where paper implementation detail is unavailable.
- Analysis implements weighted incoming degree and directed inverse-distance betweenness with shared shortest-path credit. Rational distances avoid dropping mathematically tied paths. Original social.py is unchanged; historical checks retain their old profile conventions explicitly.
- Conversation and both private instruments request ten entries. Retrieval scoring, expiry, deduplication and Markdown handling remain unchanged. Recorder logs the requested limit so tests and data checks distinguish it from actual result count.
- Paper SVO ranges use keyed generators when enabled, including altruism through 90 degrees. Current conditions still have no altruistic agents or formal leaders. Prosocial focal draws retain their existing B6 key.
- All current arms share the published honesty sentence. Deception and confidentiality instructions are semantic paraphrases with exact study strings stored in `simulation/paper_definitions.py`; no character-identical paper-template claim is made for those two. Focal SVO text adds confidentiality, paper category ranges and consistent sentence separation while retaining the fisherman role and configured agenda. The obsolete agenda-crafting cue is absent in every paper-profile arm. Baseline still removes its mayor and anonymous-leader opener cues.
- General system text drops the extra fixed-doubling sentence while retaining the configured stochastic-growth statement. Original system and SVO constants remain available behind disabled overrides. B5 strings are unchanged.
- New StudyModelWrapper changes only generation/find caps. The original wrapper implementation, default caps, retry behavior and local parser regexes remain untouched. Raw metadata records effective limits.
- Resume selection now compares the resolved config, preventing validated old-profile smokes from being reused as amended-profile successes. Failed/old attempts and all spending are preserved.

Verification: 39 tests pass; six recorded six-cycle stub workers validate at zero API cost. Threshold boundary/scaling, altruistic bounds/key isolation, incoming direction, inverse weights and fractional tied-path credit are tested. Captured requests verify 16000 generation and 1000 fresh ratings in every arm. A separate disabled-override request fixture remains byte-identical to the pinned source after only the approved constructor repair. The six study fixtures now intentionally differ by the disclosed common paper overrides and arm manipulations.

Paper-first completeness check: the publication explicitly describes true catches. The common report source now uses allocated catches, while original native requested-catch logs are preserved. A new oversubscription test verifies both quantities and public lines. The first two amended smokes exposed no truncation but still used requested-catch reports under oversubscription; both are superseded and rerun. Replica nomination fallback was 14.3% in that superseded Flash-Lite attempt; the original parser is preserved and this is flagged for pilot review.
