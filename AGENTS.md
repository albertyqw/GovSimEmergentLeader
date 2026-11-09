# AGENTS.md

This repository runs the experiments for "Conditions for Emergent Leadership in GovSim."

## Source of truth
`METHODS.md` is the binding specification. Part B governs implementation, and section B15 covers running under Codex. Before starting any phase, re-read the Part B sections that phase touches. Never rely on remembered details of exact texts (B5), random-number keys (B6), or storage rules (B7).

## Non-negotiable rules
- Implement only what `METHODS.md` describes. If anything is ambiguous or the code doesn't match it, stop and ask.
- Stop at every gate marked **STOP** in `METHODS.md` B11. End the session there with your report. Never continue past a gate, even if approvals are off or everything looks fine.
- Never run formatters, linters, or auto-fixers on existing files.
- Never fix original bugs or quirks; record them in `QUIRKS.md`.
- Never write `OPENROUTER_API_KEY` to any file, log, or commit.
- Never call the global `random` or `np.random` in new code (B6).
- Do not upgrade or add dependencies imported by simulation code.

## Running experiments
- You run stub tests and one-cycle Flash-Lite smoke tests yourself.
- Never start a full Gemini 2.5 Flash run from a Codex command. Write `launch.sh`, give me the exact command, and I will start it in tmux. Then monitor by reading logs.

## Network
`gh`, `pip`, and OpenRouter need network access, which the sandbox blocks by default. If a command fails because the network is blocked, say so. Never work around the sandbox, and never switch to full-access mode.
