# CLI Skill Setup

A skill with executable code carries a `scripts/` directory: a shell wrapper, and a Python package
the wrapper runs. Nothing is installed when either runs, so there is no project file, no lockfile
and no environment to build. Every import is already on the image or is bundled in the plugin as
source. See `runtime.md`.

## Shell wrapper

Create `scripts/<skillname>.sh`, one wrapper per tool package:

```bash
#!/bin/bash -eu
set -o pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
exec env PYTHONPATH="$SCRIPT_DIR" python3 -m <skillname>_tool "$@"
```

Then: `chmod +x scripts/<skillname>.sh`

The wrapper has four properties, and each one is required:

- **`SCRIPT_DIR` comes from `$0`.** `$0` is always defined. `${CLAUDE_PLUGIN_ROOT}` and
  `${CLAUDE_SKILL_DIR}` are not, so a wrapper that reads one with no `:-` fallback fails the
  moment it is invoked from a test, from another skill, or from a shell.
- **`-m` is what makes the package's own imports resolve.** `python3 <skillname>_tool/cli.py` puts
  the package directory on `sys.path` rather than its parent, so the package cannot import itself,
  and it runs nothing unless that module carries an `if __name__ == "__main__"` guard.
- **`PYTHONPATH` gets only the skill's own `scripts/` directory.** Skills in one plugin share an
  interpreter, not a namespace.
- **`python3` is executed directly.** No project manager, no `uv run`, no `pip install`, no
  `npm install`. Nothing installs at run time, and a wrapper that tries makes the skill fail in
  every session.

Drop `-m` and `PYTHONPATH` only for a tool that is a single file importing nothing of its own.

## Python package

Create `scripts/<skillname>_tool/`:

**`__init__.py`**, empty or a one-line docstring.

**`__main__.py`**:

```python
from <skillname>_tool.<skillname> import main

main()
```

**`<skillname>.py`** (main module), use argparse for subcommand dispatch:

```python
import argparse
import sys


def cmd_example(args):
    pass


def main():
    parser = argparse.ArgumentParser(prog="<skillname>")
    sub = parser.add_subparsers(dest="command")
    p = sub.add_parser("example", help="Do something")
    p.add_argument("input", help="Input file")
    p.set_defaults(func=cmd_example)
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)
```

For many subcommands, split into `cmd_*.py` modules with shared code in `common.py`.

**Intra-package imports are absolute**, `from <skillname>_tool import common`, never
`from .common import ...`. Both resolve under `-m`, and the absolute form is the one that still
resolves when a module is run or imported directly.

Python packages cannot contain hyphens: `pptx-author` becomes `pptx_author_tool/`.

## What a script must not carry

- No `# /// script` inline metadata block, and no `uv run --script` shebang. The shebang is
  `#!/usr/bin/env python3`.
- No `pyproject.toml` and no `uv.lock`, at any level of the plugin. A project file gives the skill
  an environment that nothing builds and the wrapper never uses.
- No install call, direct or shelled out: `pip install`, `uv pip install`, `npm install`,
  `apt-get install`, `conda`, `brew`.
- No proxy handling, no `ssl_verify` toggle, no `.env` loading. No credential reaches a session
  shell, and no proxy or CA variable is set there. A service that needs a credential is reached
  through an MCP server. See `runtime.md`.

**When a script runs a sibling Python script, use `sys.executable`**, never a bare `python` or
`python3` string. That is the interpreter already running, which is the one the wrapper chose.

## After writing the wrapper

```bash
chmod +x scripts/<skillname>.sh
scripts/<skillname>.sh --help        # must exit 0
```

An import error here is the common failure, and it does not show up until the wrapper is actually
run. It usually means an import the image does not carry. Check it against `runtime.md` and
`pip_freeze.txt`.

`--help` on a laptop proves the wrapper and the imports resolve on the laptop's Python. It does
not prove they resolve in a session. `cowork_evals test --docker <plugin>/tests` runs the
plugin's tests on the session's Python and wheel set.
