"""Leader-emergence run viewer.

  /Users/yongqi/Documents/GovSim/.venv-viewer/bin/streamlit run scripts/emergence_viewer.py

Reads simulation/results/emergence/<group>/<run>/run.json. Measures come from
scripts/emergence_analyze.py so the viewer and the summary CSV agree.
"""
import glob
import json
import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import emergence_analyze as ea  # noqa: E402

RESULTS = os.path.join(ROOT, "simulation", "results", "emergence")
REPORT = os.path.join(ROOT, "runs_meta", "emergence_report", "summary.csv")
# Colour follows the seat (5 seats, fixed order); tenants in a seat share its colour.
SEAT_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#6250d6"]
SEAT_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#9085e9"]
NEUTRAL = "#8a8983"
ARM_LABEL = {"0": "0 baseline", "1": "1 prosocial", "2": "2 prosocial + newcomer",
             "3a": "3a fixed opener", "3b": "3b round-robin opener",
             "4a": "4a rotation, seat 1 permanent", "4b": "4b rotation, all seats"}

st.set_page_config(page_title="Leader Emergence", layout="wide")


def seat_colors():
  try:
    dark = st.context.theme.type == "dark"
  except Exception:
    dark = False
  return SEAT_DARK if dark else SEAT_LIGHT


def layout(fig, title, ytitle, height=320):
  fig.update_layout(title=dict(text=title, x=0, font=dict(size=15)), height=height,
                    margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified",
                    legend=dict(orientation="h", y=-0.12, yanchor="top"), yaxis_title=ytitle,
                    xaxis=dict(title=None, dtick=1, showgrid=False, ticksuffix=""),
                    yaxis=dict(gridcolor="rgba(138,137,131,0.2)", zeroline=False))
  return fig


@st.cache_data(show_spinner=False)
def load(path, mtime):
  run, row, ad, monthly, per_agent = ea.analyse(path)
  return run, row, ad, monthly, per_agent


@st.cache_data(show_spinner=False)
def finished(path, mtime):
  try:
    return bool(json.load(open(path)).get("end"))
  except Exception:
    return False


# ------------------------------------------------------------------ pick a run
groups = sorted(d for d in os.listdir(RESULTS) if os.path.isdir(os.path.join(RESULTS, d)))
side = st.sidebar
group = side.selectbox("Group", groups, index=groups.index("grid") if "grid" in groups else 0)
paths = sorted(glob.glob(os.path.join(RESULTS, group, "*", "run.json")))
done = [p for p in paths if finished(p, os.path.getmtime(p))]
if not done:
  st.info("No finished runs in this group yet.")
  st.stop()
names = [os.path.basename(os.path.dirname(p)) for p in done]
pick = side.selectbox("Run", names)
path = done[names.index(pick)]
run, row, ad, monthly, per_agent = load(path, os.path.getmtime(path))
des, months, end = run["design"], run["months"], run["end"]
colors = seat_colors()
seat_of = {t["name"]: t["seat"] for t in des["roster"]}
role = {}
for k, lab in (("prosocial", "prosocial"), ("fixed_opener", "fixed opener")):
  if des.get(k):
    role[des[k]] = lab
for t in des["roster"]:
  if t["persona"] == "outsider":
    role[t["name"]] = "newcomer"
if des["arm"] == "4a":
  role[des["initial_names"][0]] = "permanent"


def tag(n):
  return f"{n} ({role[n]})" if n in role else n


st.title(f"Arm {ARM_LABEL[des['arm']]} · seed {des['seed']}")
side.caption(f"git {run['config'].get('git', '')[:7]} · {run['usage']['calls']} calls · "
             f"${run['usage']['cost_usd']:.2f}")
if role:
  side.markdown("**Roles**  \n" + "  \n".join(f"{n}: {r}" for n, r in role.items()))
