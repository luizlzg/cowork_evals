# The CoWork runtime

A CoWork session is an Ubuntu 22.04.5 aarch64 VM. Each session is a new user with a new home
directory, and cannot count on anything an earlier session installed. Code in a skill uses
what the image carries, or what the plugin ships as source, and nothing else.

The Docker image `cowork_evals setup --docker` builds reproduces this image. The tables below
are a selection. Whether an import resolves or a command exists is settled on that image:
`cowork_evals test --docker <plugin>/tests` runs the plugin's tests on it, and
`cowork_evals run --docker <plugin>/evals` runs its evals there with the session's environment
variables.

## Python

Python 3.10.12, at `/usr/bin/python3`, `/usr/bin/python3.10` and `/usr/bin/python`. The
installed packages and their exact versions are `pip_freeze.txt` beside this file. An import
resolves when it is the standard library, a package in `pip_freeze.txt`, or a module the
plugin ships.

Code written for 3.11 or later often parses on 3.10 and fails at the first call.

| Not in 3.10                             | Use                                           |
| --------------------------------------- | --------------------------------------------- |
| `datetime.UTC`                          | `datetime.timezone.utc`                       |
| `enum.StrEnum`                          | `class X(str, enum.Enum)`                     |
| `tomllib`                               | JSON or YAML: no TOML parser is installed     |
| `typing.Self`, `Never`, `LiteralString` | a `TypeVar`, `NoReturn`, `str`                |
| `typing.Required`, `NotRequired`        | two `TypedDict` classes, `total=False` on one |
| `typing.override`                       | drop it                                       |
| `ExceptionGroup`, `except*`             | a list of exceptions                          |
| `asyncio.TaskGroup`, `asyncio.timeout`  | `asyncio.gather`, `asyncio.wait_for`          |
| `contextlib.chdir`                      | `os.chdir` in `try`/`finally`                 |
| `itertools.batched`                     | a loop                                        |
| PEP 695 `type X = ...`, `def f[T]()`    | `TypeAlias`, `TypeVar`                        |

`match` is available. `X | Y` in an annotation needs `from __future__ import annotations`.

Import names differ from the names in `pip_freeze.txt`:

| Package                                   | Import              |
| ----------------------------------------- | ------------------- |
| `beautifulsoup4`                          | `bs4`               |
| `PyYAML`                                  | `yaml`              |
| `Pillow`                                  | `PIL`               |
| `python-docx`, `python-pptx`              | `docx`, `pptx`      |
| `opencv-python`, `opencv-python-headless` | `cv2`               |
| `python-dateutil`, `python-dotenv`        | `dateutil`, `dotenv` |
| `pdfminer.six`                            | `pdfminer`          |
| `camelot-py`, `tabula-py`                 | `camelot`, `tabula` |
| `odfpy`, `Wand`, `fonttools`              | `odf`, `wand`, `fontTools` |

`uno` and `unohelper`, LibreOffice's bindings, import from the system interpreter.

Not installed, and often carried by a ported skill: `httpx`, `typer`, `rich`, `structlog`,
`pydantic`, `pymupdf`, `anthropic`, `openai`, `google-genai`, `tenacity`, `mammoth`,
`pypandoc`, `weasyprint`, `pytest`.

## Commands

| Area         | Commands                                                                     |
| ------------ | ---------------------------------------------------------------------------- |
| Office       | `soffice` (LibreOffice 26.2.5.2), `unoserver`, `unoconvert`                  |
| Conversion   | `pandoc` 2.9.2.1                                                             |
| PDF          | `pdftoppm`, `pdftotext`, `pdfinfo` (poppler 22.02.0), `gs` 9.55.0, `qpdf`    |
| TeX          | `pdflatex`, `xelatex`, `latexmk` (TeX Live 2021)                             |
| OCR          | `tesseract` 4.1.1, English                                                   |
| Image, media | `convert`, `identify` (ImageMagick 6), `ffmpeg`, `ffprobe` 4.4.2             |
| Diagrams     | `dot` (Graphviz)                                                             |
| Display      | `xvfb-run`                                                                   |
| Runtimes     | `python3`, `node` 22.23.2, `npm`, `npx`, `java` (OpenJDK 11), `uv`           |
| Everyday     | `git`, `curl`, `wget`, `jq`, `rg`, `zip`, `unzip`, `rsync`, `xmllint`, `ssh` |
| Build        | `gcc`, `make`                                                                |

ImageMagick is 6: the command is `convert`, and there is no `magick`.

Not installed: `wkhtmltopdf`, `weasyprint`, `exiftool`, `docker`, the `sqlite3` CLI, `magick`,
`mutool`, `inkscape`, `rsvg-convert`, any browser, `gh`, `yq`, `aws`, `gcloud`, `az`.

