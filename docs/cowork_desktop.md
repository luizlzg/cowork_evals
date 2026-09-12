# CoWork desktop internals

## Summary

How the desktop application starts a session, where it writes, and what a script needs to
drive it. These are the measured internals. What the driver does with them is
[cowork_driver.md](cowork_driver.md).

- **Input is a deep link.** The application registers the `claude` URL scheme and takes a
  prompt in `q`. No query parameter submits.
- **Submission is a synthetic Return**, which needs the macOS Accessibility grant. No
  supported method avoids that permission prompt.
- **Output is on the host filesystem.** Nothing reads the screen: a session writes a
  transcript, a signed audit log and an `outputs/` directory under the profile.
- **Never write anywhere under the profile.** Those directories are application managed.
- **Five authorizations are needed**, none discoverable from the code. A second machine needs
  all of them.
- **Nothing here is a public interface.** The coupling list at the end is the checklist to
  re-probe after an application update.

Captured 2026-09-02 on a macOS development machine by direct probe, re-probed 2026-09-08 for
section 3, which reads session directories already on disk, and extended 2026-09-12 with the
process name, what the keyboard does to a submission, and section 5, which is what five real
sessions did when asked. Expect any release to change these.

## Measured facts

| Fact              | Value                                                                |
| ----------------- | -------------------------------------------------------------------- |
| Application       | `Claude.app`, Electron, bundle id `com.anthropic.claudefordesktop`   |
| Process name      | `Claude`, as `System Events` reports it. Snapshot 2026-09-12          |
| Version probed    | 1.40609.1                                                            |
| Profiles          | `~/Library/Application Support/<profile>`                            |
| Session isolation | Apple Virtualization VM with gvisor networking, local to the machine |
| Host to guest RPC | vsock, `CID=2 port=51234`. Not SSH                                   |
| Guest OS          | Ubuntu 22.04.5 LTS, kernel 6.8.0-136-generic, aarch64                |
| Claude Code in VM | SDK payload at `claude-code-vm/<version>/claude`                     |
| New session boot  | About 45 seconds from deep link to the first tool call in the guest  |
| Driven run        | 8.2 seconds end to end, deep link to collected result. Snapshot 2026-09-08 |
| Guest bash tool   | `mcp__workspace__bash`, an MCP tool, not Claude Code's own `Bash`     |
| Guest fetch tool  | `mcp__workspace__web_fetch`. Snapshot 2026-09-12                     |
| Host write tool   | `Write`, which names a host path and lands in `outputs/`. Snapshot 2026-09-12 |

A build may install more than one profile directory. Which one is active is read from `lsof`
on the running process. Name the active profile in `cowork_evals.yaml`; do not hardcode it.
See [cowork_driver.md](cowork_driver.md).

Chrome DevTools Protocol was not pursued. The application ships Electron fuses that disable
`RunAsNode` and `EnableNodeCliInspectArguments`.

The driven run is one measurement of one prompt: a marker prompt, no tool call, and a warm
VM bundle already on disk. It is the floor, not the typical case. The 45 second boot above
is what a cold VM costs, and a prompt that calls a tool pays it.

## 1. Input, by deep link

The application registers the `claude` URL scheme, and its router accepts a prompt in `q`.

| Route                                                 | Status                                                       |
| ----------------------------------------------------- | ------------------------------------------------------------ |
| `claude://claude.ai/new?q=<text>&surface=cowork`      | Verified. Produced a session that ran a tool in the VM       |
| `claude://claude.ai/new?q=<text>`                     | Verified. Produced a session with no `surface` parameter     |
| `claude://cowork/new?q=<text>`                        | Answered, and wrote no session directory. Not usable         |
| `claude://claude.ai/new?...&file=&folder=`            | Router reads both. Not fired. Needed only for fixtures       |
| `claude://customize/plugins/new?marketplace=&plugin=` | Router accepts it. Not fired. Needed only for plugin staging |

Both `surface=cowork` and the bare form produced a session, so the parameter is not load
bearing on the evidence available.

The three route statuses above come from three probes, one prompt each. Two shapes were
covered, and they are the two a grader reads:

| Probe                                                              | Established                                                       |
| ------------------------------------------------------------------ | ----------------------------------------------------------------- |
| A prompt asking for one exact token back                           | A session directory, and the reply captured verbatim              |
| A prompt asking for `uname -a`, `ls /sessions` and `/etc/os-release` | A tool call into the guest, and its output captured on the host  |
| The same token prompt through `claude://cowork/new`                | The application answers and writes no session directory           |

