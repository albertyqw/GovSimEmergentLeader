"""Fill the Apart hackathon template with the study write-up.

Reads the Apart template read-only from ~/Downloads and writes the .docx next to this script.
Run from the folder that contains analysis/ (repo root):  python3 -I submission/build_submission.py
"""
import re
import shutil
import struct
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
TEMPLATE = Path.home() / "Downloads" / "Apart Research Hackathon Submission Template.docx"
FIGS = next(p for p in (HERE.parent / "figures", HERE.parent / "analysis" / "figures") if p.is_dir())
OUT = HERE / "Emergent_Leadership_GovSim_Apart_Submission.docx"
FONT = '<w:rFonts w:ascii="Old Standard TT" w:cs="Old Standard TT" w:eastAsia="Old Standard TT" w:hAnsi="Old Standard TT"/>'

# ------------------------------------------------------------------ content
TITLE = "Conditions for Emergent Leadership in GovSim"
AUTHOR = ("Albert [surname]", "[Affiliation]")

ABSTRACT = (
    "When does a leader emerge in a group of LLM agents that share a resource and have no formal roles? "
    "Using GovSim's fishing commons in AgentElect's leaderless setting, we break the agents' symmetry three ways: "
    "one agent privately holds prosocial values and a plan (values), one has a much longer public tenure (stakes), "
    "and the group grows from 8 to 16 to 32 agents under a fixed 50-message discussion (coordination load). "
    "We ran 30 six-month simulations with Gemini 2.5 Flash and measured leadership three ways: whose proposals are "
    "adopted, centrality in a graph of mentions and nominations, and private peer nominations. Peers named the values "
    "agent most influential far more often than chance (45% of votes vs. 12.5%; p = 0.0008) and the long-tenure agent "
    "somewhat more often (34%, p = 0.04), but neither agent's proposals were adopted more often, and neither was "
    "significantly more central (p ≥ 0.17). Speaking order shows the same split: whoever spoke first in the randomized "
    "opening round received 59% of votes, yet its proposals were adopted no more often than anyone else's. Growing the "
    "group concentrated influence far beyond chance (standardized Gini of incoming references rising from 0.3 to 6.7; "
    "trend p = 1.3 × 10⁻⁶), while speaking turns stayed evenly shared. The values arm also over-harvested and was the "
    "only arm to collapse (2 of 5 runs). Who agents name as their leader follows salience rather than influence, and "
    "scale alone concentrates influence: both matter for overseeing multi-agent systems."
)

S = []  # list of (kind, payload)
H2 = lambda t: S.append(("h2", t))
H3 = lambda t: S.append(("h3", t))
P = lambda *runs: S.append(("p", runs))
B = lambda *runs: S.append(("bullet", runs))
N = lambda *runs: S.append(("num", runs))
TBL = lambda rows, widths, caption: S.append(("table", (rows, widths, caption)))
IMG = lambda name, width_in, caption: S.append(("img", (name, width_in, caption)))

H2("1. Introduction")
P("LLM agents increasingly work in groups: they negotiate, share resources and hand work to each other. In human groups, "
  "leaders often emerge without being appointed, and they shape what the group decides. If the same happens among agents, "
  "influence can concentrate in agents nobody chose or audits, and one agent's errors or goals can spread through the group. "
  "In the August 2026 OpenAI / Hugging Face incident, one agent with the largest remaining compute budget became a key "
  "coordinator of about 1,200 agents and used other agents to recruit low-budget agents into risky experiments (METR, 2026). "
  "Overseers need to know which conditions produce such de facto leaders.")
P("GovSim (Piatti et al., 2024) is a commons game in which LLM agents fish a shared lake, talk, and reflect each month. "
  "AgentElect (Faulkner et al., 2026) showed that elected leaders improve welfare and survival over leaderless groups. "
  "We ask the prior question: does a leader emerge with no formal role once the agents stop being identical? We break the "
  "symmetry in three ways, each motivated by prior evidence: prosocial values (AgentElect's voters favored prosocial "
  "leaders), unequal runway (the Hugging Face incident) and group size (coordination costs grow with N).")
P("Our main contributions are:")
N(("A pre-registered, leaderless GovSim protocol with three symmetry-breaking interventions, a negative-control baseline "
   "and mechanism-matched null models for airtime and influence (30 runs, all validated).", False))
N(("Evidence that perceived and behavioral leadership come apart: peers privately name the prosocial agent, and "
   "whoever happens to speak first, as their leader, but neither's proposals are adopted more often.", False))
