# SKILL.md Body

The body follows the YAML frontmatter. Budget: 500 lines or fewer, around 5000 tokens. Move heavy
content to `references/`.

Start with an H1 matching the skill's display name, for example `# Data Analysis`.

## Structure

1. **Introduction**, one paragraph: what the skill does, when to use it.
2. **Instructions**, numbered steps for the primary workflow. Multiple modes get separate
   subsections.
3. **CLI reference** (if applicable), commands grouped by category, each with syntax and key
   flags.
4. **Rules**, bullet list of constraints the agent must follow.

## Progressive disclosure

Skills load in three tiers:

1. **Metadata** (around 100 tokens): `name` and `description` only, loaded at startup for every
   skill. This is the only matching surface.
2. **SKILL.md body** (under 5000 tokens): loaded once the skill activates.
3. **Resources** (on demand): `references/`, `scripts/`, `assets/`, `resources/` files loaded only
   when the agent reads them.

Design the body as the always-loaded middle tier. Anything long, rarely needed, or only useful
during a specific sub-task belongs in a reference file the body links to, not inline.

Keep references one level deep: `SKILL.md` to `references/topic.md`. Do not chain
(`references/a.md` to `references/b.md` to `references/c.md`). Flatten instead.

## Principles

- Agent-facing only, no implementation details or architecture. Those belong in the project's own
  documentation, not in the skill.
- Document outputs, where files are written and in what format.
- Call out non-obvious behaviour, for example "batch correction is OFF by default".
- All file paths relative from the skill root: `references/topic.md`, `scripts/tool.sh`.
- Every referenced file must exist on disk.
- **Never link outside the skill directory.** The skill ships alone. A path that walks up out of it
  resolves in the authoring tree and nowhere else. If the body needs a rule that lives in a project
  document, inline the rule.
- **An asset the skill's output references must ship with the skill.** A generated HTML page that
  points at a CDN, or a generated script with a bare JS module specifier, resolves to nothing in a
  session. Bundle the asset and reference it by relative path.
