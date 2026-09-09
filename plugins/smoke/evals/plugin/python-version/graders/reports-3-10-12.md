---
# The version is a literal here, and only here. This file is read inside the sandbox, so it
# imports nothing. Its sibling is EXPECTED_VERSIONS["python3"] in
# src/cowork_evals/docker/parity.py, and the two change in one commit.
type: regex
target: last_message
pattern: 'Python 3\.10\.12'
match: contains
---
