"""The CoWork backend: which case this backend can run, and what running one produces.

The layer above the driver. It reads the case tree `cases.py` produced, submits each
case's prompt through `CoWork`, grades the session document, and writes the same
`aggregate-result.json` v1 document every other backend writes.

The skip rule is [docs/running_evals.md](../../docs/running_evals.md): a key the case wrote
out is honoured when this backend's behaviour already satisfies it, and skipped otherwise.
A key the case left to its default is not a request and is not a skip, which is why this
reads `Case.frontmatter_keys` and `Case.case_yaml_keys` and never a merged value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .cases import Case

# The eval directory the harness defaults to, and this repository never configures another.
# docs/eval_format.md.
EVAL_DIR = "evals"

# The MCP stand-in directory. Its three layers, suite, group and case, are
# docs/claude_code/plugin_eval_reference.md.
MOCKS_DIR = "mocks"

# The grader target and focus value that names those stand-ins.
MOCK_CALLS = "mock_calls"

# Case keys this backend cannot honour, each with why. The session decides its own model,
# its own tools and its own system prompt, and no turn cap reaches it.
# docs/approaches.md.
UNHONOURED_CASE_KEYS = {
    "max_turns": "no turn cap reaches a CoWork session",
    "model": "the session decides its model",
    "allowed_tools": "the session decides its tools",
    "append_system_prompt": "the session decides its system prompt",
    "env": "nothing sets an environment variable in the VM",
}

# The `case.yaml` keys, which are all of one shape and share one reason.
CONTEXT_PREFIX = "context."
CONTEXT_REASON = "nothing stages files into the VM"


@dataclass(frozen=True, slots=True)
class Skips:
    """Why a case submits nothing, and why a grader is not scored.

    The two are never one list. A `case` reason submits nothing and leaves `arms.with`
    empty. A `graders` entry runs the case and drops that grader from the score, so a case
    does not fail for a grader that was never asked.
    """

    case: tuple[str, ...] = ()
    graders: dict[str, str] = field(default_factory=dict)

    @property
    def skipped(self) -> bool:
        return bool(self.case)

    @property
    def reason(self) -> str:
        """Every case reason as one line, for the result document's `skipReason`."""
        return "; ".join(self.case)


def skips(case: Case, plugin_root: Path | str) -> Skips:
    """What this backend cannot honour in one case. It reads files and submits nothing.

    `plugin_root` is where the `evals/` tree starts, which is what makes a suite-wide
    `evals/mocks/` reach a case several directories below it.
    """
    reasons = [
        f"{key}: {why}" for key, why in UNHONOURED_CASE_KEYS.items() if key in case.frontmatter_keys
    ]
    reasons += [
        f"{key}: {CONTEXT_REASON}" for key in case.case_yaml_keys if key.startswith(CONTEXT_PREFIX)
    ]
    reasons += [
        f"{directory / MOCKS_DIR}: stand-ins are the harness's, and the MCP servers here are real"
        for directory in _mock_layers(case.directory, Path(plugin_root))
    ]
    return Skips(case=tuple(reasons), graders=_grader_skips(case))


def _grader_skips(case: Case) -> dict[str, str]:
    """The one grader skip that is decided before a run.

    The other one, an `llm` grader whose focus turns out to be an image, is read from the
    file's bytes and so exists only after the run. `judge.py` decides that one.
    """
    skipped = {}
    for grader in case.graders:
        for key in ("target", "focus"):
            if grader.config.get(key) == MOCK_CALLS:
                skipped[grader.name] = f"{key}: {MOCK_CALLS}, and no stand-in serves a CoWork run"
                break
    return skipped


def _mock_layers(case_dir: Path, plugin_root: Path) -> list[Path]:
    """Every directory from `evals/` down to the case that carries a `mocks/`.

    `evals/mocks/` skips every case in the plugin and a case's own `mocks/` skips that case
    alone, which are the layers the harness adds up.
    """
    case_dir = case_dir.resolve()
    evals = (plugin_root.resolve() / EVAL_DIR).resolve()
    above = [case_dir, *case_dir.parents]
    chain = above[: above.index(evals) + 1] if evals in above else [case_dir]
    return [directory for directory in reversed(chain) if (directory / MOCKS_DIR).is_dir()]
