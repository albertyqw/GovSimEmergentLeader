"""Deterministic per-person proposal extraction from public utterance text (B2.10).

A proposal is a forward-looking per-person catch the speaker advocates for the coming month
(including endorsing someone else's number). The text is split into sentences (markdown
asterisks removed). Candidate numbers come from:
  P1  number + tons + per-person unit        "5 tons each", "0 or 1 ton per person"
  P2  proposal verb ... number + tons        "I propose we stick to 5 tons", "reduce my catch to 6 tons"
  P3  number + tons + next/upcoming month    "5 tons next month", "5 tons again"
  P4  each (of us) + catch verb ... number   "each of us catching 5-7 tons"
  P5  individual catch/limit ... number      "individual catches ideally at 6 tons"
  L   number-ton limit/quota/target/...      "the 6-ton limit", "a **3-ton individual limit**"
Sentence rules:
  - A sentence with a past marker (this/last/past month, previous, earlier, remembered, we set,
    agreed upon/on, aimed for, so far, stuck to, started with, caught) and neither a time-forward
    marker (next/upcoming/coming month, going forward, from now on, for the next) nor a forward
    verb (propose, continue, commit, support, maintain, keep, ...) is skipped.
  - L candidates need a forward marker or forward verb (propose, suggest, continue, commit,
    support, maintain, keep, stick with) in the sentence.
Number rules: skip past-tense catch reports and references to old agreements ("caught 5 tons",
"the initial 5-ton agreement"), group totals ("a total of 40
tons", "40 tons collectively"; not applied to explicit per-person units or to 0), and stock
quantities ("leave 50 tons", "96 tons removed", "before regeneration"). Ranges take the lower
bound ("5-7", "0 or 1"), matching the framework extractor's first-integer rule.
Audit: results/proposal_audit.csv (tuning sample) and results/proposal_audit_holdout.csv.
"""
import re

NUM = r"(\d+(?:\.\d+)?)(?:\s*(?:-|–|to|or)\s*\d+(?:\.\d+)?)?"
TONS = r"\s*-?\s*tons?\b"
PER = (r"(?:per\s+(?:person|fisherman|fisher|fishermen|individual|head|household|boat)|each|apiece|"
       r"individually|per\s+capita)")
VERB = (r"\b(?:propose|proposing|suggest|suggesting|recommend|should|let's|let\s+us|aim(?:ing)?\s+(?:for|to)|"
        r"stick(?:ing)?\s+(?:to|with)|plan(?:ning)?\s+to|i\s+will|i'll|we\s+will|we'll|going\s+to|"
        r"commit(?:ted|ting)?\s+to|reduc\w*(?:\s+(?:my|our)\s+catch(?:es)?)?\s+to|lower\w*(?:\s+(?:it|my\s+catch))?\s+to|"
        r"count\s+me\s+in\s+for)\b")
P1 = re.compile(NUM + TONS + r"(?:\s+of\s+fish)?(?:\s+\w+){0,3}?\s+" + PER + r"\b", re.I)
P2 = re.compile(VERB + r"[^.?!\d]{0,25}?" + NUM + TONS, re.I)
P3 = re.compile(NUM + TONS + r"(?:\s+of\s+fish)?\s+(?:next\s+month|again|for\s+(?:the\s+)?(?:next|upcoming|coming)\s+month|"
                r"(?:in\s+)?the\s+(?:upcoming|coming)\s+month)", re.I)
P4 = re.compile(r"\beach(?:\s+of\s+us)?\s+(?:to\s+)?(?:catch|catching|take|taking|fish|fishing|harvest|harvesting)\b"
                r"[^.?!\d]{0,15}?" + NUM + TONS, re.I)
P5 = re.compile(r"\bindividual(?:ly)?\s+(?:catch(?:es)?|limits?|quotas?)\b[^.?!\d]{0,20}?" + NUM + TONS, re.I)
L = re.compile(NUM + r"\s*-\s*tons?\s+(?:\w+\s+){0,2}?(?:limit|quota|cap|target|maximum|agreement|commitment|plan|range|mark)\b", re.I)

