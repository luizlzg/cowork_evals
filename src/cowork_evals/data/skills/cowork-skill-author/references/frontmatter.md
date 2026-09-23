# Frontmatter

## `name` (required)

1 to 64 chars, lowercase alphanumeric plus hyphens, no leading, trailing or consecutive hyphens.
Must match the parent directory name.

Regex: `^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$`

## `description` (required)

This single line decides whether the skill fires. It is the only matching surface.

Structure:

1. Capability sentence in third person, "Extracts text from PDFs", not "Use this skill to...".
2. `TRIGGER when:`, concrete user phrases, file extensions, task patterns.
3. `NOT for ...` where the boundary with a neighbouring skill is fuzzy.

**Must be a literal single line.** Multi-line YAML breaks the parser. This is a hard rule.

**Length is a budget, not a cliff.** Every character is paid in every session by every user, so
keep it tight, around 250 chars is the target. It is _not_ a limit: descriptions well past 1000
chars render in full in the loaded skill list, and shipped skills at 349 and 542 chars match fine.
Past the target, ask what the extra characters buy. Do not treat it as a failure.

**Front-load the triggers anyway.** `TRIGGER when:` early is good practice regardless of length. A
capability sentence that buries the trigger list is a real matching problem, because the part of
the description that matches user phrasing is the part that has to be found. Keep the capability
sentence tight.

**Declare the negative case.** At org scale a greedy description hijacks unrelated conversations.
Where two skills sit next to each other (`pptx` and `pptx-author`, `pdf` and `pdf-redact`),
state the boundary in the description and record an eval case that must _not_ fire.

Always measure: `echo -n '<description>' | wc -c`

### Good

```
Analyzes datasets in CSV, TSV, and Excel formats. Generates summary statistics, filters rows, and produces charts. TRIGGER when: user asks to explore, summarize, or visualize tabular data.
```

### Bad

```
Use this skill to analyze data
# first person, no TRIGGER when
```

```
A very powerful and flexible tool that can do many things including reading, writing, converting, transforming, analyzing, summarizing, filtering, grouping, aggregating, pivoting, and producing charts from ... TRIGGER when: user mentions spreadsheet.
# the capability sentence buries the triggers, and says nothing concrete
```

```
Helps with documents
# vague, no TRIGGER, no specifics
```

### Anti-patterns

- **Missing TRIGGER**, capability alone is not enough. The agent needs matching patterns.
- **Vague triggers**, "when needed" or "when relevant" do not help matching. Use concrete phrases.
- **First or second person**, "I can help you" or "Use this skill to" break system prompt context.
- **Repeating the skill name**, wastes chars. Use the space for trigger keywords instead.

## `version` (optional)

Free-form string at the **top level**, not inside `metadata`. Bumping it is informational, nothing
compares versions on reload.

Do not confuse it with the plugin's `version`, which lives in `plugin.json`. Those two are
unrelated fields.

## `allowed-tools`, do not use it

Skills declare `name` and `description` and nothing else. The key takes paths relative to the
authoring tree, like `Bash(skills/<name>/scripts/<name>.sh:*)`, which do not resolve once the
skill is installed under `<plugin>/skills/<name>/`. The paths silently point at nothing. Skills
ported from a source repo carry it. Drop it.

A skill that calls another skill's CLI invokes the wrapper **by path**. It does not need, and must
not declare, `allowed-tools` to do so.

## `metadata` (optional)

Arbitrary string-to-string key-value map. Use it for free-form keys like `author` or `date`. Keep
`version` at the top level, not in here.

## Other optional fields

- `license`, license name or reference to a bundled file.
- `compatibility`, 500 chars or fewer. Declare runtime and system requirements here: external
  tools or system binaries the skill shells out to, not pip dependencies, with install hints.
  Example: `Requires LibreOffice and Poppler (pdftoppm) for visual-preview and export-pdf.`

Optional keys are tolerated but not enforced: nothing reads them at run time, and
`claude plugin validate --strict` never opens `SKILL.md` at all, so it will not reject an
unrecognised skill key either. Set them for the reader's benefit, do not rely on them.
