#!/usr/bin/env bash
# B11: the user starts full Flash runs from tmux; Codex only monitors them.
set -euo pipefail
STUDY_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$STUDY_ROOT"
exec "$STUDY_ROOT/.venv/bin/python" -m tools.launch "$@"
