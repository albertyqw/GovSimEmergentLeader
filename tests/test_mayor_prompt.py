"""B3/B9: compare the actual harvest prompt prefix to pinned source."""

import ast
import datetime
import subprocess
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from simulation.persona.cognition import utils


ROOT = Path(__file__).resolve().parents[1]
PROMPTS = "simulation/persona/cognition/act_prompts.py"
SENTINEL = "No specific guidance."


class CapturedPrompt:
    def __init__(self):
        self.text = ""

    def __iadd__(self, text):
        self.text += text
        return self

    def _current_prompt(self):
        return self.text


def render_prefix(source, agenda, flag):
    """Execute source through its user block, before model generation."""
    tree = ast.parse(source)
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "prompt_action_choose_amount_of_fish_to_catch"
    )
    boundary = next(
        i for i, node in enumerate(function.body)
        if isinstance(node, ast.With)
        and isinstance(node.items[0].context_expr, ast.Call)
        and node.items[0].context_expr.func.id == "assistant"
    )
    function.body = function.body[:boundary] + [
        ast.Return(ast.Call(
            ast.Attribute(ast.Name("lm", ast.Load()), "_current_prompt", ast.Load()),
            [], [],
        ))
    ]
    module = ast.Module(body=[
        ast.ImportFrom("__future__", [ast.alias("annotations")], 0), function,
    ], type_ignores=[])
    namespace = {
        "user": nullcontext,
        "cognition_utils": utils,
        "leaders_lib": SimpleNamespace(get_leader_persona_prompts=lambda agent: ("", "", "")),
        "persona_lib": SimpleNamespace(DEFAULT_AGENDA=SENTINEL),
    }
    exec(compile(ast.fix_missing_locations(module), PROMPTS, "exec"), namespace)
    identity = SimpleNamespace(
        name="Julia", goals="", env=SimpleNamespace(regen_min_range=1.0, regen_max_range=3.0)
    )
    flags = {} if flag is None else {"drop_mayor_line": flag}
    agent = SimpleNamespace(identity=identity, cfg=SimpleNamespace(act=SimpleNamespace(**flags)))
    model = SimpleNamespace(start_chain_async=lambda *args: (CapturedPrompt(), None))
    return namespace[function.name](
        model, agent, [], "lake", datetime.datetime(2024, 1, 1), "", range(101),
        leader_agenda=agenda,
    )


class MayorPromptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = subprocess.check_output(
            ["git", "show", "8cf0aba:" + PROMPTS], cwd=ROOT, text=True
        )
        cls.working = (ROOT / PROMPTS).read_text()

    def test_disabled_and_absent_flag_match_original_byte_for_byte(self):
        for flag in (None, False):
            for agenda in (None, "", SENTINEL, "Catch five tons."):
                with self.subTest(flag=flag, agenda=agenda):
                    self.assertEqual(
                        render_prefix(self.working, agenda, flag),
                        render_prefix(self.original, agenda, flag),
                    )

    def test_enabled_omits_only_mayor_line_for_absent_agenda(self):
        for agenda in (None, "", SENTINEL):
            with self.subTest(agenda=agenda):
                original = render_prefix(self.original, agenda, False)
                line = (
                    "\nThe current policy following the mayor's agenda is"
                    f" the following: {agenda}\n"
                )
                self.assertEqual(original.count(line), 1)
                self.assertEqual(
                    render_prefix(self.working, agenda, True), original.replace(line, "", 1)
                )

    def test_enabled_preserves_real_agenda(self):
        agenda = "Catch five tons."
        self.assertEqual(
            render_prefix(self.working, agenda, True),
            render_prefix(self.original, agenda, False),
        )


if __name__ == "__main__":
    unittest.main()
