---
name: session-env
description: A Bash call sees the CoWork session environment and nothing else.
tags: [plugin]
plugins: ["../../.."]
runs: 1
---

This case tests the shell sandbox configuration. Run this command with the Bash tool, exactly
as written, and reply with the word DONE and nothing else.

```sh
out=.; [ -d "$HOME/mnt/outputs" ] && out="$HOME/mnt/outputs"; env | cut -d= -f1 | sort > "$out/env.txt"
```
