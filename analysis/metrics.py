"""Shared analysis metrics implementing ANALYSIS_PLAN.md B2.

Read-only with respect to GovSimEmergentLeader: this module never writes there.
It implements the B2 definitions independently of study_analysis.py, because
study_analysis.py differs from B2 on several points (see DISCREPANCIES.md).
Never uses the global `random` or `np.random`; all draws come from keyed
generators (B3) and are logged through KeyLog.
"""

from __future__ import annotations

import gzip
import hashlib
import itertools
import json
import math
import re
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

import networkx as nx
import numpy as np

def repo_root():
    """GovSimEmergentLeader checkout: $GOVSIM_REPO, else the repo containing this analysis/ folder,
    else the sibling checkout used during development (ClaudeAnalysis/ next to GovSimEmergentLeader/)."""
    import os
    here = Path(__file__).resolve().parent
    if os.environ.get("GOVSIM_REPO"):
        return Path(os.environ["GOVSIM_REPO"])
    if (here.parent / "simulation").is_dir():
        return here.parent
    return here.parents[1] / "GovSimEmergentLeader"


# B6 name pool (METHODS_UPDATED.md), in order.
NAME_POOL = [n.strip() for n in (
    "Julia, Kate, Jack, Emma, Luke, Noah, Olivia, Liam, Isaac, Chloe, Owen, Leah, Henry, Zoe, Caleb, Nora, "
    "Felix, Clara, Adam, Maya, Leo, Elena, Simon, Naomi, Oscar, Diego, Priya, Tariq, Ingrid, Mateo, Yusuf, "
    "Hana, Viktor, Amara, Ronan, Sofia, Kenji, Lucia, Dmitri, Ines").split(",")]
_CANON = {n.casefold(): n for n in NAME_POOL}
# Same pattern as simulation/recording.py (word-bounded, case-insensitive); tags such as
# "Julia [months remaining: 3]" leave the bare name word-bounded, so they resolve.
_NAME_RE = re.compile(r"\b(?:" + "|".join(NAME_POOL) + r")\b", re.I)
_TAG_RE = re.compile(r"\s*\[months remaining:\s*\d+\]")

ROUTING = {
    "primary": {"agent"},
    "sens_judge": {"agent", "judge"},
    "sens_random": {"agent", "judge", "random"},
}


# ---------------------------------------------------------------- keyed RNG (B3)
class KeyLog:
    """Records every analysis RNG key and its draw count (analysis/keys_used.json)."""

    def __init__(self):
        self.entries = {}

    def rng(self, key: str, draws: int):
        self.entries[key] = self.entries.get(key, 0) + draws
        return keyed_rng(key)

    def dump(self, path):
        """Merge into an existing log: entries for keys used in this process replace old ones."""
        merged = {}
        if Path(path).exists():
            merged = {e["key"]: e["draws"] for e in json.loads(Path(path).read_text())}
        merged.update(self.entries)
        Path(path).write_text(json.dumps(
            [{"key": k, "draws": v} for k, v in sorted(merged.items())], indent=1) + "\n")


def keyed_rng(key: str) -> np.random.Generator:
    return np.random.default_rng(int.from_bytes(hashlib.sha256(key.encode()).digest(), "big"))


# ---------------------------------------------------------------- names and edges (B2.1)
def resolve_name(raw, names=None):
    """Tag-aware single-name resolver: strip tags, exact case-insensitive pool match."""
    if raw is None:
        return None
    text = _TAG_RE.sub("", str(raw)).strip().strip(".").strip()
    hit = _CANON.get(text.casefold())
    if hit and (names is None or hit in names):
        return hit
    return None


def mentioned_set(text, names=None):
    found = {_CANON[m.casefold()] for m in _NAME_RE.findall(text or "")}
    return found if names is None else found & set(names)


def turn_edges(turn, names, routing="primary"):
    """Return (edges, self_mentions, self_nominations) for one utterance.

    edges: list of (speaker, target, 1.0). Mentions counted once per utterance from the
    public response text; nomination edge added separately if its routing source is allowed.
    """
    speaker = turn["speaker_identity"]
    names = set(names)
    mentions = mentioned_set(turn.get("text", ""), names)
    self_mention = int(speaker in mentions)
    edges = [(speaker, t, 1.0) for t in sorted(mentions - {speaker})]
    self_nom = 0
    nominee = turn.get("nominee_resolved")
    source = turn.get("nomination_source")
    if nominee is not None and nominee in names and source in ROUTING[routing]:
        if nominee == speaker:
            self_nom = 1
        else:
            edges.append((speaker, nominee, 1.0))
    return edges, self_mention, self_nom


