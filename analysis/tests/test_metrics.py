"""ANALYSIS_PLAN.md B5 tests. No network, no paid calls.

Run from the folder that contains analysis/ (repo root): PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider analysis/tests
"""

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import metrics as M  # noqa: E402

TOL = 1e-6


def g(names, edges):
    return M.graph_from_edges(names, [(u, v, w) for u, v, w in edges])


# ---------------------------------------------------------------- B5.1
def test_b51a_degree_betweenness():
    gr = g("ABCD", [("A", "B", 2), ("B", "C", 1), ("A", "C", 1), ("C", "D", 1), ("D", "A", 1)])
    assert M.in_degree(gr) == {"A": 1, "B": 2, "C": 2, "D": 1}
    assert M.betweenness(gr) == pytest.approx({"A": 3, "B": 0, "C": 3, "D": 3}, abs=TOL)


def test_b51b_fractional_ties():
    gr = g("ABCD", [("A", "B", 1), ("A", "C", 1), ("B", "D", 1), ("C", "D", 1)])
    assert M.betweenness(gr) == pytest.approx({"A": 0, "B": 0.5, "C": 0.5, "D": 0}, abs=TOL)


def test_b51c_exact_rational_ties():
    gr = g("ABCD", [("A", "B", 2), ("B", "D", 12), ("A", "C", 3), ("C", "D", 4)])
    b = M.betweenness(gr)
    assert b["B"] == pytest.approx(0.5, abs=TOL) and b["C"] == pytest.approx(0.5, abs=TOL)


def test_b51d_eigenvector():
    gr = g("ABC", [("A", "B", 1), ("B", "A", 1), ("B", "C", 1), ("C", "A", 1)])
    vec, reason = M.eigenvector(gr)
    assert reason is None
    assert M.eigenvalue(gr) == pytest.approx(1.324718, abs=TOL)
    assert vec == pytest.approx({"A": 0.726517, "B": 0.548432, "C": 0.413999}, abs=TOL)


def test_b51e_undefined_eigenvector():
    vec, reason = M.eigenvector(g("ABC", [("A", "B", 1), ("B", "C", 1)]))
    assert vec is None and reason == "not_strongly_connected"


NAMES8 = M.NAME_POOL[:8]
BASE = "I agree with Kate. Kate and Jack made good points, and I, Julia, will stick to 6."


def _turn(text, nominee="Emma", source="agent"):
    return {"speaker_identity": "Julia", "text": text, "nominee_resolved": nominee, "nomination_source": source}


def _w(gr):
    return {(u, v): d["weight"] for u, v, d in gr.edges(data=True)}


def test_b51f_edge_construction():
    gr = M.build_graph(NAMES8, [_turn(BASE)])
    assert _w(gr) == {("Julia", "Kate"): 1, ("Julia", "Jack"): 1, ("Julia", "Emma"): 1}
    gr = M.build_graph(NAMES8, [_turn(BASE + " Emma, what do you think?")])
    assert _w(gr)[("Julia", "Emma")] == 2
    gr = M.build_graph(NAMES8, [_turn(BASE, nominee="Julia")])
    assert ("Julia", "Julia") not in _w(gr) and gr.graph["self_nominations"] == 1
    judged = _turn(BASE, source="judge")
    assert ("Julia", "Emma") not in _w(M.build_graph(NAMES8, [judged], "primary"))
    assert _w(M.build_graph(NAMES8, [judged], "sens_judge"))[("Julia", "Emma")] == 1


def test_b51g_stakes_tags():
    t = {"speaker_identity": "Kate", "text": "Julia [months remaining: 3] said we should fish 5",
         "nominee_resolved": None, "nomination_source": "end"}
    assert _w(M.build_graph(NAMES8, [t])) == {("Kate", "Julia"): 1}
    assert M.resolve_name("Julia [months remaining: 3]") == "Julia"