N(("Evidence that group size alone concentrates influence far beyond chance, while speaking turns stay evenly shared.", False))

H2("2. Related Work")
P("GovSim (Piatti et al., 2024) measures whether LLM societies sustain a shared resource. AgentElect (Faulkner et al., 2026) "
  "adds policy and election phases and imposes or elects leaders; it reports that leadership helps but that social "
  "influence stays dispersed. Both study groups where a leader exists by design. We remove every scripted leadership cue "
  "and ask when one arises on its own, measuring it with AgentElect's influence graph plus two measures it lacks: "
  "adoption of each agent's proposals and private peer nominations. The stakes arm is modeled on the Hugging Face "
  "incident (METR, 2026), where leadership followed remaining budget rather than seniority.")

H2("3. Methods")
P(("Environment. ", True), ("GovSim's fishery as implemented in GovSimElect (commit 8cf0aba), No-Leader population. Each month "
  "agents privately choose a catch, a framework announcer reads out all catches, agents discuss (at most 50 messages), "
  "reflect, and the stock regrows by a random factor between 1 and 3 (capacity 100 tons; collapse below 5). Runs last six "
  "months. All agents are Gemini 2.5 Flash via OpenRouter at temperature 0. We removed every leadership cue from the "
  "prompts and made discussion two-stage: each agent speaks once in a seeded order, then speakers nominate the next "
  "speaker or end the discussion.", False))
TBL([["Condition", "N", "What differs"],
     ["Reference", "8", "AgentElect No-Leader with our neutral two-stage protocol (comparability anchor)"],
     ["Baseline", "8", "Reference plus private measurement questions (negative control)"],
     ["Values", "8", "One agent privately gets a prosocial value orientation and a sustainability plan"],
     ["Stakes", "8", "Public tags show months remaining; one agent has 16 months, others 3–8; leavers hand over to a household successor"],
     ["Coordination", "16, 32", "More agents; lake scaled with N; discussion still capped at 50 messages"]],
    [1500, 700, 7160], "Table 1. Conditions (five seeds each, 30 runs). The focal agent's slot rotates with the seed.")
P(("Leadership measures. ", True), ("(1) Proposal adoption: before each discussion every agent privately states the per-person "
  "limit it prefers; credit for the agreed limit is split among agents whose number matches. (2) Influence graph: a directed "
  "edge from speaker to each agent named in an utterance and to the agent it nominates to speak next (AgentElect's "
  "Algorithm 1, counting each name once per utterance and only nominations the agent made itself). We use incoming degree, "
  "betweenness and eigenvector centrality. (3) Peer nomination: after each discussion every agent privately names whose "
  "suggestions most influenced the decision, or 'no one'. Private answers never enter any prompt or memory.", False))
P(("Tests. ", True), ("Five primary tests, fixed before analysis and Holm-corrected. For the values and stakes agents we compare "
  "their percentile rank among peers with exact or Monte Carlo permutation of the focal label within each run (or cycle). "
  "For coordination we standardize each cycle's Gini of airtime and of incoming degree against null models that keep the "
  "real discussion length and speakers but redraw who is nominated or referenced (10,000 keyed draws), then test for an "
  "increasing trend across N = 8, 16, 32 with an exact Jonckheere–Terpstra test (Jonckheere, 1954). The reference–baseline "
  "difference serves as a noise floor.", False))

H2("4. Results")
P(("Group outcomes were near ceiling. ", True), ("All runs survived six months except two values runs, which collapsed in "
  "month 6. The values and stakes arms caught more and over-harvested more often than the two controls (over-usage 0.61 "
  "and 0.63 vs. 0.27–0.35, beyond the reference–baseline noise floor; Kruskal–Wallis p = 0.004). The values agent itself "
  "caught at or below the peer average in 4 of 5 runs.", False))
TBL([["Hypothesis", "Statistic (0.5 = chance for ranks)", "p", "Holm p"],
     ["H1a Values agent's proposals adopted more", "rank 0.53", "0.44", "0.72"],
     ["H1b Values agent more central (eigenvector)", "rank 0.63", "0.17", "0.51"],
     ["H2 16-month agent more central (in-degree)", "rank 0.52", "0.36", "0.72"],
     ["H3a Airtime concentrates as N grows", "z = −3.3 / −2.9 / −0.5", "0.003", "0.012"],
     ["H3b Influence concentrates as N grows", "z = 0.3 / 3.5 / 6.7", "1.3 × 10⁻⁶", "6.6 × 10⁻⁶"]],
    [3700, 2560, 1550, 1550],
    "Table 2. Primary tests. Ranks are the focal agent's mean percentile rank among peers; z is the run-mean Gini "
    "standardized against its null model for N = 8 / 16 / 32 (nomination phase). Five runs per condition.")
