"""B9 deterministic transport stub using the original Pathfinder parser."""

import copy
import re

from pathfinder import ModelAPI
from simulation.utils.models import ModelWandbWrapper


class StubModel(ModelAPI):
    def __init__(self, seed=0, turns=3, catch=2, nomination_style="tagged"):
        super().__init__("google/gemini-2.5-flash", seed)
        self.requests = []
        self.turns = turns
        self.catch = catch
        self.nomination_style = nomination_style

    def request_api(self, chat, temperature, top_p, max_tokens):
        prompt = "\n".join(message["content"] for message in chat)
        if "Before this month's discussion begins" in prompt:
            plan = "" if "PLAN: <number>" not in prompt else f"PLAN: {self.catch}\n"
            response = plan + f"LIMIT: {self.catch}\nREASON: Preserve the commons."
        elif "whose suggestions, if anyone's" in prompt:
            response = "ANSWER: Julia"
        elif "how many tons of fish would you catch this month?" in prompt:
            response = f"Preserve the commons. Answer: {self.catch} tons."
        elif "Task: What would you say next in the group chat?" in prompt:
            names_text = re.findall(r"Scenario: (.*?) are engaged in a group chat\.", prompt)[-1]
            names = [part.strip() for part in names_text.replace(", and ", ", ").split(", ")]
            speaker = re.search(r"You are ([A-Za-z]+)", prompt).group(1)
            bare_names = [name.split(" [", 1)[0] for name in names]
            next_name = names[(bare_names.index(speaker) + 1) % len(names)]
            if self.nomination_style != "tagged":
                next_name = next_name.split(" [", 1)[0]
                if self.nomination_style == "lowercase":
                    next_name = next_name.lower()
                elif self.nomination_style == "partial":
                    next_name = next_name[:3]
            transcript = prompt.rsplit("\nConversation so far:\n", 1)[1].split("\n\nTask:", 1)[0]
            previous_turns = len(re.findall(r"^-(?:" + "|".join(bare_names) + r")(?: \[.*?\])?:", transcript, re.M))
            ending = "yes" if previous_turns + 1 >= self.turns else "no"
            response = (
                f"Response: Let us agree on {self.catch} tons each.\n"
                f"Conversation conclusion by me: {ending}\nNext speaker: {next_name}"
            )
        elif "Summarize the conversation above in one sentence." in prompt:
            response = f"The community agreed to {self.catch} tons per person."
        elif "Determine whether there was an explicit agreement" in prompt:
            response = f"The limit is explicit. Answer: {self.catch}"
        elif "Rating (1 to 10):" in prompt:
            response = "5"
        elif "remember for your planning" in prompt:
            response = f"I should follow the {self.catch} ton agreement."
        elif "found interesting from your own perspective" in prompt:
            response = f"Julia supported {self.catch} tons per person."
        elif "What high-level insights can you infere" in prompt:
            response = f"Preserve the {self.catch} ton agreement (because of 1)."
        else:
            raise AssertionError("Unrecognized stub call: " + prompt[-300:])
        self.requests.append({
            "request": {
                "model": self.model_name, "messages": copy.deepcopy(chat),
                "temperature": temperature, "top_p": top_p,
                "seed": self.seed, "max_tokens": max_tokens,
            },
            "response": response,
        })
        return response


class StubLogger:
    def __init__(self):
        self.operations = []
        self.games = []

    def get_agent_chain(self, agent, phase):
        return (agent, phase)

    def start_chain(self, name):
        return name

    def end_chain(self, *args, **kwargs):
        pass

    def log_trace_llm(self, **record):
        self.operations.append(record)

    def log_game(self, record, **kwargs):
        self.games.append(record)


def make_wrapper(seed=0, turns=3, catch=2):
    transport = StubModel(seed=seed, turns=turns, catch=catch)
    logger = StubLogger()
    wrapper = ModelWandbWrapper(
        transport, render=False, wanbd_logger=logger,
        temperature=0.0, top_p=1.0, seed=seed, is_api=True,
    )
    return wrapper, logger, transport