def test_b51h_silent_agents():
    gr = g("ABCD", [("A", "B", 1), ("B", "C", 1), ("C", "A", 1)])
    deg = M.in_degree(gr)
    assert deg["D"] == 0
    assert M.gini(deg.values()) == pytest.approx(0.25, abs=TOL)  # [1,1,1,0]
    assert M.eigenvector(gr) == (None, "not_strongly_connected")


# ---------------------------------------------------------------- B5.2
def test_b52_gini():
    assert M.gini([0, 0, 0, 10]) == pytest.approx(0.75)
    assert M.gini([1, 2, 3, 4]) == pytest.approx(0.25)
    assert M.gini([1, 1, 1, 1]) == 0
    assert M.gini([0, 0, 0, 0]) is None
    rows = M.gini_rows([[0, 0, 0, 10], [1, 2, 3, 4], [1, 1, 1, 1], [0, 0, 0, 0]])
    assert rows[:3] == pytest.approx([0.75, 0.25, 0.0]) and np.isnan(rows[3])


def test_b52_percentile_rank():
    assert M.percentile_ranks({"a": 3, "b": 2, "c": 1}) == {"a": 1.0, "b": 0.5, "c": 0.0}
    r = M.percentile_ranks({"a": 2, "b": 2, "c": 1})
    assert r["a"] == 0.75 and r["b"] == 0.75


# ---------------------------------------------------------------- B5.3
def test_b53_adoption():
    p = {"A": 6, "B": 6, "C": 5}
    assert M.adoption(p, 6) == {"A": 0.5, "B": 0.5, "C": 0}
    assert M.adoption(p, 7) == {"A": 0, "B": 0, "C": 0}
    assert M.adoption(p, None) is None
    assert M.adoption({"A": 6.0000005}, 6) == {"A": 1.0}
    assert M.adoption({"A": 6.000002}, 6) == {"A": 0.0}
    assert M.originator({"B": (2, 6), "A": (4, 6)}, 6) == {"B": 1.0, "A": 0.0}


# ---------------------------------------------------------------- B5.4
def test_b54_exact_enumeration_toy():
    # 2 runs x 3 agents, no ties: each run's ranks are {0, 0.5, 1}; focal ranks 1.0 and 0.5
    p, n = M.exact_stratified_p([[0.0, 0.5, 1.0], [0.0, 0.5, 1.0]], (1.0 + 0.5) / 2)
    assert n == 9 and p == pytest.approx(1 / 3)


def test_b54_holm():
    assert M.holm([0.01, 0.04, 0.03, 0.20, 0.005]) == pytest.approx([0.04, 0.09, 0.09, 0.20, 0.025])


def _toy_cycle(names, k_nom):
    opts = list(names)
    opening = [{"speaker_identity": n, "discussion_stage": "opening", "nominee_options": opts,
                "text": "", "nominee_resolved": None, "nomination_source": "fixed_opening"} for n in names]
    nom = [{"speaker_identity": names[i % len(names)], "discussion_stage": "nomination", "nominee_options": opts,
            "text": names[(i + 1) % len(names)], "nominee_resolved": None, "nomination_source": "end"}
           for i in range(k_nom)]
    return opening + nom


def test_b54_null_determinism():
    names = NAMES8
    turns = _toy_cycle(names, 10)
    a = M.airtime_null(names, turns, "nomination", M.keyed_rng("k1"), 500)
    b = M.airtime_null(names, turns, "nomination", M.keyed_rng("k1"), 500)
    c = M.airtime_null(names, turns, "nomination", M.keyed_rng("k2"), 500)
    assert np.array_equal(a, b) and not np.array_equal(a, c)
    nt = M.phase_turns(turns, "nomination")
    a = M.influence_null(names, nt, M.keyed_rng("k1"), 500)
    b = M.influence_null(names, nt, M.keyed_rng("k1"), 500)
    c = M.influence_null(names, nt, M.keyed_rng("k2"), 500)
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def test_b54_standardized_undefined():
    assert M.standardized(0.5, [0.875] * 100) is None


