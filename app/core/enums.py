from enum import Enum


class SessionPhase(str, Enum):
    """Canonical timer phases.

    Values match the legacy ``MainWindow.mode`` strings so existing
    UI text, settings and tests keep working during the migration.
    """

    FOCUS = "Focus"
    SHORT_BREAK = "Short Break"
    LONG_BREAK = "Long Break"


class BreakKind(str, Enum):
    SHORT = "short"
    LONG = "long"


MODE_TO_PHASE = {
    "Focus": SessionPhase.FOCUS,
    "Short Break": SessionPhase.SHORT_BREAK,
    "Long Break": SessionPhase.LONG_BREAK,
}


def phase_from_mode(mode):
    """Return the SessionPhase for a legacy mode string."""
    try:
        return MODE_TO_PHASE[mode]
    except KeyError:
        raise ValueError(f"Unknown session mode: {mode!r}") from None


def mode_label_for_phase(phase):
    """Return the header label text for a phase."""
    if phase == SessionPhase.FOCUS:
        return "FOCUS SESSION"
    if phase == SessionPhase.SHORT_BREAK:
        return "SHORT BREAK"
    return "LONG BREAK"