PAST_SENT = re.compile(r"\b(?:this\s+month|last\s+month|this\s+past\s+month|past\s+month|previous(?:ly)?|earlier|"
                       r"remembered|we\s+set|agreed[-\s]upon|we\s+agreed|agreed\s+(?:on|to)|aimed\s+for|so\s+far|stuck\s+to|"
                       r"started\s+(?:with|at)|caught)\b", re.I)
FWD_TIME = re.compile(r"\b(?:next\s+month|upcoming\s+month|coming\s+month|going\s+forward|from\s+now\s+on|"
                      r"for\s+the\s+next|moving\s+forward|in\s+the\s+future)\b", re.I)
FWD_VERB = re.compile(r"\b(?:propose|proposal|suggest|recommend|continue|continuing|commit\w*|support|maintain\w*|"
                      r"plan(?:ning)?\s+to|i'll|i\s+will|we'll|we\s+will|going\s+to|let's|"
                      r"keep(?:ing)?|stick(?:ing)?\s+with|safest|on\s+board|in\s+favor)\b", re.I)
PAST_NUM = re.compile(r"\b(?:caught|took|harvested|fished|got|catch\s+of|removed|removing|initial|original|old|previous|existing)\b[^.?!]{0,40}$", re.I)
TOTAL_BEFORE = re.compile(r"\b(?:total|collective(?:ly)?|combined|group|overall|altogether|in\s+all|sum)\b[^.?!\d]{0,35}$", re.I)
TOTAL_AFTER = re.compile(r"^[^.?!\d]{0,20}\b(?:total|in\s+total|collective(?:ly)?|combined|altogether|overall|"
                         r"for\s+the\s+(?:whole\s+)?group|as\s+a\s+group)\b", re.I)
STOCK = re.compile(r"(?:\b(?:leave|leaving|left|keep|population|lake\s+at|start(?:ed|ing)?\s+(?:at|with)|capacity\s+of)\b[^.?!\d]{0,20}$)", re.I)
STOCK_AFTER = re.compile(r"^[^.?!\d]{0,25}\b(?:before\s+(?:regeneration|reproduction)|in\s+the\s+lake|left|removed|"
                         r"for\s+(?:regeneration|reproduction))\b", re.I)
SENT = re.compile(r"(?:[^.?!\n]|\.(?=\d))+(?:[.?!]+|$)")  # keep decimals like 6.25 intact


def _candidates(sentence):
    forward_time = bool(FWD_TIME.search(sentence))
    if PAST_SENT.search(sentence) and not forward_time and not FWD_VERB.search(sentence):
        return []
    out = []
    for pat, per_person in ((P1, True), (P2, False), (P3, False), (P4, True), (P5, True)):
        for m in pat.finditer(sentence):
            out.append((m.start(1), float(m.group(1)), per_person, m.end()))
    if forward_time or FWD_VERB.search(sentence):
        for m in L.finditer(sentence):
            out.append((m.start(1), float(m.group(1)), True, m.end()))
    keep = {}
    for start, value, per_person, end in out:
        before = sentence[max(0, start - 50):start]
        after = sentence[end:end + 35]
        if PAST_NUM.search(before) or STOCK.search(before) or STOCK_AFTER.search(after):
            continue
        if not per_person and value != 0 and (TOTAL_BEFORE.search(before) or TOTAL_AFTER.search(after)):
            continue
        keep.setdefault(start, value)
    return sorted(keep.items())


def extract(text):
    """Return list of (value, absolute_start) per-person proposals in order."""
    text = (text or "").replace("*", "")
    hits = []
    for s in SENT.finditer(text):
        hits += [(v, s.start() + pos) for pos, v in _candidates(s.group(0))]
    return hits


# Plausibility rule (added after the audits, applied to every use): a per-person proposal cannot
# exceed twice the full-stock fair share, capacity / N * 2 = 25 tons at every N in this study
# (capacity scales with N). Removes stock forecasts such as "100 tons for next month".
MAX_PER_PERSON = 25.0


def extract_plausible(text, max_value=MAX_PER_PERSON):
    return [h for h in extract(text) if h[0] <= max_value]


def first_proposal(text, max_value=MAX_PER_PERSON):
    hits = extract_plausible(text, max_value)
    return hits[0][0] if hits else None
