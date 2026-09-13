# Checks

## What was measured

Two facts about a tool-using `claude -p`, on CLI 2.1.270, `haiku`, over a text file, an 8 by
8 PNG and a one-page PDF written by the measurement.

| Fact                                                                                   | Holds |
| -------------------------------------------------------------------------------------- | ----- |
| `--allowedTools Read,Glob,Grep` alone lets a non-interactive judge read a file in its working directory | yes |
| `--add-dir` alone lets it read a file outside that directory                           | yes   |
| A tool-using judge answers with the bare word, so `judge.read_reply` reads it exactly   | yes   |
| It reads the file rather than agreeing: the same claim inverted came back `FAIL`        | yes   |

So the check judge's argument list carries no permission mode and no turn cap, and the reply
is read by the same `read_reply` every other vote goes through.
