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