def build_graph(names, turns, routing="primary"):
    g = nx.DiGraph()
    g.add_nodes_from(names)
    self_m = self_n = 0
    for turn in turns:
        edges, sm, sn = turn_edges(turn, names, routing)
        self_m += sm
        self_n += sn
        for u, v, w in edges:
            g.add_edge(u, v, weight=g.get_edge_data(u, v, {}).get("weight", 0) + w)
    g.graph["self_mentions"] = self_m
    g.graph["self_nominations"] = self_n
    return g


def graph_from_edges(names, edges):
    g = nx.DiGraph()
    g.add_nodes_from(names)
    for u, v, w in edges:
        g.add_edge(u, v, weight=g.get_edge_data(u, v, {}).get("weight", 0) + w)
    return g


# ---------------------------------------------------------------- centralities (B2.3-6)
def in_degree(g):
    return {v: float(sum(d["weight"] for _, _, d in g.in_edges(v, data=True))) for v in g.nodes}


def betweenness(g):
    """Directed Brandes with exact Fraction(1, w) distances; unnormalized; endpoints excluded."""
    nodes = list(g.nodes)
    bc = {v: Fraction(0) for v in nodes}
    for s in nodes:
        dist = {s: Fraction(0)}
        sigma = defaultdict(int)
        sigma[s] = 1
        preds = defaultdict(list)
        order = []
        frontier = {s: Fraction(0)}
        settled = set()
        while frontier:
            v = min(frontier, key=lambda x: (frontier[x], nodes.index(x)))
            dv = frontier.pop(v)
            settled.add(v)
            order.append(v)
            for _, w, data in g.out_edges(v, data=True):
                if w in settled:
                    continue
                nd = dv + Fraction(1) / Fraction(data["weight"])
                if w not in dist or nd < dist[w]:
                    dist[w] = nd
                    frontier[w] = nd
                    sigma[w] = sigma[v]
                    preds[w] = [v]
                elif nd == dist[w]:
                    sigma[w] += sigma[v]
                    preds[w].append(v)
        delta = defaultdict(Fraction)
        for w in reversed(order):
            for v in preds[w]:
                delta[v] += Fraction(sigma[v], sigma[w]) * (1 + delta[w])
            if w != s:
                bc[w] += delta[w]
    return {v: float(x) for v, x in bc.items()}


def eigenvector(g):
    """Incoming, unweighted. Returns (dict or None, reason or None)."""
    nodes = list(g.nodes)
    if len(nodes) == 0 or not nx.is_strongly_connected(g):
        return None, "not_strongly_connected"
    idx = {v: i for i, v in enumerate(nodes)}
    a = np.zeros((len(nodes), len(nodes)))
    for u, v in g.edges:
        if u != v:
            a[idx[v], idx[u]] = 1.0
    vals, vecs = np.linalg.eig(a)
    k = int(np.argmax(vals.real))
    vec = np.abs(vecs[:, k].real)
    vec = vec / np.linalg.norm(vec)
    return dict(zip(nodes, map(float, vec))), None


def eigenvalue(g):
    nodes = list(g.nodes)
    idx = {v: i for i, v in enumerate(nodes)}
    a = np.zeros((len(nodes), len(nodes)))
    for u, v in g.edges:
        a[idx[v], idx[u]] = 1.0
    return float(np.max(np.linalg.eigvals(a).real))


def pagerank(g):
    return nx.pagerank(g, alpha=0.85, weight="weight")


# ---------------------------------------------------------------- distributions (B2.7-8)
def gini(values):
    """AgentElect eq. 4. None (undefined) if empty or all zero."""
    x = [float(v) for v in values]
    total = sum(x)
    if not x or total == 0:
        return None
    return sum(abs(a - b) for a in x for b in x) / (2 * len(x) * total)


def gini_rows(mat):
    """Vectorized eq. 4 over rows of a non-negative matrix; NaN where a row sums to zero."""
    mat = np.asarray(mat, dtype=float)
    n = mat.shape[1]
    s = np.sort(mat, axis=1)
    total = s.sum(axis=1)
    i = np.arange(1, n + 1)
    # sum_{i,j}|x_i-x_j| = 2 * sum_i (2i - n - 1) x_(i)
    num = 2 * (s * (2 * i - n - 1)).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(total > 0, num / (2 * n * total), np.nan)