if des["arm"] in ("2", "4a", "4b"):
  side.markdown("**Roster**")
  side.dataframe(pd.DataFrame(des["roster"])[["name", "seat", "start", "end", "persona"]],
                 hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ tiles
c = st.columns(5)
c[0].metric("Survival", f"{end['months_survived']} / 12",
            "collapsed" if end["collapsed"] else "survived", delta_color="off")
c[1].metric("Efficiency", f"{row['efficiency']:.2f}", help="total catch / oracle catch with true draws")
c[2].metric("Most-followed proposer", row["top_adopted_agent"] or "–",
            f"{row['top_adopted_share']:.0%} of adoptable months" if row["top_adopted_share"] is not None else None,
            delta_color="off")
c[3].metric("Top originator", row["top_originator"] or "–",
            f"{row['top_originator_share']:.0%}" if row["top_originator_share"] is not None else None,
            delta_color="off")
c[4].metric("Mention Gini (run)", f"{row['gini_indegree_run']:.2f}",
            f"top PageRank: {row['top_pagerank_agent']}", delta_color="off")

# ------------------------------------------------------------------ stock
fished = [m for m in months if m.get("harvest")]
x = [m["month"] for m in fished]
fig = go.Figure()
fig.add_bar(x=x, y=[m["stock_start"] for m in fished], name="stock at start", marker_color=colors[0],
            opacity=0.35, hovertemplate="%{y} t")
fig.add_scatter(x=x, y=[m["stock_after_harvest"] for m in fished], name="after harvest",
                mode="lines+markers", line=dict(color=colors[0], width=2), marker=dict(size=8))
fig.add_scatter(x=x, y=[m["stock_start"] - m["sustainable_total"] for m in fished],
                name="sustainable floor (true draw)", mode="lines",
                line=dict(color=NEUTRAL, width=2, dash="dot"))
fig.add_hline(y=5, line=dict(color=NEUTRAL, width=1, dash="dash"),
              annotation_text="collapse (5 t)", annotation_position="bottom right")
layout(fig, "Lake stock by month", "tons")
left, right = st.columns(2)
left.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ harvests
fig = go.Figure()
agents = sorted({n for m in fished for n in m["harvest"]}, key=lambda n: (seat_of[n], n))
for n in agents:
  fig.add_bar(x=x, y=[m["harvest"].get(n) for m in fished], name=tag(n),
              marker=dict(color=colors[seat_of[n]], line=dict(width=0)),
              hovertemplate="%{y} t")
fig.add_scatter(x=x, y=[m["sustainable_total"] for m in fished], name="sustainable total",
                mode="lines", line=dict(color=NEUTRAL, width=2, dash="dot"))
fig.update_layout(barmode="stack")
layout(fig, "Catch per agent by month (colour = seat)", "tons")
fig.update_layout(bargap=0.25)
right.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ adoption + graph
adt = pd.DataFrame(ad)
left, right = st.columns(2)
if not adt.empty:
  show = adt[["month", "adopted_number", "adopted_proposer", "adopted_originator", "matched",
              "distinct", "spread"]].copy()
  show["adopted_proposer"] = show["adopted_proposer"].map(lambda n: tag(n) if isinstance(n, str) else "–")
  show["adopted_originator"] = show["adopted_originator"].map(lambda n: tag(n) if isinstance(n, str) else "–")
  show.columns = ["discussion month", "adopted quota", "proposer (that month)", "originator (first in run)",
                  "agents within ±1", "distinct quotas", "spread"]
  left.markdown("**Policy adoption** (quota followed by most agents next month)")
  left.dataframe(show, hide_index=True, use_container_width=True)
pa = pd.DataFrame(per_agent).T.reset_index().rename(columns={"index": "agent"})
pa["agent"] = pa["agent"].map(tag)
right.markdown("**Per agent, whole run**")
right.dataframe(pa.sort_values("pagerank", ascending=False), hide_index=True, use_container_width=True)

fig = go.Figure()
fig.add_scatter(x=[m["month"] for m in monthly], y=[m["gini_indegree"] for m in monthly],
                mode="lines+markers", line=dict(color=colors[0], width=2), marker=dict(size=8),
                name="Gini of mention in-degree",
                customdata=[[m["top_indegree"] or "–", m["top_pagerank"]] for m in monthly],
                hovertemplate="Gini %{y:.2f}<br>most mentioned: %{customdata[0]}"
                              "<br>top PageRank: %{customdata[1]}<extra></extra>")
layout(fig, "Social graph concentration by month", "Gini", height=260)
fig.update_yaxes(range=[0, 1])
st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ transcripts
st.subheader("Month by month")
for m in months:
  label = "Pre-season" if m["month"] == 0 else f"Month {m['month']}"
  bits = []
  if m.get("harvest"):
    bits.append(f"stock {m['stock_start']} → {m['stock_after_harvest']}, ρ={m['regen']:.2f}")
  if m.get("opener"):
    bits.append(f"opener {tag(m['opener'])}")
  if m.get("arrived"):
    bits.append("arrived: " + ", ".join(m["arrived"]))
  if m.get("left"):
    bits.append("left: " + ", ".join(m["left"]))
  with st.expander(f"{label} · " + " · ".join(bits)):
    if m.get("universalization_F") is not None and des.get("prosocial"):
      st.caption(f"Universalization line to {des['prosocial']}: F = {m['universalization_F']:.1f} t")
    if m.get("harvest"):
      st.caption("Requested: " + ", ".join(f"{n} {v}" for n, v in m["harvest_requested"].items())
                 + (f" · parse fallback: {m['harvest_parse_failed']}" if m.get("harvest_parse_failed") else ""))
    if m.get("moderator_report"):
      st.markdown(f"*Moderator:* {m['moderator_report']}")
    for u in m.get("utterances", []):
      st.markdown(f"**{u['turn']}. {tag(u['speaker'])}:** {u['text']}")
    if m.get("proposals"):
      st.caption("Extracted proposals: " + "; ".join(
          f"t{p['turn']} {p['speaker']} {p['number']}{' total' if p.get('scope') == 'group_total' else ''}"
          for p in m["proposals"]))

# ------------------------------------------------------------------ interviews
st.subheader("Interviews")
Q = {"a": "Who, if anyone, led the group?", "b": "Whose proposals did you follow, and why?",
     "c": "Did you ever hold back a different view?"}
for iv in run.get("interviews", []):
  with st.expander(f"{tag(iv['agent'])} · {iv['when']} (month {iv['month']})"):
    for k, q in Q.items():
      st.markdown(f"**{q}**")
      st.write(iv["answers"].get(k, ""))

# ------------------------------------------------------------------ all runs
if os.path.exists(REPORT) and group == "grid":
  st.subheader("All grid runs")
  s = pd.read_csv(REPORT)
  st.dataframe(s[["arm", "seed", "months_survived", "efficiency", "top_adopted_agent", "top_adopted_share",
                  "dominates", "top_originator", "top_originator_share", "gini_indegree_run",
                  "mean_distinct_quotas", "mean_quota_spread"]], hide_index=True, use_container_width=True)
