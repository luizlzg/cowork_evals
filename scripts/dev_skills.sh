#!/usr/bin/env bash
#
# Copy every shipped skill into this repository's own .claude/skills/.
#
#   (no args)  copy each skill, overwriting what is there
#
# A consumer gets these from `cowork_evals init`, which never overwrites. This
# repository is not a consumer, so it takes them the other way: the shipped copy
# under src/cowork_evals/data/skills/ is the one source, .claude/skills/ is
# generated and git-ignored, and this script regenerates it. A committed second
# copy would be a duplicate with no rule. See docs/library.md.
set -euo pipefail
# shellcheck source=lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

case "${1-}" in
  "") ;;
  -h | --help) usage ;;
  *) die "unknown argument '$1' (expected none)" ;;
esac

SOURCE="$ROOT/src/cowork_evals/data/skills"
TARGET="$ROOT/.claude/skills"
[ -d "$SOURCE" ] || die "$SOURCE is not there"

for skill in "$SOURCE"/*/; do
  name="$(basename "$skill")"
  [ -f "$skill/SKILL.md" ] || die "$name carries no SKILL.md"
  mkdir -p "$TARGET/$name"
  cp "$skill/SKILL.md" "$TARGET/$name/SKILL.md"
  echo "wrote $TARGET/$name/SKILL.md"
done
