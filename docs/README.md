# Documentation

Reference material for running evals against Claude CoWork. Read the page that covers what
you are about to change, and link to it rather than restating it.

| Page                                             | Covers                                                          |
| ------------------------------------------------ | --------------------------------------------------------------- |
| [`approaches.md`](approaches.md)                 | The three approaches and what each proves                       |
| [`running_evals.md`](running_evals.md)           | The eval system: layout, scopes, flags, gate, logs, cadence     |
| [`docker.md`](docker.md)                         | The container that reproduces the CoWork image                  |
| [`cowork_driver.md`](cowork_driver.md)           | Driving a real CoWork session and collecting the result         |
| [`runtime.md`](runtime.md)                       | What a CoWork session provides and what is on the image         |
| [`environments.md`](environments.md)             | The two Python environments and how to build them               |
| [`plugin_eval.md`](plugin_eval.md)               | `claude plugin eval`: case layout, graders, flags, limits       |
| [`cowork_desktop.md`](cowork_desktop.md)         | Desktop application internals: deep links, session filesystem   |
| [`data/requirements.txt`](data/requirements.txt) | `pip freeze` from a CoWork VM, 136 pins, verbatim               |
| `data/requirements_installable.txt`              | The same minus the 9 pins that cannot install off the VM        |

Every page here is a snapshot of something measured, not a contract. Each carries its
capture date. Re-probe and update the date when the thing it describes changes.

A page here never links to a plan. Plans are deleted once implemented, so anything durable
a plan establishes is written into one of these pages before the plan is removed.

Writing rules are in [`../CLAUDE.md`](../CLAUDE.md). The public repository rule is in
[`../README.md`](../README.md), and it applies to every page here.
