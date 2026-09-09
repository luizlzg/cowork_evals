---
name: hello
description: The greeter answers by name.
tags: [greeter]
plugins: ["../../.."]
runs: 3
max_turns: 10
timeout_seconds: 300
env:
  EVAL_FIXTURE: "1"
---

Say hello to Alex.
