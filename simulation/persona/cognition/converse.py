"""Converse cognition component — handles group conversations."""

import datetime
import random

from simulation.utils import models as sim_models
from simulation.persona import common
from simulation.persona.cognition import component
from simulation.persona.cognition import converse_prompts
from simulation.persona.cognition import reflect_prompts
from simulation.persona.cognition import retrieve as retrieve_mod
from simulation.interventions import ANNOUNCER_TEMPLATE
from simulation.intervention_randomness import opener_slot
from simulation import measurement_prompts
from simulation.persona.cognition.utils import render_name


class ConverseComponent(component.Component):
  """Handles group conversation cognition."""

  def __init__(
      self,
      model: sim_models.ModelWandbWrapper,
      model_framework: sim_models.ModelWandbWrapper,
      retrieve: retrieve_mod.RetrieveComponent,
      cfg=None,
  ):
    """Initialize the converse component."""
    super().__init__(model, model_framework, cfg)
    self.retrieve = retrieve

  def converse_group(
      self,
      target_personas,
      current_location: str,
      current_time: datetime.datetime,
      current_context: str,
      agent_resource_num: dict[str, int],
      mayoral_agenda: str | None = None,
      harvest_report: str | None = None,
      leader_persona=None,
      debug: bool = False,
      intervention_seed: int | None = None,
      intervention_cycle: int | None = None,
  ) -> tuple[list[tuple[str, str]], str]:
    """Conduct a group conversation among personas."""
    current_conversation: list[
        tuple[common.PersonaIdentity, str]
    ] = []

    html_interactions = []
    turn_records = []
    if leader_persona:
      current_leader_id = leader_persona.identity
    else:
      if getattr(self.cfg, "neutral_announcer", False):
        current_leader_id = common.PersonaIdentity("framework", "Announcer")
      else:
        current_leader_id = common.PersonaIdentity(
            "framework", "Anonymous Leader",
        )

    if (
        self.cfg.inject_resource_observation
        and self.cfg.inject_resource_observation_strategy
        == "individual"
    ):
      for persona in target_personas:
        p = self.other_personas[persona.identity.name]
        current_conversation.append(
            (
                p.identity,
                (
                    "This month, I caught"
                    f" {agent_resource_num[p.agent_id]}"
                    " tons of fish!"
                ),
            ),
        )
        html_interactions.append(
            "<strong>Framework</strong>:  This month, I caught"
            f" {agent_resource_num[p.agent_id]} tons of fish!"
        )
    elif (
        self.cfg.inject_resource_observation
        and self.cfg.inject_resource_observation_strategy
        == "manager"
    ):
      if getattr(self.cfg, "neutral_announcer", False) and not leader_persona:
        current_conversation.append(
            (current_leader_id, ANNOUNCER_TEMPLATE.format(report=harvest_report))
        )
      else:
        current_conversation.append(
            (
                current_leader_id,
                (
                    f"I, {current_leader_id.name}, will lead"
                    " the group this cycle. Fellow citizens,"
                    " let me give you the monthly fishing"
                    f" report:\n{harvest_report}"
                ),
            ),
        )
      if mayoral_agenda and leader_persona:
        current_conversation.append(
            (
                current_leader_id,
                (
                    "I'd also like to share my"
                    " policy agenda to help"
                    " guide our collective"
                    f" action: {mayoral_agenda}"
                ),
            ),
        )

    max_conversation_steps = self.cfg.max_conversation_steps

    self.measurement_results = {"elicitation": {}, "perceived_leadership": {}}
    if getattr(self.cfg, "elicitation", False):
      for participant in target_personas:
        self.measurement_results["elicitation"][participant.identity.name] = measurement_prompts.measure(
            self.model, participant, target_personas, current_location,
            current_time, current_context, harvest_report, "elicitation",
        )

    if leader_persona:
      current_persona = leader_persona
    else:
      if getattr(self.cfg, "seeded_opener", False):
        if intervention_seed is None or intervention_cycle is None:
          raise ValueError("Seeded openers require an experiment seed and cycle")
        current_persona = target_personas[
            opener_slot(intervention_seed, intervention_cycle, len(target_personas))
        ]
      else:
        current_persona = random.choice(target_personas)

    while True:
      focal_points = [current_context]
      if current_conversation:
        for _, utterance in current_conversation[-4:]:
          focal_points.append(utterance)

        if len(current_conversation) == 4:
          focal_points += current_conversation[0:1]
        elif len(current_conversation) > 5:
          focal_points += current_conversation[0:2]
      if getattr(self.persona.cfg, "paper_definitions", False):
        focal_points = self.other_personas[
            current_persona.identity.name
        ].retrieve.retrieve(focal_points, top_k=10)
      else:
        focal_points = self.other_personas[
            current_persona.identity.name
        ].retrieve.retrieve(focal_points, top_k=5)

      if self.cfg.prompt_utterance == "one_shot":
        prompt = (
            converse_prompts
            .prompt_converse_utterance_in_group
        )
      else:
        raise NotImplementedError(
            "prompt_utterance="
            f"{self.cfg.prompt_utterance}"
        )

      utterance, end_conversation, next_name, h = prompt(
          self.model,
          current_persona,
          target_personas,
          focal_points,
          current_location,
          current_time,
          current_context,
          self.conversation_render(current_conversation),
          debug,
      )
      html_interactions.append(h)

      observed_turn = {}
      if hasattr(self.model, "recorder"):
        observed_turn = getattr(self.model.recorder, "last_utterance", {}).get(current_persona.identity.name, {})
      turn_records.append({
          "speaker_identity": current_persona.identity.name,
          "slot": int(current_persona.agent_id.split("_")[-1]),
          "rendered_tag": render_name(current_persona.identity),
          "text": utterance, "nominee_raw": (observed_turn.get("nominee_raw") or
              getattr(current_persona, "last_nominee_raw", next_name)),
          "nominee_resolved": next_name, "end_conversation": end_conversation,
          "call_ids": observed_turn.get("call_ids", []),
          "nominee_options": [] if end_conversation else [p.identity.name for p in target_personas],
          "nominee_options_rendered": [] if end_conversation else [render_name(p.identity) for p in target_personas],
      })

      current_conversation.append(
          (current_persona.identity, utterance),
      )

      if (
          end_conversation
          or len(current_conversation)
          >= max_conversation_steps
      ):
        break
      else:
        current_persona = self.other_personas[next_name]

    if getattr(self.cfg, "perceived_leadership", False):
      for participant in target_personas:
        self.measurement_results["perceived_leadership"][participant.identity.name] = measurement_prompts.measure(
            self.model, participant, target_personas, current_location,
            current_time, current_context, harvest_report, "perceived_leadership",
            conversation=self.conversation_render(current_conversation),
        )

    summary_conversation, h = (
        converse_prompts
        .prompt_summarize_conversation_in_one_sentence(
            self.model_framework,
            self.conversation_render(current_conversation),
        )
    )
    html_interactions.append(h)

    resource_limit, h = (
        reflect_prompts
        .prompt_find_harvesting_limit_from_conversation(
            self.model_framework,
            self.conversation_render(current_conversation),
        )
    )
    html_interactions.append(h)
    for persona in target_personas:
      p = self.other_personas[persona.identity.name]
      p.store.store_chat(
          summary_conversation,
          self.conversation_render(current_conversation),
          self.persona.current_time,
      )
      p.reflect.reflect_on_convesation(
          self.conversation_render(current_conversation),
      )
      if resource_limit is not None:
        p.store.store_thought(
            (
                "The community agreed on a maximum limit"
                f" of {resource_limit} tons of fish per"
                " person."
            ),
            self.persona.current_time,
            always_include=True,
        )
    if debug:
      print(
          "CONVERSATION TRANSCRIPT:"
          f" {self.conversation_render(current_conversation)}."
      )
    self.last_conversation = {
        "summary": summary_conversation, "agreed_limit": resource_limit,
        "turns": turn_records, "framework_messages": len(current_conversation) - len(turn_records),
        "end_reason": "end_conversation" if end_conversation else "cap",
        "measurements": self.measurement_results,
    }
    return (
        current_conversation,
        summary_conversation,
        resource_limit,
        html_interactions,
    )

  def conversation_render(
      self,
      conversation: list[
          tuple[common.PersonaIdentity, str]
      ],
  ):
    """Render conversation as name-utterance tuples."""
    return [(render_name(p), u) for p, u in conversation]
