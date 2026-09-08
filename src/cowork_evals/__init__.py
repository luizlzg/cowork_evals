"""Drive Claude CoWork and read what a session produced.

See docs/cowork_driver.md for the behaviour and docs/cowork_desktop.md for the
application internals it couples to.
"""

from .config import Config, CoWorkError
from .cowork import CoWork

__all__ = ["Config", "CoWork", "CoWorkError"]
