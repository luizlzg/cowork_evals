# CoWork runtime

## Summary

A CoWork session runs in a Linux VM that neither you nor this repository controls. Everything
a consumer ships in a skill, command, agent or hook executes inside it, so that code can use
only what the VM already carries. This file records what is on the image, what the host hands
a skill at invocation time, and the rules that follow for the code under test. Every value
below was read from a real session by direct probe: it is what one session held, not a
contract the product offers. Re-capture it when the base image changes.

- **Every session starts a fresh VM.** Nothing installed during a session survives it, and
  every session pays the install cost again.
- **The code under test is bound to Python 3.10 and the image wheel set.** No runtime install,
  no virtualenv, no package that is not already there.
- **The host gives a skill less than a laptop does.** No plugin `bin/` on `PATH`, no working
  directory at the skill, no shell state between `Bash` calls.

What reproduces this inventory in a container is [docker.md](docker.md). What a consumer's own
package pins may not exceed is [environments.md](environments.md).

## Rules for code that runs in a session

These bind every file under the path a consumer passes to `cowork_evals run`: each skill,
command, agent and hook in the plugin. They do not bind `cowork_evals` itself, which runs on a
laptop, and they do not bind a case's `checks/*.py`, which is host code under the eval path
and runs after the run is graded. See [library.md](library.md) and [checks.md](checks.md).

- **Python 3.10 syntax only.** The session interpreter is 3.10.12. Match statements are fine.
  `X | Y` in an annotation needs `from __future__ import annotations`. Anything added in 3.11
  or later is not available at all.
- **Import only what the image carries.** The standard library, and the wheels in
  `src/cowork_evals/data/requirements.txt`. Nothing else resolves.
- **No package install at runtime.** No `pip install`, `uv pip install`, `npm install`,
  `apt-get install`, `conda`, `brew`, or a script that shells out to one, in a skill, a
  command, an agent or a hook.
- **No virtualenvs.** Do not create `.venv`, `node_modules`, a conda environment, or any other
  per-session environment directory.
- **Use what is already there.** Check the inventory below before assuming a package is
  missing: `pandas`, `python-docx`, `pypdf`, LibreOffice, ffmpeg and ImageMagick are present.
- **Bundle instead of installing.** A small pure-Python or pure-JS file shipped inside the
  plugin costs one download at plugin install, not one per session.
- **Reach out, do not install.** When work needs a library the image lacks, prefer an MCP
  server or a remote API over pulling the library into the session.
- **Do not leave files behind.** Write temporary files under the session temp directory, not
  into the user home or the project.
- **Rely only on what the host provides.** See the table below. An invented environment
  variable expands to the empty string, and the command then fails on a path starting with
  `/`.

## What the host provides

| Mechanism                                   | Present in a skill Bash call | Evidence                                                                                 |
| ------------------------------------------- | ---------------------------- | ---------------------------------------------------------------------------------------- |
| Plugin `bin/` on `PATH`                     | no                           | `PATH` is the OS default, `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin` |
| `cwd` set to the skill directory            | no                           | `pwd` is the session root. A bare `python scripts/x.py` fails with ENOENT                |
| Shell state across Bash calls               | no                           | Each call is a fresh shell. No `cwd` and no exported variable survives                   |
| `Base directory for this skill: <abs path>` | yes                          | Injected above the `SKILL.md` body at invocation time, not in the file                   |
| `TMPDIR`                                    | yes                          | `/sessions/<session>/tmp`, honoured by `tempfile.mkdtemp()`. `/tmp` is also writable     |

A skill names a script it ships by a path relative to the skill directory. The model prefixes
the announced base directory. The shell never resolves it.

```sh
python3 scripts/build_pipeline.py --out deck.pptx
```

An agent is not a skill and gets no base directory. An agent that runs a bundled script takes
the path as an argument from its caller.

## Session lifetime

The VM stops on application quit, not per session, and its session data image persists.
Session directories from earlier sessions therefore remain present inside a running VM.
Sessions are separate users and separate directories on a reused VM.

An eval case cannot assume a clean guest filesystem outside its own session directory.