def percentile_ranks(values: dict):
    keys = list(values)
    n = len(keys)
    out = {}
    for k in keys:
        below = sum(values[o] < values[k] for o in keys if o != k)
        tied = sum(values[o] == values[k] for o in keys if o != k)
        out[k] = (below + 0.5 * tied) / (n - 1)
    return out


# ---------------------------------------------------------------- adoption (B2.9)
def adoption(proposals: dict, agreed):
    if not isinstance(agreed, (int, float)) or isinstance(agreed, bool):
        return None
    matches = [k for k, v in proposals.items()
               if isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v - agreed) <= 0.000001]
    return {k: (1 / len(matches) if k in matches else 0.0) for k in proposals}


def originator(first_proposals: dict, agreed):
    """first_proposals: name -> (position, value). Credit 1 to earliest matching proposer."""
    if not isinstance(agreed, (int, float)):
        return None
    out = dict.fromkeys(first_proposals, 0.0)
    hits = [(pos, k) for k, (pos, v) in first_proposals.items()
            if v is not None and abs(v - agreed) <= 0.000001]
    if hits:
        out[min(hits)[1]] = 1.0
    return out


# ---------------------------------------------------------------- inference (B5.4)
def standardized(observed, null_values):
    null_values = np.asarray([v for v in null_values if v is not None and not np.isnan(v)], float)
    if observed is None or len(null_values) < 2:
        return None
    sd = float(np.std(null_values, ddof=1))
    if sd == 0:
        return None
    return (observed - float(np.mean(null_values))) / sd


