"""Every test under tests/integration/ is integration, whether or not it says so.

The marker is applied here so it cannot be forgotten on a new file. Selection stays
`-m integration`, which is what pyproject.toml deselects by default.

pytest_collection_modifyitems in a subdirectory conftest still receives every collected
item, so the hook filters by path.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent


def pytest_collection_modifyitems(items) -> None:
    for item in items:
        if HERE in Path(str(item.path)).parents:
            item.add_marker("integration")
