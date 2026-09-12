---
# The case writes `max_turns`, which no CoWork session honours, so it carries `no-cowork`
# and is declared there. The container backend honours the key and runs this grader.
type: regex
target: last_message
pattern: 'PONG'
match: contains
---
