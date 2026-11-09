"""A10 feasibility calculations on stored data; never imported by simulation."""

import math
import random
from collections import Counter

import networkx as nx
import numpy as np


def gini(values):
    values = list(values)
    total = sum(values)
    if not values or total == 0:
        return 0.0
    return sum(abs(a - b) for a in values for b in values) / (2 * len(values) * total)


def adoption(proposals, agreed):
    if not isinstance(agreed, (int, float)):
        return None
    matches = [name for name, value in proposals.items()
               if isinstance(value, (int, float)) and abs(value - agreed) <= 0.000001]
    return {name: 1 / len(matches) if name in matches else 0.0 for name in proposals}


def reference_events(turn, names):
    speaker = turn["speaker_identity"]
    mentions = [name for name in turn["mentioned_identities"] if name in names and name != speaker]
    nomination = turn.get("nominee_resolved")
    nominations = [nomination] if nomination in names else []
    return mentions, nominations


def graph_measures(names, turns, rng=None):
    """Directed version of AgentElect's edge and shortest-path conventions.

    Mentions and nominations add weight; weighted endpoint degree counts both
    ends. Betweenness counts intermediate nodes on the selected unweighted
    shortest paths, following social.py. Eigenvector centrality is unweighted,
    as in social.py, with incoming-edge direction and explicit non-uniqueness.
    """
    graph = nx.DiGraph()
    graph.add_nodes_from(names)
    for turn in turns:
        speaker = turn["speaker_identity"]
        mentions, nominations = reference_events(turn, names)
        for target in mentions + nominations:
            if rng is not None:
                target = rng.choice([name for name in names if name != speaker])
            graph.add_edge(speaker, target, weight=graph.get_edge_data(speaker, target, {}).get("weight", 0) + 1)
    degree = {name: float(graph.degree(name, weight="weight")) for name in names}
    between = dict.fromkeys(names, 0.0)
    for source, paths in nx.all_pairs_shortest_path(graph):
        for target, path in paths.items():
            if source != target:
                for middle in path[1:-1]:
                    between[middle] += 1
    adjacency = nx.to_numpy_array(graph, nodelist=names, weight=None).T
    eigen = None
    reason = None
    values, vectors = np.linalg.eig(adjacency)
    radius = float(max(abs(values), default=0))
    candidates = [i for i, value in enumerate(values) if abs(value.imag) < 1e-8 and abs(value.real - radius) < 1e-8]
    nullity = len(names) - np.linalg.matrix_rank(adjacency - radius * np.eye(len(names)), tol=1e-8)
    if nullity != 1 or not candidates:
        reason = "Dominant eigenvector is not unique"
    else:
        vector = vectors[:, candidates[0]].real
        if vector.sum() < 0:
            vector *= -1
        if np.any(vector < -1e-8) or np.linalg.norm(vector) == 0:
            reason = "No numerically valid nonnegative eigenvector"
        else:
            vector = np.maximum(vector, 0)
            vector /= np.linalg.norm(vector)
            eigen = dict(zip(names, map(float, vector)))
    result = {"degree": degree, "betweenness": between, "eigenvector": eigen,
              "eigenvector_status": "undefined" if reason else "ok", "eigenvector_reason": reason}
    result["gini"] = {key: gini(result[key].values()) if result[key] is not None else None
                      for key in ("degree", "betweenness", "eigenvector")}
    return result


def null_comparisons(names, turns, condition, seed, cycle, samples=1000):
    """User-defined nomination-chain airtime and airtime-conditioned targets."""
    airtime = []
    influence = {key: [] for key in ("degree", "betweenness", "eigenvector")}
    for replicate in range(samples):
        rng = random.Random(f"analysis_airtime|{condition}|{seed}|{cycle}|{replicate}")
        counts = dict.fromkeys(names, 0)
        if turns:
            speaker = turns[0]["speaker_identity"]
            for position in range(len(turns)):
                counts[speaker] += 1
                if position < len(turns) - 1:
                    options = turns[position]["nominee_options"]
                    if not options:
                        raise ValueError("An intermediate turn has no recorded nominee options")
                    speaker = rng.choice(options)
        airtime.append(gini(counts.values()))
        targets = random.Random(f"analysis_targets|{condition}|{seed}|{cycle}|{replicate}")
        random_graph = graph_measures(names, turns, rng=targets)
        for key in influence:
            if random_graph["gini"][key] is not None:
                influence[key].append(random_graph["gini"][key])

    def summarize(values):
        return {"mean": float(np.mean(values)) if values else None,
                "mc_standard_error": float(np.std(values, ddof=1) / math.sqrt(len(values))) if len(values) > 1 else None,
                "defined_samples": len(values), "undefined_samples": samples - len(values)}

    return {"samples": samples, "airtime": summarize(airtime),
            "influence": {key: summarize(value) for key, value in influence.items()},
            "airtime_key": f"analysis_airtime|{condition}|{seed}|{cycle}|{{replicate}}",
            "influence_key": f"analysis_targets|{condition}|{seed}|{cycle}|{{replicate}}"}


def cycle_measures(metadata, cycle, turns, samples=1000):
    names = [row["identity"] for row in cycle["catches"]]
    counts = Counter(turn["speaker_identity"] for turn in turns)
    airtime = {name: counts[name] for name in names}
    elicitations = cycle.get("elicitation") or {}
    limits = {name: result.get("preferred_limit") for name, result in elicitations.items()}
    votes = Counter(result["resolved_identity"] for result in (cycle.get("perceived_leadership") or {}).values())
    preferred = [value for value in limits.values() if isinstance(value, (int, float))]
    plans = [result["plan"] for result in elicitations.values() if isinstance(result.get("plan"), (int, float))]
    graph = graph_measures(names, turns)
    focal = metadata["seed"] % 8 if metadata["condition"] in ("values_N8", "stakes_N8") else None
    opener_slot = turns[0]["slot"] if turns else None
    opener = turns[0]["speaker_identity"] if turns else None
    agreed = cycle["agreed_limit"]
    opener_limit = limits.get(opener)
    return {
        "cycle": cycle["cycle"], "airtime": airtime, "silent_share": sum(value == 0 for value in airtime.values()) / len(names),
        "airtime_gini": gini(airtime.values()), "centrality": graph,
        "elicited_proposal_adoption": adoption(limits, cycle["agreed_limit"]) if elicitations else None,
        "peer_nominations": dict(votes), "planned_catch_dispersion": float(np.std(plans)) if plans else None,
        "preferred_limit_dispersion": float(np.std(preferred)) if preferred else None,
        "mean_distance_to_agreement": float(np.mean([abs(value - cycle["agreed_limit"]) for value in preferred]))
        if preferred and isinstance(cycle["agreed_limit"], (int, float)) else None,
        "focal_opened": opener_slot == focal if focal is not None else None,
        "speaking_order": {
            "opener": opener,
            "opener_preferred_limit_distance": abs(opener_limit - agreed)
            if isinstance(opener_limit, (int, float)) and isinstance(agreed, (int, float)) else None,
            "random_agent_mean_distance": float(np.mean([abs(value - agreed) for value in preferred]))
            if preferred and isinstance(agreed, (int, float)) else None,
            "discussion_first_proposer": "stored text reserved for post-experiment extraction",
        },
        "null": null_comparisons(names, turns, metadata["condition"], metadata["seed"], cycle["cycle"], samples),
    }
