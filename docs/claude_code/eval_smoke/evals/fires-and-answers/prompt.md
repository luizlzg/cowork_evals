---
# Not this repository's case format. This is the harness's own shape: no `tags`, and
# `plugins: ["../.."]` with the case directly under `evals/`. `max_turns` and `allowed_tools`
# below are honoured by the container backend and not by CoWork, so a case carrying them is
# skipped there and a skip fails the gate. Do not copy this file. The format is
# docs/eval_format.md, and what this plugin is for is its own README.md.
name: fires-and-answers
description: The skill activates on a natural ask and emits the token.
runs: 1
max_turns: 5
timeout_seconds: 120
allowed_tools: [Skill]
plugins: ["../.."]
---

Run the smoke check and give me the smoke token.