Not covered by those probes, and therefore not stated anywhere here: repeated runs,
concurrent sessions, parallel tool calls, and attachments. The terminal lifecycle state was
not covered either, and is established below by the 2026-09-08 re-probe.

The application caps `q` at 14336 characters and truncates silently above it. A driver must
refuse a longer prompt rather than truncate, or a case is graded on an altered prompt.

The prefill does not submit. No query parameter submits.

## 2. Submit, by synthetic Return

```sh
osascript -e 'tell application "Claude" to activate' \
          -e 'delay 0.8' \
          -e 'tell application "System Events" to key code 36'
```

Without the macOS Accessibility grant this fails with:

```
System Events got an error: osascript is not allowed to send keystrokes. (1002)
```

The same permission check applies to CGEvent and to pressing the send button through the
Accessibility
API. No supported method avoids it.

### What the keyboard does to a submission

Snapshot 2026-09-12, on the same machine and application version.

Two submissions of one prompt, `Reply with the single word: ready`, were recorded in
`audit.jsonl` as `Reply with the single word: readyennumera` and
`Reply with the single word: read`. The developer was typing in another application while
the driver held the keyboard. The first submission carried their characters into the prompt.
The second lost the prompt's own last character.

The deep link had already brought the application forward, so the characters a human typed
next went into its composer, beside the prefilled prompt. Attribution refused both, so
nothing was submitted to a grader and nothing was scored on an altered prompt.

A separate probe the same day, one prompt, fired the deep link into a composer that already
held the text `RESIDUE`. The recorded prompt was the submitted prompt exactly, carrying none
of it. `claude://claude.ai/new` starts a new conversation, so what a driver has to protect
against is a human typing after the deep link, not text left in a field before it.

What the driver does about all of this is [cowork_driver.md](cowork_driver.md).

## 3. Output, on the host filesystem

Nothing reads the screen. The session writes under
`~/Library/Application Support/<profile>/local-agent-mode-sessions/<account8>/<profile8>/<session8>/`.

| Path inside the session directory                   | Contents                                     |
| --------------------------------------------------- | -------------------------------------------- |
| `.claude/projects/session/<uuid>.jsonl`             | Full Claude Code transcript                  |
| `.claude/projects/session/<uuid>/subagents/*.jsonl` | Subagent sidechains                          |
| `audit.jsonl`                                       | Signed event log, one record per event       |
| `.audit-key`                                        | Key material for the audit HMAC              |
| `outputs/`                                          | Artifacts, mounted read write into the guest |
| `uploads/`                                          | Attached inputs, mounted read only           |

Transcript record keys observed: `type`, `message`, `toolUseResult`, `attributionMcpServer`,
`attributionMcpTool`, `permissionMode`, `promptId`, `sessionId`, `timestamp`, `version`,
`isSidechain`, `cwd`, `gitBranch`. Content blocks carry `id` on a `tool_use` and
`tool_use_id` on a `tool_result`, which is how a reader pairs them.

Transcript record types observed, snapshot 2026-09-08 over seven session directories:
`user`, `assistant`, `attachment`, `queue-operation`, `atis-latch`, `last-prompt` and
`mode`. Only `user` and `assistant` carry a `message`. A reader takes turns from those two
and ignores the rest, because the set is open. `mode` was absent from the five directories
probed earlier the same day and present in the seven probed later, which is the set being
open in practice.

`message.content` is a string or a list of blocks. Observed block types: `text`, `thinking`,
`tool_use` and `tool_result`. A `thinking` block is not turn text.

Subagent records carry `isSidechain: true`. Each `subagents/agent-<id>.jsonl` has a sibling
`agent-<id>.meta.json` holding `agentType`, `description`, `spawnDepth` and `toolUseId`.

Audit record shape:

```json
{"type":"user","uuid":"...","session_id":"...","client_platform":"desktop_app",
 "timestamp":"...","message":{"role":"user","content":"..."},
 "_audit_timestamp":"...","_audit_hmac":"..."}
{"type":"command_lifecycle","command_uuid":"...","state":"queued","session_id":"..."}
{"type":"command_lifecycle","command_uuid":"...","state":"started","session_id":"..."}
{"type":"result","subtype":"success","is_error":false,"num_turns":13,
 "total_cost_usd":0.64,"result":"...","stop_reason":"end_turn","session_id":"..."}
{"type":"command_lifecycle","command_uuid":"...","state":"completed","session_id":"..."}
```

