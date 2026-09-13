# The panel

## Summary

What state the evals under a path are in, from records left by earlier runs. `cowork_evals
panel` reads the case tree and the history together and prints one row per case: the latest
outcome on each backend, how old it is, what it scored, how long it took, how often it flakes,
whether the case files have changed since, and where that result's artefacts are.

- **The history is the record, and the run directory is not.** A run directory holds what one
  invocation produced and is deleted on the retention `prune` is given. A record outlives it.
- **`run` writes one record per case, once, after the verdict.** No backend changes, and
  nothing writes a record during a run.
- **The panel spends nothing and reaches no backend.** It reads files.
- **`outcome` is the word [running_evals.md](running_evals.md) defines.** The verdict decides
  it, and the panel records what was decided rather than deciding again.
- **A case with no record reads `never run`.** Coverage is the first question the panel
  answers, so it is a value in the column and never an empty cell.

The verb, its options and its exit codes are [cli.md](cli.md). The setting is `panel.root`, in
[library.md](library.md)'s ladder.

## The tree

```
logs/evals/history/<plugin>/<skill>/<case>.jsonl
```

One file per case, one JSON object per line, appended once per invocation that ran the case.
`panel.root` names the root, and it defaults to `logs/evals/history` under the working
directory. `--out DIR` does not move it: that option relocates what one invocation produced,
and a record is read after that invocation's directory is gone.

The path is the plugin, then the case's directory under `evals/`, every component through the
same slug a run directory's name uses. Two shapes are not the ordinary
`<plugin>/<skill>/<case>.jsonl`, and both stay unique:

| The case sits                  | Its file                                |
| ------------------------------ | --------------------------------------- |
| under one skill directory      | `<plugin>/<skill>/<case>.jsonl`         |
| directly under `evals/`        | `<plugin>/<case>.jsonl`                 |
| deeper than one skill directory | `<plugin>/<skill>/<...>/<case>.jsonl`  |

The second cannot collide with the first: one is a file and the other a directory of the same
stem. The third carries every component, so two cases sharing a directory name under two
skills stay apart.

The case is the panel's row, so the path is the lookup key and reading one row is one file
open. Two invocations contend only when both ran the same case. Retiring one case is `rm` of
one file.

Two plugins whose manifests carry the same `name` share one history directory. A run
directory suffixes the second `-2`; a history path cannot, because it has to be stable across
invocations.

`logs.prune` deletes only children of the log root whose names match the run stamp, so the
history directory under that root survives it. `prune --history` is what deletes a record.

## The record

One JSON object per line. An optional field is absent, never null. The contract is
additive-only: a reader ignores a field it does not know, and a line of another
`schemaVersion` is reported and not read.

| Field                           | Is                                                          |
| ------------------------------- | ------------------------------------------------------------- |
| `schemaVersion`                 | `1`                                                         |
| `invocation`                    | the run directory's name                                    |
| `startedAt`                     | the document's own stamp                                    |
| `claudeVersion`                 | the `claude` that produced it                               |
| `backend`                       | `docker` or `cowork`                                        |
| `image`                         | the image tag, on the container backend                     |
| `coworkEvals`                   | the distribution version that recorded it                   |
| `plugin`, `pluginVersion`       | the manifest name and version, not the run directory's name |
| `skill`                         | the first component under `evals/`, absent for a case outside a skill |
| `case`, `dir`                   | the case's name, and its directory relative to the plugin root |
| `caseDigest`                    | `sha256` over the files that define the case, on this host, absent when that directory defines none |
| `outcome`                       | `pass`, `fail` or `declared`                                |
| `score`, `passRate`             | the case's aggregates                                       |
| `delta`                         | the case's delta, on a two-arm run                          |
| `runs`                          | how many times the case ran                                 |
| `durationSeconds`, `costUsd`    | summed over those runs                                      |
| `failedGraders`                 | every scored grader that did not pass, each named once      |
| `error`                         | the first run error                                         |
| `deniedTools`, `unofferedTools` | the union over the runs, when the trace was kept            |
| `tracePath`                     | the first failing run's trace, else the first run's         |

A record is self-contained. It repeats the plugin, the skill and the case its own path already
says, so one line is readable alone and a row for a case that has left the tree can be built
from the record itself.

`invocation` and `tracePath` are the two join keys back into the run tree. The panel reports
the artefacts as gone when the directory is not there, which is what a pruned run directory
leaves behind.

### The digest

`caseDigest` covers `prompt.md`, `case.yaml` when the case has one, each `graders/*.md` in
path order and then each `checks/*.py`: every file that decides what the case asks and how it
is graded. Nothing else in the case directory counts, so a note beside the graders moves no
digest.

