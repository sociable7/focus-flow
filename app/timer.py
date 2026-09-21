"""Backwards-compatible timer alias.

Group 1: the canonical implementation is ``app.core.clock.Clock``
(monotonic deadline + drift correction). ``PomodoroTimer`` remains as a
thin subclass so existing imports and tests keep working; new code
should import ``Clock`` (or ``SessionEngine``) directly.
"""

from app.core.clock import Clock


class PomodoroTimer(Clock):
    pass