`completed` is the terminal `command_lifecycle` state. Snapshot 2026-09-08, five session
directories, nine commands, every one of them reaching `completed`. No other terminal state
was seen, so a failed or cancelled command has an unknown state name and quiescence remains
the fallback signal.

The terminal record carries `type`, `state`, `command_uuid`, `session_id`, `uuid`,
`timestamp`, `_audit_timestamp` and `_audit_hmac`, and nothing else. It carries no assistant
text, no turn count and no cost.

The `result` record immediately before it carries all three: `result` is the final assistant
text, `num_turns` the turn count, `total_cost_usd` the cost. It also carries `subtype`,
`is_error`, `stop_reason`, `terminal_reason`, `usage`, `modelUsage`, `duration_ms` and
`permission_denials`.

Every lifecycle record carries `command_uuid`. One session directory holds more than one
command: three of the five held three each, one prompt per command, and the states of two
commands interleave when a prompt is queued before the previous one completes. A driver that
submits one prompt into a fresh session sees one command, and keys completion on the first
`completed` it sees.

The `user` record is what makes a run identifiable: its `message.content` is the submitted
prompt verbatim. A driver compares it and refuses any session that does not match.

### Discovery by structure

Snapshot 2026-09-08, two profiles. A session directory is exactly three levels below the
sessions root and holds an `audit.jsonl`. No `audit.jsonl` exists at any other depth. The
`audit.jsonl` test is what separates a session from its siblings at the same depth:
`cowork_plugins`, `memory`, `usage-ledger`, `rpm` and the `skills-plugin` tree all sit three
levels down and hold none.

`.claude/projects/session/` was present in every session directory probed, holding one
top level `<uuid>.jsonl` per run. The `<uuid>/subagents/` directory exists only when a
subagent ran. A reader still tolerates the directory's absence, because a session directory
is created before its first transcript is written.

## 4. Guest mounts

The session daemon bind mounts host directories over virtiofs.

| Host path, relative to the profile                     | Guest path                              | Mode |
| ------------------------------------------------------ | --------------------------------------- | ---- |
| `<session>/outputs`                                    | `/sessions/<name>/mnt/outputs`          | rw   |
| `<session>/uploads`                                    | `/sessions/<name>/mnt/uploads`          | ro   |
| `<session>/.claude/projects`                           | `/sessions/<name>/mnt/.claude/projects` | ro   |
| `local-agent-mode-sessions/skills-plugin/<...>/skills` | `/sessions/<name>/mnt/.claude/skills`   | ro   |
| `<...>/memory/memory`                                  | `/sessions/<name>/mnt/.auto-memory`     | ro   |

Never write anywhere under the profile. These directories are application managed and
writing into them may corrupt a profile. To stage a plugin, use the install deep link, on a
throwaway profile first.

## 5. What a session does when asked

Snapshot, captured 2026-09-12 on application version 1.52386.0. Four prompts through
`cowork_evals ask --cowork`, one submission each, on a profile with nothing granted to the
session beyond what a fresh session has. Every prompt asked the session to do the thing. What
a session says about its own configuration is not evidence, so every row below is read from
the session document's `tool_calls` and `outputs`, and from the host filesystem afterwards.

| Asked for                       | Tool called                  | Result                                   |
| ------------------------------- | ---------------------------- | ---------------------------------------- |
| Write a file                    | `Write`                      | Wrote `outputs/<name>.txt`, 1 assistant turn |
| Run a shell command             | `mcp__workspace__bash`       | `Linux 6.8.0-136-generic`, `Python 3.10.12`, and the session name as the guest user |
| Fetch a URL                     | `mcp__workspace__web_fetch`  | `HTTP 200 OK` and the page body, from `https://example.com` |
| Produce a `.pptx`               | `mcp__workspace__bash`, six times | Read `.claude/skills/pptx/SKILL.md` with `cat`, `npm install`ed a library and wrote a 44 KB `outputs/<name>.pptx` |

Every one of the four ran to `completed` with no interaction. Nothing was granted, nothing
was asked, and the driver sends the deep link and one Return and nothing else, so a permission
prompt would have stalled the run until the run timeout. A session writes files, shells out and
reaches the network on its own.

Four consequences a case format and a grader act on.