## What is on the image

Base image: Ubuntu 22.04.5 LTS (Jammy), architecture `aarch64` (ARM64).

Exact Python pins: `src/cowork_evals/data/requirements.txt`, the verbatim `pip freeze`.

### Core runtime

| Component    | Version                                                                              |
| ------------ | ------------------------------------------------------------------------------------ |
| OS           | Ubuntu 22.04.5 LTS (jammy)                                                           |
| Architecture | aarch64 (ARM64). On an x86_64 development machine package builds and behaviour differ |
| Python       | 3.10.12 (`/usr/bin/python3`, also `/usr/bin/python3.10`). Every development environment here is built on that exact version. See [environments.md](environments.md) |
| pip          | 25.3                                                                                 |
| uv           | 0.12.3                                                                               |
| Node.js      | v22.23.2                                                                             |
| npm          | 10.9.8                                                                               |
| npm globals  | corepack, npm. No other global npm package                                           |
| Java         | OpenJDK 11.0.31 (Ubuntu build)                                                       |
| Git          | 2.34.1                                                                               |

### Document and office tooling

| Component                       | Version                                                      |
| ------------------------------- | ------------------------------------------------------------ |
| LibreOffice (`soffice`)         | 26.2.5.2                                                     |
| unoserver                       | 3.7, pairs with the LibreOffice UNO API for headless convert |
| pandoc                          | 2.9.2.1                                                      |
| poppler-utils (`pdftoppm` etc.) | 22.02.0                                                      |
| ghostscript (`gs`)              | 9.55.0                                                       |
| qpdf                            | 10.6.3                                                       |
| tesseract-ocr                   | 4.1.1 (leptonica 1.82.0)                                     |

**Not** present: `wkhtmltopdf`, `weasyprint`, `exiftool`, `docker`.

### Image and media tooling

| Component               | Version              |
| ----------------------- | -------------------- |
| ImageMagick (`convert`) | 6.9.11-60 Q16        |
| ffmpeg                  | 4.4.2 (Ubuntu build) |

ImageMagick is 6, not 7. The binary is `convert`, and argument semantics differ between the
two.

### Fonts

394 font faces, 118 families, the standard Ubuntu font stack: DejaVu, Liberation, Carlito,
Caladea, Latin Modern, Bitstream Charter, C059, Century Schoolbook L, Courier, D050000L,
Dingbats, Droid Sans Fallback, FontAwesome, Noto fallbacks, URW base 35 clones, TeX Gyre.
Full list: `fc-list : family | sort -u`.

No proprietary Microsoft-metric font is present. LibreOffice substitutes Liberation, Carlito
and Caladea. This matters to a skill that needs pixel-exact Office rendering.

### Misc CLI utilities

`git`, `curl` 7.81.0, `wget` 1.21.2, `jq` 1.6, `ssh`, standard coreutils and the
build-essential toolchain. There is no `sqlite3` CLI binary on `PATH`; the Python `sqlite3`
module is available.

### Notable pre-installed Python packages

| Area          | Packages                                                                                                                                                                                                                               |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Document/PDF  | `python-docx`, `python-pptx`, `openpyxl`, `xlsxwriter`, `xlrd`, `pypdf`, `pypdfium2`, `pdfplumber`, `pdfminer.six`, `pikepdf`, `pdf2image`, `camelot-py`, `tabula-py`, `img2pdf`, `pdfkit`, `reportlab`, `markitdown`, `odfpy`, `pyoo` |
| Data/analysis | `pandas`, `numpy`, `matplotlib`, `seaborn`, `opencv-python`, `opencv-python-headless`, `Pillow`, `sympy`                                                                                                                               |
| Web/parsing   | `requests`, `beautifulsoup4`, `lxml`, `markdown`, `markdownify`, `mistune`, `marko`, `Jinja2`                                                                                                                                          |
| OCR/ML        | `pytesseract`, `onnxruntime`, `magika`                                                                                                                                                                                                 |
| Other         | `Wand` (ImageMagick binding), `graphviz`, `psutil`, `python-dotenv`                                                                                                                                                                    |