A check file counts because editing an assertion would otherwise leave this column green over
a result that asserted something else. See [checks.md](checks.md).

It hashes bytes, so a whitespace edit moves it, and it hashes each file's name before its
content, so a renamed grader moves it too. It is computed when the record is written and
recomputed when the row is rendered, and a row whose two differ reads `stale`: the result is
green over files that are not the files there now.

Both readings are of the tree on this host. The container backend's result document names
`/work/plugin` as `suite.root`, which is where the plugin was mounted inside the container
and is nothing here, so `run` hands the record the plugin root it was pointed at rather than
the one the document carries.

A case directory holding no file that defines a case has no digest, and the record then
carries none. `sha256` over no bytes is a valid-looking digest that matches no real one, so
recording it would make every later row read `stale` over files nobody edited.

The plugin's git revision is deliberately not recorded. It needs a subprocess against a tool
that may be absent, in a tree that may not be a repository, and it moves on every unrelated
commit. The digest answers the same question without any of that.

### Appending

`run` appends after the verdict, once, from the result documents the invocation wrote. A
`--dry-run` and every refusal return before the sweep, so neither appends.

Each file is opened for append under an exclusive `flock`, and every line it takes is written
in one call, so a concurrent reader sees whole lines.

An append that fails prints `panel: <reason>` on stderr and leaves the exit code alone.
Recording a result is not deciding one, and an unwritable history root does not turn a passing
run red.

A line that does not parse is reported and skipped. A record is one line, so a truncated last
line loses one measurement; refusing the file for it would lose every other measurement of
that case.

## The render

One row per case under the path. The definitions come from the case tree at render time, never
from a record: a second copy of what a case is would drift from the case.

| Column        | Is                                                                   |
| ------------- | ---------------------------------------------------------------------- |
| `plugin`      | the manifest name                                                    |
| `skill`       | the skill directory, empty for a case outside one                    |
| `case`        | the case name                                                        |
| `description` | the case's own, empty when it writes none, cut to 40 characters in the text table alone |
| `docker`      | that backend's latest outcome, and its age in days                   |
| `cowork`      | the same for CoWork                                                  |
| `score`       | the latest record's score                                            |
| `duration`    | how long that run took                                               |
| `flake`       | how often that backend's records of this case passed, and how many they are |
| `stale`       | whether the case files have changed since                            |
| `artefacts`   | where that result's artefacts are, relative to the working directory when they are under it, marked `gone` when the directory is not there |

The five columns after the backends come from the row's latest record, whichever backend
produced it: the panel answers what is known about the case now, and that is its most recent
measurement. `flake` is over that same backend's records, and a declared record is out of it.

A backend with no record for the case reads `never run`. The CoWork column of a case carrying
`no-cowork` reads `declared` whether or not it has ever been submitted: the tag is in the tree
and is the reason no record will ever appear there. The tag is
[eval_format.md](eval_format.md).

Each backend's newest record is the last one for that backend in the file. Appending is the
only write, so file order is the order the records were made in.

### The three renders

`table` is the text table, and it is the only one that cuts a description: a terminal is the
one render with a width to fit. `--markdown FILE` writes the same columns as a Markdown table
with every description whole. `--json FILE` writes the same rows as a JSON snapshot, one entry
each, nothing formatted: a number is a number, and an absent one is absent. Both may be given
at once, and both carry the rows the table carries.

### A case that has left the tree

`--removed` adds a row for every history file of a selected plugin whose case is no longer in
the tree. Those rows carry `removed` in place of a description and are built from the record
itself.

It is the tree that decides, not the path argument: a case that is still there and was not
selected is not a case that was removed.

## Pruning

`prune --history --older-than DAYS` drops every record older than `DAYS`, deletes a file left
with no record, and then deletes every directory that leaves empty. It reads `panel.root` and
ignores `--out`.

The age is the record's own stamp, never the file's modification time: reading a file moves
that time, and a case nobody has looked at is not younger than one somebody has. A record with
no stamp, and a line that did not parse, are both kept: neither can be dated, and dropping
what cannot be dated is a deletion on the age of nothing.

`DAYS` is read here as `logs.prune` reads it, at one exact moment `DAYS` before now, because
it is one flag over both trees. A floor on whole days would keep a record for a day longer
than the run directory it names.

There is no automatic retention. A keep-N or keep-days rule applied on its own would delete
the newest record of a case that runs twice a year, which is the row the panel most needs.
Deleting a record is the operator's act.

Deleting the history of a case that is no longer in the tree is not `prune`'s either. `prune`
takes no path and cannot know what the tree holds now. Retiring one case is `rm` of one file,
and `panel --removed` is how those files are found.
