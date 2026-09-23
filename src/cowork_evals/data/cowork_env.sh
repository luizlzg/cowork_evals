#!/bin/sh
# The shell prefix every Bash call and every hook command in a Docker run goes through. It runs
# the command under the CoWork session environment and nothing else. A name survives only when
# it is listed in the keep file, one per line, and has a value, or when a case set it through
# its `env` key. docs/docker.md, "The session environment".
#
# The keep file is mounted read-only per run. Claude Code passes the command as one string,
# and /bin/bash runs it, as the CoWork Bash tool does.

keep_file=/etc/cowork_evals/keep_env.txt
command=$1
set -f
set --
while IFS= read -r name; do
  case $name in
    '' | [!A-Za-z_]* | *[!A-Za-z0-9_]*) continue ;;
  esac
  # Five names whose CoWork value is a function of another variable.
  case $name in
    USER | LOGNAME) value=${HOME:+${HOME##*/}} ;;
    CLAUDE_TMPDIR | CLAUDE_CODE_TMPDIR) value=${TMPDIR-} ;;
    SHELL) value=/bin/sh ;;
    *) eval "value=\${$name-}" ;;
  esac
  if [ -n "$value" ]; then
    set -- "$@" "$name=$value"
  fi
done <"$keep_file"
# A case's own `env` keys, which the harness restricts to EVAL_[A-Z0-9_]*. Such a case carries
# no-cowork, so keeping them claims nothing about a session.
for name in $(env | sed -n 's/^\(EVAL_[A-Z0-9_]*\)=.*/\1/p'); do
  eval "value=\${$name-}"
  set -- "$@" "$name=$value"
done
exec env -i "$@" /bin/bash -c "$command"
