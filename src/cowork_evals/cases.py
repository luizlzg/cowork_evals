"""The case reader. One case tree in, one list of `Case` out.

It parses what [docs/eval_format.md](../../docs/eval_format.md) defines, the way
`claude plugin eval` parses it, so every backend sees the same case set. It is
backend-neutral: nothing here knows which backend will run a case, and nothing here
decides a skip.

It refuses nothing a case merely got wrong. A `prompt.md` with no frontmatter is read, with
its missing keys left for the case validator, which cannot report what the reader declined
to build. `CaseError` is for a tree that cannot be read at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

import frontmatter
import yaml

# What makes a directory a case, a case's optional second file, and its grader directory.
# docs/eval_format.md.
PROMPT_FILE = "prompt.md"
CASE_YAML = "case.yaml"
GRADERS_DIR = "graders"

# What makes a directory a plugin root. docs/eval_format.md.
PLUGIN_MANIFEST = Path(".claude-plugin") / "plugin.json"

# The eval directory the harness defaults to, and this repository never configures another.
# It is here rather than under a backend because every reader of a case tree needs it.
# docs/eval_format.md.
EVAL_DIR = "evals"

# Directories the harness never descends into during discovery. Matching it is what keeps
# the case set identical on every backend. docs/claude_code/plugin_eval_reference.md.
PRUNED = frozenset({"node_modules", ".git", ".claude", "results"})

# A grader's default weight. docs/eval_format.md.
DEFAULT_WEIGHT = 1

# `source` in the v1 result document. A case is discovered by its `prompt.md`, so
# `case_yaml` cannot occur here. docs/claude_code/plugin_eval_reference.md.
PROSE = "prose"
MIXED = "mixed"

# The one key of `case.yaml` whose children are kept separately, so a reader asks for
# `context.add_dirs` and not for the mapping above it.
CONTEXT = "context"


class CaseError(Exception):
    """A case tree that cannot be read: unparsable YAML, or no plugin root."""


@dataclass(frozen=True, slots=True)
class Grader:
    """One file under `graders/`. Its frontmatter, split into what every grader has."""

    name: str
    type: str
    weight: int | float
    config: dict[str, Any]
    markdown: str
    path: Path


@dataclass(frozen=True, slots=True)
class Case:
    """One directory holding a `prompt.md`.

    `directory` is that directory and `path` is the `prompt.md` inside it. `name` defaults
    to the directory name, which is the harness's rule for a case with no `case.yaml`.

    `frontmatter_keys` and `case_yaml_keys` are what each file wrote out, mapped to the
    value as authored. They are the keys, not the merged defaults: a backend honours a key
    the case asked for and ignores one it left alone, and the case validator reports a key
    the format does not allow. A `case.yaml` `context:` mapping is flattened, so its keys
    arrive as `context.add_dirs` and the mapping above them is not a key of its own.
    """

    name: str
    directory: Path
    prompt: str
    graders: tuple[Grader, ...]
    tags: tuple[str, ...]
    source: str
    frontmatter_keys: dict[str, Any] = field(default_factory=dict)
    case_yaml_keys: dict[str, Any] = field(default_factory=dict)
    path: Path = Path(PROMPT_FILE)


def plugin_root(target: Path | str) -> Path:
    """The nearest directory at or above `target` holding `.claude-plugin/plugin.json`."""
    resolved = Path(target).resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / PLUGIN_MANIFEST).is_file():
            return candidate
    raise CaseError(f"no {PLUGIN_MANIFEST} at or above {resolved}")


def discover(
    root: Path | str, *, tags: tuple[str, ...] = (), case_glob: str | None = None
) -> list[Case]:
    """Every case at or under `root`, sorted by path.

    Discovery is recursive and a case directory is a leaf: a directory holding a
    `prompt.md` is read as a case and never searched through, and anything else is
    searched through rather than run.

    `tags` keeps a case carrying any of them, and `case_glob` globs the case `name`, which
    is what the harness globs. They are `--tag` and `--case` in docs/cli.md.
    """
    base = Path(root)
    cases = [read(directory) for directory in sorted(_case_directories(base))]
    if tags:
        wanted = set(tags)
        cases = [case for case in cases if wanted.intersection(case.tags)]
    if case_glob is not None:
        cases = [case for case in cases if fnmatchcase(case.name, case_glob)]
    return cases


def read(directory: Path | str) -> Case:
    """One case directory, already known to hold a `prompt.md`."""
    case_dir = Path(directory)
    prompt_path = case_dir / PROMPT_FILE
    post = _post(prompt_path)
    written = dict(post.metadata)

    yaml_path = case_dir / CASE_YAML
    document = _case_yaml(yaml_path) if yaml_path.is_file() else None
    yaml_written = {} if document is None else _flatten(document)

    # The merge order is the harness's: `case.yaml` is the base and the `prompt.md`
    # frontmatter overrides it. docs/claude_code/plugin_eval_reference.md.
    merged = {**yaml_written, **written}
    name = merged.get("name")
    tags = merged.get("tags")

    return Case(
        name=name if isinstance(name, str) and name else case_dir.name,
        directory=case_dir,
        prompt=post.content,
        graders=_graders(case_dir / GRADERS_DIR),
        tags=tuple(str(tag) for tag in tags) if isinstance(tags, list) else (),
        source=PROSE if document is None else MIXED,
        frontmatter_keys=written,
        case_yaml_keys=yaml_written,
        path=prompt_path,
    )


def _case_directories(base: Path) -> list[Path]:
    """Recurse, stopping at a case and at the directories the harness prunes."""
    if not base.is_dir():
        return []
    if (base / PROMPT_FILE).is_file():
        return [base]
    found: list[Path] = []
    for child in sorted(base.iterdir()):
        if child.is_dir() and child.name not in PRUNED:
            found += _case_directories(child)
    return found


def _graders(directory: Path) -> tuple[Grader, ...]:
    """Every grader file, alphabetically, as the harness orders them.

    A file whose metadata is empty is a note, not a grader, and is ignored exactly as the
    harness ignores it. That is the first authoring trap in docs/eval_format.md: a file
    with no `---` delimiters leaves the case running with fewer graders than it appears to
    have.
    """
    if not directory.is_dir():
        return ()
    graders = []
    for path in sorted(directory.glob("*.md")):
        post = _post(path)
        if not post.metadata:
            continue
        metadata = dict(post.metadata)
        name = metadata.pop("name", None)
        kind = metadata.pop("type", None)
        weight = metadata.pop("weight", DEFAULT_WEIGHT)
        graders.append(
            Grader(
                name=name if isinstance(name, str) and name else path.stem,
                type=kind if isinstance(kind, str) else "",
                weight=weight if isinstance(weight, int | float) else DEFAULT_WEIGHT,
                config=metadata,
                markdown=post.content,
                path=path,
            )
        )
    return tuple(graders)


def _post(path: Path) -> frontmatter.Post:
    """One Markdown file, split into frontmatter and body.

    An absent `---` block yields empty metadata, which is what makes a `prompt.md` with no
    frontmatter readable and a grader file with none ignorable.
    """
    try:
        return frontmatter.load(str(path))
    except OSError as error:
        raise CaseError(f"{path}: unreadable: {error}") from error
    except yaml.YAMLError as error:
        raise CaseError(f"{path}: unparsable frontmatter: {error}") from error


def _case_yaml(path: Path) -> dict[str, Any]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CaseError(f"{path}: unreadable: {error}") from error
    except yaml.YAMLError as error:
        raise CaseError(f"{path}: unparsable YAML: {error}") from error
    if document is None:
        return {}
    if not isinstance(document, dict):
        raise CaseError(f"{path}: expected a mapping at the top level")
    return document


def _flatten(document: dict[str, Any]) -> dict[str, Any]:
    """Top level keys as authored, with `context:` replaced by its dotted children."""
    flat: dict[str, Any] = {}
    for key, value in document.items():
        if key == CONTEXT and isinstance(value, dict):
            for inner, held in value.items():
                flat[f"{CONTEXT}.{inner}"] = held
            continue
        flat[key] = value
    return flat