P(("Peers see a leader that behavior does not show. ", True), ("Private votes were nearly unanimous within each month: "
  "96–99% of named votes went to one agent. The values agent received 45% of named votes (chance 12.5%; exact permutation "
  "p = 0.0008, exploratory) and was the top vote-getter in 3 of 5 runs; the 16-month agent received 34% (p = 0.04). "
  "Framework summaries credited the values agent by name (\"Julia's framework\"), and 14.5% of all agents' retrieved "
  "memories named it, against 0.1% for each peer. Yet its proposals were not adopted more often (H1a) and its centrality "
  "advantage was not significant (H1b; p = 0.06 with PageRank, 0.11 excluding months it spoke first). Figure 1 shows "
  "the gap run by run.", False))
IMG("paper_fig1_focal_share.png", 6.3, "Figure 1. Share of named peer votes (dark) and of incoming references in the "
    "influence graph (light) received by the focal agent, per seed. Dashed line: chance (1/8).")
P(("Speaking first wins votes, not agreement. ", True), ("The opening order is a seeded random draw, so its effect is "
  "causal within our protocol. Across the 8-agent arms, the first speaker received 59% of named votes (chance 12.5%; "
  "within-month permutation p < 0.001; 41% vs. 4.7% chance at N = 16 and 32), and votes fell off with speaking position. "
  "Yet the first speaker's private limit was adopted no more often than anyone else's (credit 0.10 vs. 0.10, p = 0.51), "
  "and its public proposal matched the final agreement no more often than other proposers' (0.79 vs. 0.85). This also "
  "explains part of the values result: the values agent opened 3 of its 30 months, and excluding them its vote share "
  "stays at 41% but the permutation test weakens to p = 0.065 (stakes: p = 0.18).", False))
P(("Size concentrates influence, not airtime. ", True), ("As the group grew, references and nominations piled onto a few "
  "agents far beyond what random targeting predicts (Figure 2; H3b). This held when we added nominations routed by the "
  "framework's judge or random fallback, and in both discussion phases. Speaking turns, by contrast, were more evenly "
  "spread than a random nomination chain at every N; the significant H3a trend is a move toward chance, not past it. "
  "At N = 32, 70% of agents never spoke after the opening round.", False))
IMG("paper_fig2_concentration_vs_N.png", 4.4, "Figure 2. Concentration of influence (blue) and airtime (orange) relative "
    "to null models, nomination phase. Dots are runs; bars are means. Zero is chance.")
P(("Robustness. ", True), ("H1 and H2 stay non-significant under every sensitivity check: excluding months the focal agent "
  "opened, adding framework-routed nominations, betweenness or eigenvector in place of degree, and a matched-slot comparison "
  "with the same speaking positions in the baseline. Reference and baseline differ by 0.1–0.4 SD on group outcomes, smaller "
  "than the values and stakes effects on over-usage.", False))

H2("5. Discussion and Limitations")
P("Two results matter for multi-agent oversight. First, perceived leadership can diverge from measurable influence: agents "
  "named the prosocial agent, and whoever spoke first, as their leader even though the group did not follow their numbers "
  "more than anyone else's. Who agents credit seems to track salience rather than influence. Monitoring that relies on what agents say about each other, or on behavioral traces alone, can miss "
  "half the picture. Second, size alone concentrates influence: with a fixed communication budget, a few agents attract "
  "most references as the group grows, even when turns are shared fairly. Bottlenecks of this kind are where one agent's "
  "mistakes or goals would spread. The values arm's collapses also caution that a prosocial agent who is seen as a leader "
  "does not by itself make the group more sustainable.")
H3("Limitations")
P("Five seeds per arm gives low power for the individual-agent tests, and the focal agent's slot is confounded with the "
  "seed. One model was tested, and its logs show no reasoning tokens, so it likely ran without extended thinking. "
  "Agents often misnamed the next speaker, so 35–47% of hand-offs were routed by a random fallback; we excluded these from "
  "the main graphs. The peer-nomination question asks about influence directly, is exploratory, and is strongly shaped "
  "by speaking order. In the stakes arm, "
  "agents in their final month still caught 1.8 tons more than peers (p = 0.002), so succession did not fully align "
  "incentives.")
H3("Future Work")
P("Judge agents' written reasoning for explicit deference (prompt and cost calibration done), test more seeds and models, "
  "and vary the communication budget with N to separate size from airtime scarcity.")