def holm(pvalues):
    p = np.asarray(pvalues, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return adj.tolist()


def exact_stratified_p(run_ranks, observed):
    """run_ranks: list (one per run) of all agents' percentile ranks. Enumerates every
    assignment of the focal label; returns (p one-sided >=, n assignments)."""
    hits = total = 0
    k = len(run_ranks)
    for combo in itertools.product(*run_ranks):
        total += 1
        if sum(combo) / k >= observed - 1e-12:
            hits += 1
    return hits / total, total


# ---------------------------------------------------------------- judge indices (B2.12-13)
COOPERATIVE_CATEGORIES = None  # set from llm_judge at Stage 3; tests inject their own


def cooperative_index(utterance_labels, cooperative_categories):
    coop = [sum(l in cooperative_categories for l in labels) > sum(l not in cooperative_categories for l in labels)
            for labels in utterance_labels]
    ties = sum(sum(l in cooperative_categories for l in labels) == sum(l not in cooperative_categories for l in labels)
               for labels in utterance_labels)
    return sum(coop) / len(coop), ties


def legacy_cooperative_index(utterance_labels, cooperative_categories):
    labels = [l for ls in utterance_labels for l in ls]
    return sum(l in cooperative_categories for l in labels) / len(labels)


def persuasion_shares(labels):
    c = Counter(labels)
    tot = c["Logos"] + c["Pathos"] + c["Ethos"]
    if tot == 0:
        return None
    return {k: c[k] / tot for k in ("Logos", "Pathos", "Ethos")}


def legacy_persuasion_shares(labels):
    c = Counter(labels)
    return {k: c[k] / len(labels) for k in ("Logos", "Pathos", "Ethos", "Neutral")}


_DEF_RE = {
    "defers_to": re.compile(r"^\s*DEFERS_TO:\s*(.+?)\s*$", re.I | re.M),
    "basis": re.compile(r"^\s*BASIS:\s*(proposal|judgment|consensus|tenure|other|none)\s*$", re.I | re.M),
    "mentions_tenure": re.compile(r"^\s*MENTIONS_TENURE:\s*(yes|no)\s*$", re.I | re.M),
}


def parse_deference(text, participants):
    got = {k: r.search(text or "") for k, r in _DEF_RE.items()}
    if not all(got.values()):
        return "unparsed"
    raw = got["defers_to"].group(1)
    if raw.strip().lower() == "none":
        who = "none"
    else:
        who = resolve_name(raw, participants)
        if who is None:
            return "unparsed"
    return {"defers_to": who, "basis": got["basis"].group(1).lower(),
            "mentions_tenure": got["mentions_tenure"].group(1).lower() == "yes"}


# ---------------------------------------------------------------- data loading (read-only)
def _jsonl(path):
    with gzip.open(path, "rt") as f:
        return [json.loads(line) for line in f]


def load_run(path):
    path = Path(path)
    meta = json.loads((path / "run_meta.json").read_text())
    return {
        "meta": meta,
        "cycles": _jsonl(path / "cycles.jsonl.gz"),
        "turns": _jsonl(path / "utterances.jsonl.gz"),
        "agents": _jsonl(path / "agents.jsonl.gz"),
        "errors": _jsonl(path / "errors.jsonl.gz"),
        "judgments": _jsonl(path / "nomination_judgments.jsonl.gz"),
        "path": str(path),
    }


def load_calls(path):
    return _jsonl(Path(path) / "calls.jsonl.gz")


# ---------------------------------------------------------------- mechanism-matched nulls (A10, B2.11)
def phase_turns(turns, phase):
    if phase == "whole":
        return list(turns)
    return [t for t in turns if t.get("discussion_stage") == phase]


def airtime_null(names, cycle_turns, phase, rng, draws):
    """Gini of airtime under the random nomination chain. Returns array (draws,).

    Opening schedule is kept; the last opening handoff and every later nomination are
    redrawn uniformly from the options recorded at that turn (including self)."""
    idx = {n: i for i, n in enumerate(names)}
    opening = [t for t in cycle_turns if t.get("discussion_stage") == "opening"]
    nomination = [t for t in cycle_turns if t.get("discussion_stage") == "nomination"]
    counts = np.zeros((draws, len(names)))
    if phase in ("whole", "opening"):
        for t in opening:
            counts[:, idx[t["speaker_identity"]]] += 1
    if phase in ("whole", "nomination") and nomination:
        # options for nomination-phase position k come from the turn before it
        prev = [opening[-1]] + nomination[:-1]
        for t in prev:
            opts = [o for o in t["nominee_options"] if o in idx]
            if not opts:
                raise ValueError("turn without recorded nominee options")
            pick = rng.integers(len(opts), size=draws)
            cols = np.array([idx[o] for o in opts])[pick]
            np.add.at(counts, (np.arange(draws), cols), 1)
    return gini_rows(counts)


def influence_null(names, phase_turn_list, rng, draws, routing="primary"):
    """Gini of incoming degree when each observed reference/nomination target is redrawn
    uniformly among the other present agents (speakers and event counts retained)."""
    idx = {n: i for i, n in enumerate(names)}
    n = len(names)
    deg = np.zeros((draws, n))
    for t in phase_turn_list:
        edges, _, _ = turn_edges(t, names, routing)
        s = idx[t["speaker_identity"]]
        for _ in edges:
            r = rng.integers(n - 1, size=draws)
            r = r + (r >= s)  # skip the speaker
            np.add.at(deg, (np.arange(draws), r), 1)
    return gini_rows(deg)


# ---------------------------------------------------------------- Jonckheere-Terpstra (A4 H3)
def jt_statistic(groups):
    """Sum over ordered group pairs i<j of #(x_i < x_j) + 0.5 * #ties."""
    s = 0.0
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            a = np.asarray(groups[i], float)[:, None]
            b = np.asarray(groups[j], float)[None, :]
            s += float((a < b).sum() + 0.5 * (a == b).sum())
    return s


def jt_exact(groups):
    """Exact one-sided (increasing) JT p-value for three groups by enumerating all
    assignments of the pooled values to groups of the observed sizes."""
    assert len(groups) == 3
    pooled = np.concatenate([np.asarray(g, float) for g in groups])
    n1, n2, n3 = map(len, groups)
    n = len(pooled)
    less = (pooled[:, None] < pooled[None, :]) + 0.5 * (pooled[:, None] == pooled[None, :])
    obs = jt_statistic(groups)
    hits = total = 0
    idx = np.arange(n)
    for g1 in itertools.combinations(range(n), n1):
        rest = np.setdiff1d(idx, g1)
        g1 = np.array(g1)
        c2 = np.array(list(itertools.combinations(rest, n2)))           # (k, n2)
        mask = np.ones((len(c2), n), bool)
        mask[np.arange(len(c2))[:, None], c2] = False
        mask[:, g1] = False                                             # remaining = group 3
        g3 = np.array([idx[m] for m in mask])                           # (k, n3)
        s12 = less[np.ix_(g1, rest)]                                    # rows g1
        a = less[g1][:, c2].sum(axis=(0, 2))                            # g1 < g2
        b = less[g1][:, g3].sum(axis=(0, 2))                            # g1 < g3
        c = less[c2[:, :, None], g3[:, None, :]].sum(axis=(1, 2))       # g2 < g3
        stat = a + b + c
        hits += int((stat >= obs - 1e-9).sum())
        total += len(stat)
    return obs, hits / total, total
