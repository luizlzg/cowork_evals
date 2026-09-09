# Staged runtime

A relocatable Python 3.10 interpreter carrying the CoWork wheel set, copied into the plugin
directory under test before a run. The venv backend puts its `bin` first on `PATH`, so a
bare `python3` in a granted `Bash` call resolves to 3.10 with the CoWork wheels.

The measurements in this file are a snapshot. The mirror it is built from is
[environments.md](environments.md). The backend that stages it, and whether that backend is
built, are both in [running_evals.md](running_evals.md). The sandbox rules it satisfies are
the "How the sandbox works" section of
[claude_code/plugin_eval_reference.md](claude_code/plugin_eval_reference.md).

## Why the mirror is not staged directly

Granting `Bash` in any form turns on Claude Code's OS-level sandbox, seatbelt on macOS and
bubblewrap on Linux. Inside it the readable set is the per-run sandbox, the plugin directory
under test, the case's `context.add_dirs` entries, and the `PATH` directories inside those.
The home directory and its siblings are unreadable. This is the one copy of that set.

A virtual environment is a pointer, not an installation. The mirror at `.venv_cowork` holds
no interpreter and no standard library. Measured 2026-09-04:

| Property         | Value                                                              |
| ---------------- | ------------------------------------------------------------------ |
| `bin/python3`    | symlink to `bin/python`, symlink to the uv interpreter store       |
| `pyvenv.cfg home`| `~/.local/share/uv/python/cpython-3.10.16-macos-aarch64-none/bin`  |
| `sys.base_prefix`| `~/.local/share/uv/python/cpython-3.10.16-macos-aarch64-none`      |
| `os.__file__`    | the same store, under `lib/python3.10/`                            |

Copying `.venv_cowork` into the plugin therefore copies `site-packages` and leaves the
interpreter and the whole standard library under the home directory, where the sandbox
cannot read them.

Staging the interpreter itself removes the pointer. uv installs
python-build-standalone, which is relocatable, so the copy runs from its new path.

## Layout

```
<plugin>/.cowork-runtime/python/bin/python3                     on PATH
<plugin>/.cowork-runtime/python/lib/python3.10/                 standard library
<plugin>/.cowork-runtime/python/lib/python3.10/site-packages/   the CoWork wheels
```

Two sources build it:

| Source                                                       | Copied to                            | Size  |
| ------------------------------------------------------------ | ------------------------------------ | ----- |
| `~/.local/share/uv/python/cpython-3.10.<x>-<platform>/`       | `.cowork-runtime/python/`            | 56 MB |
| `.venv_cowork/lib/python3.10/site-packages/`                  | the staged `site-packages/`          | 593 MB |

The wheels go into the interpreter's own `site-packages`, not a separate directory reached
through `PYTHONPATH`. `PYTHONPATH` entries are not scanned for `.pth` files, and four pins
ship one: `coloredlogs`, `lazr.restfulclient`, `lazr.uri` and `zope.interface`. Measured
2026-09-04:

| Marker `.pth` placed in            | Executed at interpreter start |
| ---------------------------------- | ----------------------------- |
| a `PYTHONPATH` directory           | no                            |
| the interpreter's `site-packages`  | yes                           |

The staged runtime therefore needs `PATH` only. It sets no `PYTHONPATH`.

## What is dropped

`_virtualenv.pth` and `_virtualenv.py` are virtualenv shims. They belong to `.venv_cowork`
and not to an interpreter, so the staging step removes both after the copy.

The interpreter arrives with its own `pip` and `setuptools`. The merge leaves them in place.
Their versions are not the image's, and [runtime.md](runtime.md) holds the image's.

## Lifecycle

The backend stages `.cowork-runtime/` before the harness starts and removes it when the run
ends. [library.md](library.md) says why a build product inside the consumer checkout is
allowed here and what the consumer git-ignores.

## Measurements

Snapshot 2026-09-04. macOS 26.6.2 aarch64, uv 0.11.3, interpreter
`cpython-3.10.16-macos-aarch64-none`, CLI 2.1.260. Every test below ran the staged tree from
a directory outside the home, with `PATH` pointing at `.cowork-runtime/python/bin` and no
`PYTHONPATH`.

| Test                                             | Result                                                 |
| ------------------------------------------------ | ------------------------------------------------------ |
| Interpreter runs from the staged path            | pass. `3.10.16`                                        |
| `sys.base_prefix` inside the staged tree         | pass                                                   |
| `os.__file__` inside the staged tree             | pass                                                   |
| `sys.path` entries under the home directory      | none                                                   |
| Bare `python3` resolves through `PATH`           | pass. Resolves to the staged `bin/python3`             |
| Pure-Python wheels import                        | pass. `docx`, `pptx`, `pypdf`                          |
| Compiled wheels import                           | pass. `numpy`, `pandas`, `lxml`, `PIL`, `cv2`, `onnxruntime`, `matplotlib` |
| Namespace packages import                        | pass. `zope.interface`, `lazr.uri`                     |
| `.pth` files execute from staged `site-packages` | pass                                                   |

The compiled wheels are the load-bearing ones. They carry native extensions with embedded
library paths, and they resolve them relative to the staged tree.

## What is not measured

One condition remains untested: whether the OS sandbox permits execution from the staged
directory, and not only reading of it. The reference states that the plugin directory and
the `PATH` directories inside it stay readable so that toolchains under the home directory
still run, which is this case. That is the reference's wording and not a measurement.

The test that settles it is a case granting `Bash` whose prompt asks for `python3 -V`,
`which -a python3` and `echo $PATH`, run against a plugin with the runtime already staged.
It did not run on the host it was attempted on, for the reason in the "A Bash-granting run
is refused on a host that runs a credential process" section of
[running_evals.md](running_evals.md). That refusal is a property of that host and not of
this design.

## What it does not reproduce

The interpreter and the wheels, nothing else. It inherits every gap the mirror has, listed
under "What the mirror does not reproduce" in [environments.md](environments.md).

One gap is its own. The mirror pins `3.10`, so uv resolves the newest 3.10 patch release,
and the image carries 3.10.12. The staged interpreter was 3.10.16 when this was
written. See [docker.md](docker.md) for the backend that carries the image's own
interpreter.
