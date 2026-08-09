"""
fsrs (vendored py-fsrs)
-----------------------

Vendored from `open-spaced-repetition/py-fsrs` (v6.3.2, MIT license — see
LICENSE notice in ``fsrs/LICENSE`` / the repository README). py-fsrs is the
official Python implementation of the FSRS scheduler algorithm.

Changes vs upstream (all mechanical):
- Absolute imports converted to relative (``from .state import State`` etc.)
  so the package lives under ``app.services.fsrs``.
- The ``Optimizer`` lazy-loader is dropped because it requires torch/numpy/
  pandas (not part of this app's dependencies). The scheduler itself has zero
  runtime dependencies beyond ``typing-extensions``.

See ``REPOSITORY_INTEGRATION_PLAN.md`` (Idea 52 — FSRS) for the integration
notes and the source repo: https://github.com/open-spaced-repetition/py-fsrs
"""

from .scheduler import Scheduler
from .state import State
from .card import Card
from .rating import Rating
from .review_log import ReviewLog

__all__ = ["Scheduler", "Card", "Rating", "ReviewLog", "State"]