H2("6. Conclusion")
P("Breaking symmetry among identical LLM agents, by giving one agent prosocial values or simply letting it speak first, "
  "produced a leader in the eyes of its peers, but not in what the group adopted. Scaling the group produced concentrated influence without any intervention. Studies and safeguards for agent "
  "collectives should measure both perceived and behavioral leadership, and should expect influence to concentrate as "
  "groups grow.")

H2("Code and Data")
B(("Code repository: ", True), ("github.com/albertyqw/GovSimEmergentLeader (branch emergent-leadership; fork of "
  "rfaulkner/GovSimElect). Analysis scripts: [link to analysis code].", False))
B(("Data: ", True), ("raw logs of all 30 runs (prompts, completions, costs) [link]. Total simulation cost about $50.", False))

H2("References")
for ref in [
    "Faulkner, R. et al. (2026). Evaluating Cooperation in LLM Social Groups through Elected Leadership. arXiv:2604.11721. Code: github.com/rfaulkner/GovSimElect.",
    "Jonckheere, A. R. (1954). A distribution-free k-sample test against ordered alternatives. Biometrika, 41, 133–145.",
    "METR (2026, August 26). Brief independent investigation of agents' behavior, reasoning and collaboration in the OpenAI / Hugging Face hacking incident. metr.org/hugging-face-incident-report-aug-2026.pdf.",
    "Murphy, R. O., Ackermann, K. A., & Handgraaf, M. J. J. (2011). Measuring social value orientation. Judgment and Decision Making, 6(8).",
    "Piatti, G. et al. (2024). Cooperate or Collapse: Emergence of Sustainable Cooperation in a Society of LLM Agents. arXiv:2404.16698. Code: github.com/giorgiopiatti/GovSim.",
]:
    P((ref, False))

H2("LLM Usage Statement")
P("[Edit before submitting.] Claude (Anthropic) and Codex (OpenAI) helped implement the simulation changes and analysis "
  "code and drafted this report from the author's proposal. All numbers come from the analysis scripts.")


# ------------------------------------------------------------------ XML helpers
def run(text, bold=False, italic=False, size=None):
    rpr = FONT + ('<w:b w:val="1"/><w:bCs w:val="1"/>' if bold else "") + ('<w:i w:val="1"/><w:iCs w:val="1"/>' if italic else "")
    if size:
        rpr += f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
    return f'<w:r><w:rPr>{rpr}<w:rtl w:val="0"/></w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def para(runs, num=None, jc="both"):
    body = "".join(run(t, b) for t, b in runs)
    numpr = f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num}"/></w:numPr>' if num else ""
    ind = '<w:ind w:left="720" w:hanging="360"/>' if num else ""
    return (f'<w:p><w:pPr>{numpr}<w:spacing w:after="120" w:line="264" w:lineRule="auto"/>{ind}<w:jc w:val="{jc}"/>'
            f'<w:rPr>{FONT}</w:rPr></w:pPr>{body}</w:p>')


def heading(template_xml, text):
    template_xml = re.sub(r"<w:bookmark(?:Start|End)\b[^>]*/>", "", template_xml)
    return re.sub(r'(<w:t xml:space="preserve">)[^<]*(</w:t>)', lambda m: m.group(1) + escape(text) + m.group(2), template_xml, count=1)


def caption(text):
    return (f'<w:p><w:pPr><w:spacing w:before="60" w:after="200" w:line="240" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr>'
            f'{run(text, italic=True, size=18)}</w:p>')


