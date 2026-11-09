# Original implementation quirks

Source baseline: `8cf0aba9efe0b4592f395d9a66e6cfff3cec9a26`.
These observations do not authorize changes to original simulation behavior.

## B9 / B10: Regenerated stock is truncated to whole tons

- Location: `simulation/environment/concurrent_env.py:476-480`.
- The original environment computes `int(min(capacity, post_harvest_stock * regen_factor))`.
- For example, 50 tons with a factor of 1.57 becomes 78 tons, rather than 78.5.
- B9 states an equality without the `int(...)`, whereas B2 and B10 require preserving the original regeneration and original quirks.
- Resolution: the user approved preserving the original integer behavior and making the B9 mechanics test expect `int(min(capacity, post_harvest_stock * regen_factor))`. Original code remains unchanged.

## B1 / B10: Agent initialization has incompatible constructor arguments

- Locations: `simulation/run.py:141-147`; `simulation/persona/persona.py:53-59,82-87`; `simulation/persona/cognition/retrieve.py:28-33`; `simulation/persona/cognition/store.py:15-21`. The leader construction at `simulation/run.py:122-131` has the same first mismatch.
- The runner passes four positional arguments to `PersonaAgent`, but its constructor requires five: the storage path binds to `embedding_model`, leaving `base_path` missing.
- `PersonaAgent` also passes four positional arguments to `RetrieveComponent`, which accepts three, and five to `StoreComponent`, which accepts four.
- These inconsistencies were checked using AST-derived signatures and `inspect.Signature.bind`, without importing simulation dependencies or making model calls. The first mismatch prevents normal agent creation; the remaining two would prevent initialization after resolving the first.
- Resolution: the user explicitly authorized removing the obsolete `embedding_model` constructor parameter and its two forwarded arguments in `persona.py`. Retrieval and storage implementations remain unchanged. References above describe the pinned original source.

## B3: The no-leader agenda is a nonempty sentinel

- Locations: `simulation/persona/persona.py:43`; `simulation/phases/base.py:45,77`; `simulation/persona/cognition/act_prompts.py:51-54` (pinned-source references).
- The no-leader path uses `DEFAULT_AGENDA = "No specific guidance."`, not an empty string or None. Omitting the mayor line only for empty/None agendas, as B3 specifies, would leave the mayor cue in the baseline.
- Resolution: the user approved "no mayor" for baseline conditions. The guarded omission treats the original no-guidance sentinel as absent, as well as an empty string or None. Flag-off prompts retain the original line.

## B4.4: The harvest report is inside the conversation section

- Locations: `simulation/environment/concurrent_env.py:165-174`; `simulation/persona/cognition/converse.py:75-89`; `simulation/persona/cognition/converse_prompts.py:49-64` (pinned-source references).
- Restaurant `current_context` is empty. The report enters utterance prompts as the framework's first conversation message, after "Conversation so far". Cutting the prompt before that section loses the report, contrary to B4.4's assumption that it is already in current context.
- Interpretation following the user's request to retain AgentElect's public report: keep the framework's public report unchanged (apart from B3's specified neutral announcement) and include that same public information in private elicitation context. The original shared prefix remains unchanged; the added report context must be explicitly allowlisted in its fidelity test. This repeats public information and does not create a private report or add it to memory.

## B3 / B8: The original report labels requested catches as actual catches

- Locations: `simulation/phases/harvesting.py:112-114,173-175`; `simulation/persona/cognition/leaders.py:280-292` (pinned-source references).
- `round_harvest_stats` stores requested catches (`action.quantity`), and `make_harvest_report` renders them as fish caught. Under oversubscription these can differ from actual allocations in the environment.
- B3 explicitly requires unchanged `make_harvest_report` output. Preserve this original behavior; B8 must log requested and actual catches separately.

## A10 / B11: Original social analysis constructs undirected graphs

