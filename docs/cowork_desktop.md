# CoWork desktop internals

How the desktop application starts a session, where it writes, and what a script needs to
drive it. These are the measured internals. What the driver does with them is
[cowork_driver.md](cowork_driver.md).

Captured 2026-09-02 on a macOS development machine by direct probe. Application internals
are not a public interface. Expect any release to change them, and re-probe the coupling
list at the end of this page after an update.

## Measured facts

| Fact              | Value                                                                |
| ----------------- | -------------------------------------------------------------------- |
| Application       | `Claude.app`, Electron, bundle id `com.anthropic.claudefordesktop`   |
| Version probed    | 1.40609.1                                                            |
| Profiles          | `~/Library/Application Support/<profile>`                            |
| Session isolation | Apple Virtualization VM with gvisor networking, local to the machine |
| Host to guest RPC | vsock, `CID=2 port=51234`. Not SSH                                   |
| Guest OS          | Ubuntu 22.04.5 LTS, kernel 6.8.0-136-generic, aarch64                |
| Claude Code in VM | SDK payload at `claude-code-vm/<version>/claude`                     |

A build may install more than one profile directory. Which one is active is read from `lsof`
on the running process. Set the profile name for any tooling through an environment
variable; do not hardcode it.

Chrome DevTools Protocol was not pursued. The application ships Electron fuses that disable
`RunAsNode` and `EnableNodeCliInspectArguments`.

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

The same gate applies to CGEvent and to pressing the send button through the Accessibility
API. No supported method avoids it.

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

Audit record shape:

```json
{"type":"user","uuid":"...","session_id":"...","client_platform":"desktop_app",
 "timestamp":"...","message":{"role":"user","content":"..."},
 "_audit_timestamp":"...","_audit_hmac":"..."}
{"type":"command_lifecycle","command_uuid":"...","state":"queued","session_id":"..."}
{"type":"command_lifecycle","command_uuid":"...","state":"started","session_id":"..."}
```

`queued` and `started` were observed. The terminal state was not observed and must be
established before a driver can key completion on it.

The `user` record is what makes a run identifiable: its `message.content` is the submitted
prompt verbatim. A driver compares it and refuses any session that does not match.

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
the 14336 cap, the sessions root path, the three level session directory depth, the
`audit.jsonl` filename, the `user` and `command_lifecycle` record types, the `state` values,
the transcript path under `.claude/projects/session`, the `subagents/*.jsonl` layout, the
`tool_use` `id` and `tool_result` `tool_use_id` fields, and the `outputs/` directory.
