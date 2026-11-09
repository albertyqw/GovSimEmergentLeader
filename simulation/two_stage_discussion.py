"""User-approved opening round and agent-invisible nomination adjudication."""

import re

from pathfinder import assistant, user
from simulation.interventions import (
    OPENING_TURN_PROMPT, OPENING_LAST_TURN_PROMPT,
    NOMINATION_TURN_PROMPT, NOMINATION_JUDGE_PROMPT,
)
from simulation.intervention_randomness import nomination_fallback
from simulation.measurement_prompts import conversation_prefix, resolve_name
from simulation.persona.cognition import utils


def utterance(model, persona, participants, memories, location, time, context,
              conversation, opening=False, opening_last=False):
    text = conversation_prefix(persona, participants, memories, location, time, context)
    text += "\nConversation so far:\n" + utils.conversation_to_string_with_dash(conversation) + "\n\n"
    text += (OPENING_LAST_TURN_PROMPT if opening_last else OPENING_TURN_PROMPT) if opening else NOMINATION_TURN_PROMPT
    lm, chain = model.start_chain_async(persona.identity.name, "cognition_converse", "converse_utterance")
    with user():
        lm += text
    with assistant():
        lm += "Response: "
        lm = model.gen(lm, name="two_stage_response", default_value="", stop_regex=r"\Z", chain=chain)
        raw = lm["two_stage_response"] or ""
    spoken = re.split(r"Conversation conclusion by me:|Next speaker:", raw, maxsplit=1)[0]
    spoken = re.sub(r"^\s*Response:\s*", "", spoken).strip()
    conclusion = re.search(r"Conversation conclusion by me:\s*(yes|no|No|Yes)", raw)
    ended = False if opening else (conclusion.group(1).lower() == "yes" if conclusion else True)
    enabled = (not opening or opening_last) and not ended
    match = re.search(r"Next speaker:\s*([^\n]*)", raw)
    nominee_raw = match.group(1).strip() if enabled and match else ("" if enabled else None)
    names = [p.identity.name for p in participants]
    resolved = None
    if enabled:
        if getattr(persona.identity, "stakes_months_remaining", None) is not None:
            candidate = resolve_name(nominee_raw, names)
            resolved = candidate if candidate in names else None
        else:
            # Same escaped, case-sensitive name-alternation as original Pathfinder select.
            found = re.search("(" + "|".join(re.escape(n) for n in names) + ")", nominee_raw)
            resolved = found.group(1) if found else None
    recorder = getattr(model, "recorder", None)
    if recorder is not None:
        recorder.parse_result("utterance", spoken)
        if not opening:
            recorder.parse_result("utterance_ended", ended,
                                  error=None if conclusion else "Missing conclusion; original yes default")
        if enabled:
            recorder.parse_result("next_speaker", resolved,
                                  error=None if resolved else "Invalid nomination; hidden judge required")
    model.end_chain(persona.identity.name, lm, chain=chain)
    persona.last_nominee_raw = nominee_raw
    persona.nomination_fallback = None
    return spoken, ended, resolved, lm.html()


def adjudicate(model, speaker, participants, conversation, raw_nominee, seed, cycle, turn):
    names = [p.identity.name for p in participants]
    event = {"cycle": cycle, "position": turn, "speaker_identity": speaker.identity.name,
             "raw_nomination": raw_nominee, "eligible_identities": names}
    prompt = NOMINATION_JUDGE_PROMPT + "\n\nEligible participants: " + ", ".join(names)
    prompt += f"\nNominating speaker: {speaker.identity.name}\nInvalid nomination: {raw_nominee!r}"
    prompt += "\nDiscussion data:\n" + utils.conversation_to_string_with_dash(conversation)
    lm, chain = model.start_chain_async("framework", "nomination_review", "nomination_judge")
    with user():
        lm += prompt
    with assistant():
        lm = model.gen(lm, name="judge_response", default_value="", stop_regex=r"\Z", chain=chain)
        raw = lm["judge_response"] or ""
    answer = re.search(r"^\s*ANSWER:\s*([^\n]+)\s*$", raw, re.I | re.M)
    reason = re.search(r"^\s*REASON:\s*(\S[^\n]*)", raw, re.I | re.M)
    candidate = resolve_name(answer.group(1), names) if answer else "unresolved"
    resolved = candidate if candidate in names and reason else None
    event.update(judge_output=raw, judge_answer=answer.group(1).strip() if answer else None,
                 judge_reason=reason.group(1).strip() if reason else None,
                 resolution_source="judge" if resolved else "random", random_fallback=None)
    if resolved is None:
        key = f"nominee_fallback|{seed}|{cycle}|{turn}"
        resolved = nomination_fallback(key, names)
        event["random_fallback"] = {"key": key, "options": names, "candidate": resolved, "applied": True}
    event["resolved_identity"] = resolved
    recorder = getattr(model, "recorder", None)
    if recorder is not None:
        event["judge_call_ids"] = list(getattr(recorder.local, "pending", []))
        event["cost"] = sum(recorder.buffers[cid].get("cost") or 0 for cid in event["judge_call_ids"])
        event["judge_model"] = recorder.config.llm.path.removeprefix("openrouter-")
        recorder.parse_result("judge_target", candidate, error=None if event["resolution_source"] == "judge" else "Unclear or invalid judge result")
    model.end_chain("framework", lm, chain=chain)
    if recorder is not None:
        event = recorder.record_nomination_judgment(event)
    return resolved, event