- Locations: `simulation/analysis/social.py:569,593-594` (pinned-source references).
- The original code uses `nx.from_dict_of_dicts(...)` without a directed graph constructor for betweenness and eigenvector centrality. Degree counts both endpoints; eigenvector centrality does not request weighted edges. A10 describes a directed graph while also referring to this code.
- Resolution: the user approved directed graphs for the study's A10 metric calculations. Original analysis code remains unchanged.

## B1 / B10: Unpinned Transformers resolution cannot import with pinned PyTorch

- Locations: `requirements.txt:15`; `pathfinder/requirements.txt:3`; `requirements_venv.txt:2,13`; `simulation/persona/embedding_model.py:4` (pinned-source references).
- The user-selected default requirements leave `transformers` and `sentence_transformers` unpinned. Installation resolved Transformers 5.22.2 and sentence-transformers 6.2.0 while retaining the repository's PyTorch 2.2.0 pin.
- Installation and `pip check` passed. Importing `simulation.run` failed: Transformers disabled PyTorch because it requires >=2.6, then raised `NameError: name 'nn' is not defined` in `transformers/distributed/pipeline_parallel.py`, reached through the existing sentence-transformers import.
- No model was instantiated and no paid call was made. Do not upgrade PyTorch or alter source imports to conceal this failure. The repository's alternate requirements file pins Transformers 4.51.0.
- Resolution: the user approved Transformers 4.51.0 and compatible unpinned dependencies while retaining all fixed pins. The resolver selected sentence-transformers 5.7.0, huggingface-hub 0.36.2 and tokenizers 0.21.4. The simulation imports successfully, `pip check` passes, and all nine selected fixed pins are unchanged. `constraints-macos.txt` records the resolved environment.

## B2 / B14: Fresh importance-rating calls use a 1,000-token cap

- Locations: `pathfinder/pathfinder/api.py:29-35,76-83`; `simulation/persona/cognition/store_prompts.py:32-40` and its other fresh `select`-based rating calls.
- `ModelAPI` initializes `max_tokens` to 1000. Generation sets it to 8000, but `select` does not change it. Importance ratings start fresh chains with `select` and therefore request 1000 tokens.
- A one-cycle N=8 transport stub captured 45 requests with an 8000-token cap and 32 with a 1000-token cap; all 32 shorter-cap requests were importance ratings. The original adapter and wrapper were used unchanged.
- B2/B14 assume 8000 for all calls, while B9/B10 require original request fidelity and unchanged sampling parameters. No cap has been changed. The six-cycle stub completed but its strict all-8000 assertion fails.
- Resolution: the user explicitly approved preserving original token caps and updating the test expectations. Generation requests remain at 8000 and fresh importance-rating requests at 1000; no request parameters are changed.

## B9 / B10: Original insight-reflection regex triggers the default fallback

- Location: `simulation/persona/cognition/reflect_prompts.py:37-44` (pinned-source reference).
- The insight-generation stop pattern contains an unmatched opening parenthesis after an escaped backslash. Pathfinder wraps and compiles that pattern; the original model wrapper catches the regex error and substitutes its empty default for the insight.
- The actual one-cycle stub produced eight regex warnings (one per N=8 agent), while the simulation still completed. The warnings begin `An exception occured: missing ) at position 14`.
- Resolution: the user explicitly instructed leaving this reflection-regex behavior unchanged. No repair or warning suppression has been added to simulation code. The six-cycle N=8 stub test explicitly expects the 48 original regex warnings.

## B10: Recency favors earlier markdown entries

- Location: `simulation/persona/cognition/retrieve.py:44-56`; original memory markdown ordering is oldest first.
- Recency scores are `0.99 ** index` in that order, so earlier entries have higher recency scores. Retrieval remains unchanged; recording observes these exact scores.

## B10: The v3 system text says both double and a sampled factor

- Location: `simulation/persona/cognition/utils.py`, `get_sytem_prompt_v3`.
- The original preamble says remaining fish double once, followed by the configured uniform-regeneration description. Preserve both statements verbatim at N=8; only specified lake numbers scale at larger N.