def test_b54_null_uniformity_ks():
    """Synthetic data generated from the airtime null itself; the H3 pipeline (per-cycle
    standardized nomination-phase Gini, run mean, one-sided exact Mann-Whitney between two
    arms) must give p-values that pass KS uniformity at 0.01 over 200 replicates.
    Arms of 10 runs (not 5) are used so the exact MWU distribution is fine-grained enough for
    a continuous KS comparison; this checks calibration of the machinery, not the 5-run design."""
    names = NAMES8
    gen = M.keyed_rng("test|ks|synthetic")
    pvals = []
    for rep in range(200):
        arms = []
        for arm in range(2):
            run_means = []
            for run in range(10):
                zs = []
                for cyc in range(6):
                    k = 12
                    speakers = gen.choice(names, size=k)  # realized from the null chain itself
                    turns = _toy_cycle(names, 0)
                    turns += [{"speaker_identity": s, "discussion_stage": "nomination", "nominee_options": list(names),
                               "text": "", "nominee_resolved": None, "nomination_source": "end"} for s in speakers]
                    counts = np.array([[sum(s == n for s in speakers) for n in names]])
                    obs = float(M.gini_rows(counts)[0])
                    null = M.airtime_null(names, turns, "nomination", gen, 200)
                    zs.append(M.standardized(obs, null))
                run_means.append(np.mean(zs))
            arms.append(run_means)
        pvals.append(stats.mannwhitneyu(arms[1], arms[0], alternative="greater", method="exact").pvalue)
    assert stats.kstest(pvals, "uniform").pvalue > 0.01


# ---------------------------------------------------------------- B5.5
COOP = {"Cooperative argument", "Moral considerations", "C3", "C4", "C5"}


def test_b55_cooperative_index():
    labels = [{"Cooperative argument", "Moral considerations"}, {"Payoff maximization"},
              {"Cooperative argument", "Payoff maximization"}, {"other"}]
    idx, ties = M.cooperative_index(labels, COOP)
    assert idx == 0.25 and ties == 1
    assert M.legacy_cooperative_index(labels, COOP) == 0.5


def test_b55_persuasion():
    labels = ["Logos", "Logos", "Pathos", "Neutral", "Ethos"]
    assert M.persuasion_shares(labels) == {"Logos": 0.5, "Pathos": 0.25, "Ethos": 0.25}
    assert M.legacy_persuasion_shares(labels) == {"Logos": 0.4, "Pathos": 0.2, "Ethos": 0.2, "Neutral": 0.2}


def test_b55_deference_parser():
    ok = "DEFERS_TO: Kate\nBASIS: proposal\nMENTIONS_TENURE: no"
    assert M.parse_deference(ok, NAMES8) == {"defers_to": "Kate", "basis": "proposal", "mentions_tenure": False}
    tagged = "DEFERS_TO: Julia [months remaining: 14]\nBASIS: tenure\nMENTIONS_TENURE: yes"
    assert M.parse_deference(tagged, NAMES8)["defers_to"] == "Julia"
    assert M.parse_deference("DEFERS_TO: none\nBASIS: none\nMENTIONS_TENURE: no", NAMES8)["defers_to"] == "none"
    assert M.parse_deference("I think Kate", NAMES8) == "unparsed"


def test_jt_exact():
    # perfectly increasing groups: statistic = 3 pairs * 4 = 12 (2x2 per pair), p = 1/number of assignments
    g = [[1, 2], [3, 4], [5, 6]]
    stat, p, n = M.jt_exact(g)
    assert stat == 12 and n == 90 and p == pytest.approx(1 / 90)
    assert M.jt_statistic([[1, 1], [1, 2], [2, 3]]) == pytest.approx(3 + 4 + 3.5)  # hand-computed with half-ties
