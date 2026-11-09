"""Read only the deliberately provided tmux key into process environment.

The value is never printed, put in command arguments, or written to a file.
Network use remains subject to the normal command approval boundary.
"""

import json
import os
import runpy
import subprocess
import sys


def main():
    if not os.environ.get("OPENROUTER_API_KEY"):
        result = subprocess.run(["tmux", "show-environment", "-g", "OPENROUTER_API_KEY"],
                                capture_output=True, text=True)
        if "Operation not permitted" in result.stderr:
            raise PermissionError("The sandbox blocked the tmux socket; approve the keyed command")
        name, separator, token = result.stdout.rstrip("\n").partition("=")
        if result.returncode or name != "OPENROUTER_API_KEY" or not separator or not token:
            raise SystemExit("The tmux key is not ready; no credential value was printed")
        os.environ[name] = token
    if sys.argv[1:] == ["--preflight"]:
        from simulation.openrouter_handling import authenticated_get
        key = authenticated_get("key")["data"]
        credit = authenticated_get("credits")["data"]
        print(json.dumps({"balance": credit["total_credits"] - credit["total_usage"],
                          "limit": key.get("limit"), "limit_remaining": key.get("limit_remaining"),
                          "usage": key.get("usage")}))
        return
    sys.argv[0] = "run_study.py"
    runpy.run_module("run_study", run_name="__main__")


if __name__ == "__main__":
    main()