| Measured                                                | Consequence                                                    |
| ------------------------------------------------------- | --------------------------------------------------------------- |
| No tool was granted and four were used                  | A tool grant is not a key a CoWork case can honour. It is the Docker backend's, and only there |
| `Write` named a host path, `mcp__workspace__bash` named a guest path | Both landed in the same `outputs/` directory. `Write` runs on the host and the bash tool runs in the guest, over the mount section 4 records |
| A skill was read with `cat` over its mounted directory  | There is no `Skill` tool in the transcript. A grader that looks for one finds nothing |
| `rm` of a file the session had created under `outputs/` was refused, `Operation not permitted` | A file a session wrote into `outputs/` stays there, so a collector reads a complete set |

The guest reported Python 3.10.12, which is the interpreter the code under test runs on. See
[runtime.md](runtime.md).

### What a session has, and what a named absent skill does

Snapshot, captured 2026-09-12 on application version 1.52386.0, one further
`cowork_evals ask --cowork` submission on the same profile. The prompt asked for a listing of
the guest's skills directory, and then named a skill that is not installed.

| Asked for                                      | What happened                                                |
| ---------------------------------------------- | -------------------------------------------------------------- |
| `ls -1` of the guest's skills directory        | `mcp__workspace__bash`, and eleven names: `consolidate-memory`, `docx`, `explain-usage`, `frontend-design`, `pdf`, `pdf-reading`, `pptx`, `schedule`, `setup-claude`, `setup-cowork`, `xlsx` |
| Use the `invoice-parser` skill to write a file | Nothing was written, and `outputs/` stayed empty. The session said the skill does not exist, asked whether to write the file without it, and ended the turn |

The eleven names are the host tree at
`local-agent-mode-sessions/skills-plugin/<account>/<profile>/skills/`, name for name, which
is the mount in section 4. A session's skill set is a property of the profile. That tree is
application managed and mounted read only, and nothing here writes under a profile, so a
skill is made absent by using a profile it was never installed into and by nothing else.

The second row is why a prompt does not name the skill it is testing. The session refused the
name and produced no file, so a prompt that names the skill measures the name rather than the
behaviour.

The session's own prose named ten of the eleven and added two the directory does not hold.
The eleven above are what `bash` printed. What a session says about its own configuration is
not evidence.

## Authorizations

None of these is discoverable from the code. A second machine needs all of them.

| Authorization                                | Granted by               | Why                                          | Scope       |
| -------------------------------------------- | ------------------------ | -------------------------------------------- | ----------- |
| macOS Accessibility for the driving terminal | User, in System Settings | Synthetic Return, else osascript error 1002  | Per machine |
| `Bash(open "claude://*")` permission rule    | User, in Claude Code     | Fire the deep link                           | Per machine |
| `Bash(osascript:*)` permission rule          | User, in Claude Code     | Press Return                                 | Per machine |
| CoWork signed in                             | User                     | Organization SSO with MFA is not automatable | Per machine |
| `disableDeepLinkRegistration` not set        | Tenant admin             | Disables `claude://` handling, fails closed  | Tenant wide |

The Accessibility grant follows the application that owns the terminal process, not the
script. Determine it by walking the parent process chain.

Screen Recording is not required. `screencapture` fails without it, but a driver reads the
filesystem and never the screen.

An assistant cannot write the permission rules. Self granting is blocked by the permission
classifier through every tool. The user creates `.claude/settings.local.json`, which is
git-ignored:

```json
{
  "permissions": {
    "allow": [
      "Bash(open \"claude://*\")",
      "Bash(osascript:*)"
    ]
  }
}
```

## Coupling list

Re-probe every item after an application update. This is a checklist, not an investigation.

The `claude://claude.ai/new` route, the `q`, `surface`, `file` and `folder` parameter names,
the 14336 cap, the `Claude` process name `System Events` reports, the sessions root path, the three level session directory depth, the
`audit.jsonl` filename, the `user` and `command_lifecycle` record types, the `state` values,
the transcript path under `.claude/projects/session`, the `subagents/*.jsonl` layout, the
`tool_use` `id` and `tool_result` `tool_use_id` fields, the `outputs/` directory, and the
`Write`, `mcp__workspace__bash` and `mcp__workspace__web_fetch` tool names.

Every field a reader of a collected session acts on, by file:

| File            | Fields                                                                        |
| --------------- | ------------------------------------------------------------------------------- |
| `audit.jsonl`   | `type`, `state`, `timestamp`, `message.content`                                |
| The transcript  | `type`, `attributionMcpServer`, `attributionMcpTool`, `timestamp`, `message.role`, `message.content`, and per block `type`, `text`, `id`, `name`, `input`, `tool_use_id`, `content` |
| The directory   | `.claude/projects/session/<uuid>.jsonl`, `<uuid>/subagents/*.jsonl`, `outputs/` |