No Microsoft font is installed. LibreOffice substitutes Liberation, Carlito and Caladea.

## Node

`NODE_PATH` is `/usr/local/lib/node_modules_global/lib/node_modules`, so `require()` finds these
packages from any directory. An ES module `import` does not read `NODE_PATH` and fails: load
them with `require()`, or with `createRequire(import.meta.url)` from `node:module`.

| Package                         | Version | Command |
| ------------------------------- | ------- | ------- |
| `@anthropic-ai/sandbox-runtime` | 0.0.76  | `srt`   |
| `docx`                          | 9.7.1   |         |
| `graphviz`                      | 0.0.9   |         |
| `markdown-toc`                  | 1.2.0   | `markdown-toc` |
| `marked`                        | 18.0.12 | `marked` |
| `pdf-lib`                       | 1.17.1  |         |
| `pdfjs-dist`                    | 6.3.289 |         |
| `pptxgenjs`                     | 4.0.1   |         |
| `sharp`                         | 0.35.4  |         |
| `ts-node`                       | 10.9.2  | `ts-node` |
| `tsx`                           | 4.23.13 | `tsx`   |
| `typescript`                    | 7.0.2   | `tsc`   |

No other npm package is installed. A skill that needs one bundles it as a file.

## Environment

A `Bash` call sees exactly these variables. `<session>` is the session name, which changes
every session and is also the user name.

| Variable             | Value                                                                                                 |
| -------------------- | ----------------------------------------------------------------------------------------------------- |
| `HOME`               | `/sessions/<session>`                                                                                 |
| `PWD`                | `/sessions/<session>`                                                                                 |
| `USER`               | `<session>`                                                                                           |
| `LOGNAME`            | `<session>`                                                                                           |
| `TMPDIR`             | `/sessions/<session>/tmp`                                                                             |
| `CLAUDE_TMPDIR`      | `/sessions/<session>/tmp`                                                                             |
| `CLAUDE_CODE_TMPDIR` | `/sessions/<session>/tmp`                                                                             |
| `TZ`                 | The host machine's IANA zone. The image zone is `Etc/UTC`                                             |
| `LANG`               | `C.UTF-8`                                                                                             |
| `PATH`               | `/usr/local/lib/node_modules_global/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin` |
| `NODE_PATH`          | `/usr/local/lib/node_modules_global/lib/node_modules`                                                 |
| `SHELL`              | `/bin/sh`. A `Bash` call runs bash all the same                                                       |
| `SHLVL`              | `0`                                                                                                   |
| `INVOCATION_ID`      | The systemd unit invocation id                                                                        |
| `JOURNAL_STREAM`     | The systemd journal stream                                                                            |
| `SYSTEMD_EXEC_PID`   | The PID systemd started the unit with                                                                 |

Any other variable is empty: `CLAUDE_PLUGIN_ROOT`, `CLAUDE_SKILL_DIR`, `CLAUDE_PROJECT_DIR`,
`CLAUDE_SESSION_ID`, every `ANTHROPIC_*`, every API key, `HTTP_PROXY`, `SSL_CERT_FILE`,
`PYTHONPATH`, `DISPLAY`. No credential reaches the shell. `"$CLAUDE_PLUGIN_ROOT/scripts/x.sh"`
becomes `/scripts/x.sh` and fails.

When a skill is invoked, the line `Base directory for this skill: <absolute path>` is added
above its `SKILL.md` body. A skill names a file it ships by a path relative to the skill
directory, and the model prefixes the base directory. An agent gets no base directory, and
takes a script's path as an argument from its caller. The working directory of a `Bash` call
is `HOME`, and no `cd` or `export` survives into the next call.

## Rules

- Import the standard library, a package in `pip_freeze.txt`, or a module the plugin ships.
- Run a command the image carries, or one the plugin ships, by a path relative to the skill.
  The plugin's `bin/` is not on `PATH`.
- Read only a variable in the table above. Never hard-code `/sessions/<session>`.
- No install at run time: no `pip install`, `uv pip install`, `npm install`, `apt-get install`,
  `brew`, `conda`, and no `npx` of a package that is not global.
- No `pyproject.toml`, `uv.lock`, `.venv`, `package.json` dependencies or `node_modules` in the
  plugin. Nothing builds them.
- A credential comes from an MCP server, never from the environment or a `.env` file.
- Write temporary files under `$TMPDIR`, and what the user gets under the mounted `outputs`
  folder.
- Output the skill writes references only what the skill ships: no CDN URL, no bare module
  specifier in a generated file.
