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