def table(rows, widths):
    border = ('<w:tblBorders>' + "".join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
                                         for s in ("top", "left", "bottom", "right", "insideH", "insideV")) + '</w:tblBorders>')
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    out = [f'<w:tbl><w:tblPr><w:tblW w:w="{sum(widths)}" w:type="dxa"/>{border}<w:tblLayout w:type="fixed"/>'
           f'<w:tblCellMar><w:left w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    for i, r in enumerate(rows):
        cells = []
        for w, t in zip(widths, r):
            shade = '<w:shd w:val="clear" w:color="auto" w:fill="EEEEEE"/>' if i == 0 else ""
            cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shade}</w:tcPr><w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
                         f'{run(t, bold=(i == 0), size=18)}</w:p></w:tc>')
        out.append("<w:tr>" + "".join(cells) + "</w:tr>")
    return "".join(out) + "</w:tbl>"


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def image(rid, idx, path, width_in):
    w, h = png_size(path)
    cx = int(width_in * 914400)
    cy = int(cx * h / w)
    return (f'<w:p><w:pPr><w:spacing w:before="120" w:after="0"/><w:jc w:val="center"/></w:pPr><w:r><w:drawing>'
            f'<wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{100 + idx}" name="Figure {idx}"/>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
            f'<pic:nvPicPr><pic:cNvPr id="{100 + idx}" name="fig{idx}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            f'</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')


# ------------------------------------------------------------------ assemble
def main():
    work = HERE / "_build"
    shutil.rmtree(work, ignore_errors=True)
    with zipfile.ZipFile(TEMPLATE) as z:
        z.extractall(work)
    doc = (work / "word" / "document.xml").read_text(encoding="utf8")
    b0 = doc.find("<w:body>") + len("<w:body>")
    b1 = doc.find("<w:sectPr>", b0)
    head, body, tail = doc[:b0], doc[b0:b1], doc[b1:]

    # top-level children
    kids, depth = [], 0
    for m in re.finditer(r"<(/?)w:(p|tbl)\b[^>]*?(/?)>", body):
        if m.group(3):
            continue
        if not m.group(1):
            if depth == 0:
                start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                kids.append(body[start:m.end()])
    title_tbl = kids[1]
    h2_tpl, h3_tpl = kids[4], kids[49]

    # title, authors, abstract inside the layout table
    title_tbl = title_tbl.replace(">PROJECT TITLE<", f">{escape(TITLE)}<", 1)
    # replace the nested 6-slot author grid with one centered author paragraph
    i = title_tbl.find("Author name 1")
    s = title_tbl.rfind("<w:tbl>", 0, i)
    depth, j = 0, s
    for m in re.finditer(r"<(/?)w:tbl>", title_tbl[s:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            j = s + m.end()
            break
    author_p = (f'<w:p><w:pPr><w:spacing w:after="200" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>'
                f'{run(AUTHOR[0])}<w:r><w:br/></w:r>{run(AUTHOR[1])}</w:p>')
    title_tbl = title_tbl[:s] + author_p + title_tbl[j:]
    abs_p = re.search(r"<w:p [^>]*>(?:(?!</w:p>).)*?Summarize your project(?:(?!</w:p>).)*?</w:p>", title_tbl, re.S).group(0)
    ppr = re.search(r"<w:pPr>.*?</w:pPr>", abs_p, re.S).group(0).replace('<w:u w:val="single"/>', "")
    title_tbl = title_tbl.replace(abs_p, f"<w:p>{ppr}{run(ABSTRACT)}</w:p>")
    assert "Author name" not in title_tbl and "Summarize" not in title_tbl

    rels = (work / "word" / "_rels" / "document.xml.rels").read_text(encoding="utf8")
    (work / "word" / "media").mkdir(exist_ok=True)
    out, fig_n = [kids[0], title_tbl, kids[2]], 0
    for kind, payload in S:
        if kind == "h2":
            out.append(heading(h2_tpl, payload))
        elif kind == "h3":
            out.append(heading(h3_tpl, payload))
        elif kind == "p":
            out.append(para([(r, False) if isinstance(r, str) else r for r in payload]))
        elif kind in ("bullet", "num"):
            num = 3 if kind == "bullet" else 5
            out.append(para(payload, num=num, jc="left"))
        elif kind == "table":
            rows, widths, cap = payload
            out.append(caption(cap))
            out.append(table(rows, widths))
            out.append(para([("", False)]))
        elif kind == "img":
            name, width, cap = payload
            fig_n += 1
            rid = f"rIdFig{fig_n}"
            shutil.copy(FIGS / name, work / "word" / "media" / f"fig{fig_n}.png")
            rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/fig{fig_n}.png"/></Relationships>')
            out.append(image(rid, fig_n, FIGS / name, width))
            out.append(caption(cap))
    tail = tail.replace('w:right="1440" w:header="720" w:footer="720"/>', 'w:right="1440" w:header="720" w:footer="720" w:gutter="0"/>')
    (work / "word" / "document.xml").write_text(head + "".join(out) + tail, encoding="utf8")
    (work / "word" / "_rels" / "document.xml.rels").write_text(rels, encoding="utf8")
    ct = (work / "[Content_Types].xml").read_text(encoding="utf8")
    if 'Extension="png"' not in ct:
        ct = ct.replace("<Default ", '<Default ContentType="image/png" Extension="png"/><Default ', 1)
    (work / "[Content_Types].xml").write_text(ct, encoding="utf8")

    OUT.unlink(missing_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(work.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(work).as_posix())
    shutil.rmtree(work)
    print(OUT)


if __name__ == "__main__":
    main()
