---
schema_version: "1.1"
name: greets-alex
description: Every key the format allows, written out.
tags: [greeter, smoke, no-cowork]
plugins: ["../../.."]
runs: 2
max_turns: 12
timeout_seconds: 600
model: sonnet
allowed_tools: [Read, Skill]
append_system_prompt: Answer in one sentence.
env:
  EVAL_FIXTURE: one
expected_outcome: The reply names Alex.
---

Say hello to Alex.
