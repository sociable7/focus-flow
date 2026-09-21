# Focus Flow

Focus Flow is a Pomodoro productivity desktop application for macOS, built with Python and PySide6. It runs a configurable focus/break timer, associates completed sessions with named tasks, and keeps a persistent local history with daily and weekly totals.

## Features

### Focus timer

- Configurable focus duration (1–180 min), short break (1–60 min), and long break (1–120 min)
- Configurable cycle length: sessions before a long break (1–12)
- Start, pause, and reset controls with a progress bar and per-cycle session dots
- A focus session cannot start until a task is entered; the task field locks while the timer runs
- When a timer finishes it stays finished: exactly one completion event fires per run, and the next phase is prepared without auto-starting

### Tasks and sessions

- Each completed focus session is saved with its task name, start time, and duration
- Per-task total focus time is tracked in the history view

### History and statistics

- Local SQLite database at `~/Library/Application Support/Focus Flow/focus_flow.db` (schema v3, indexed over session time/task)
- History dialog with six summaries — Today, This Week, Total Focus Time, Day Streak, Sessions, Top Task — plus a last-7-days strip and a session table (most recent 50 sessions)
- Lifetime totals and session counts come from SQL aggregates; the table reads a single capped query
- Only completed focus sessions are recorded and displayed

### Daily goal

- Configurable daily focus target (15–1440 min, default 120), stored per day in the SQLite `daily_goals` table (schema v3)
- Main-window progress label shows today's minutes against the target
- Values from the earlier `QSettings`-based storage are imported into the database on startup; `QSettings` is kept as a legacy mirror for backward compatibility

### Appearance

- Five theme options: System (follows macOS light/dark mode), Minimal, Classic Tomato, Forest, Midnight (default)
- Optional accent-color and background-color overrides; "Use Design Colors" restores the theme defaults
- Theme changes apply to the main window, settings dialog, history dialog, and floating timer; System re-applies automatically when macOS appearance changes

### Sound

- Completion sounds: System Bell, Double Bell, or a custom WAV file
- Bundled fallback sound in `assets/sounds/system_bell.wav`; a missing custom file falls back to the system bell
- Playback is dispatched asynchronously (`SoundService`) so the timer-finished handler never waits on the audio backend

### Notifications

- macOS desktop notification when a focus session, short break, or long break completes
- Notifications can be disabled in Settings
- Delivery runs on a worker thread (`NotificationService`); the `osascript` subprocess never blocks the event loop

### Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl/Command + Space | Start / Pause |
| Ctrl/Command + R | Reset |

Shortcuts are registered for both Ctrl and Command variants and do not fire while typing in the task field.

### Stats and goals

- Stats view: lifetime totals, 14-day custom-painted bar chart, per-task breakdown, and a 7-day streak strip with the current day-streak count
- Goals view: daily target editor with progress, today's totals, streak, and recent-target history

### macOS behavior

- Compact floating timer: frameless, always-on-top, shown only via the tray menu ("Show Compact Timer") and never by app focus changes; stays visible without stealing focus, shares the main timer instance
- Mini window now carries a progress bar, a break-only Skip button, persisted position, and a configurable opacity (Settings → Compact Timer, 40–100%)
- Native menu bar: app menu (About, Settings, Quit), Timer, View (page navigation), and Window (minimize, compact timer) menus with standard macOS roles
- Status-bar (tray) menu: Start/Pause, Reset, Show Focus Flow, Show Compact Timer, Quit — tooltip and labels track live timer state
- Settings and window state persist through QSettings (`Focus Flow` / `Focus Flow`)

## Technology stack

- Python 3.13
- PySide6 6.11.2 (Qt Widgets, Multimedia for sounds)
- SQLite via the standard-library `sqlite3` module (no ORM)
- QSettings for preferences; AppleScript (`osascript`) for notifications
- Tests: standard-library `unittest` with `QTest` (no pytest)

## Project structure

```text
focus-flow/
├── main.py                  # Entry point: creates QApplication and MainWindow
├── requirements.txt         # Pinned PySide6 dependencies
├── app/
│   ├── main_window.py       # MainWindow: wires services, views, dialogs, and menus
│   ├── settings_dialog.py   # SettingsDialog: timer/goal/appearance/sound/notification settings
│   ├── timer.py             # PomodoroTimer: backwards-compatible alias of core Clock
│   ├── database.py          # SQLite persistence (sessions, goals, daily_goals tables; schema v3)
│   ├── history.py           # HistoryManager: today/week/total/count/streak/daily-totals/task-breakdown queries
│   ├── history_dialog.py    # HistoryDialog: summaries + 7-day strip + top task + recent-sessions table
│   ├── goals.py             # GoalManager: canonical per-day goals in daily_goals (validated 15–1440)
│   ├── core/                # Clock (countdown engine), SessionEngine (phase state machine), session enums
│   ├── services/            # SettingsStore, GoalService, theme_service,
│   │                         # SoundService, NotificationService
│   ├── persistence/         # Schema migrations (v1 → v3) and SessionRepository queries
│   ├── ui/                  # Focus, history, stats, and goals views plus sidebar and shared components
│   ├── settings.py          # AppSettings: backwards-compatible alias of SettingsStore
│   ├── themes.py            # Theme palettes and lookup
│   ├── sounds.py            # SoundManager: cached QSoundEffect playback
│   ├── notifications.py     # macOS AppleScript notifications (sync engine)
│   ├── shortcuts.py         # Ctrl/Command keyboard shortcuts
│   ├── floating_timer.py    # Compact timer: progress, skip, opacity, persisted position
│   ├── native_menu.py       # Native macOS menu bar (app/Timer/View/Window)
│   └── menu_bar.py          # Status-bar (tray) menu with live state sync
├── packaging/               # .app prep: Info.plist template + build notes
├── .github/workflows/ci.yml # CI: compileall + headless unittest on macOS
├── widgets/                 # Legacy empty stubs (unused; views live in app/ui/)
├── assets/
│   ├── icons/               # settings.svg and related artwork
│   └── sounds/              # system_bell.wav fallback sound
└── tests/
    ├── test_regressions.py  # 8 regression tests (timer, transitions, shortcuts, sound, DB, history)
    ├── test_foundation.py   # 19 foundation tests (clock, engine, settings, migrations, themes)
    ├── test_goals.py        # 21 goal tests (migration, GoalManager, GoalService, goal UI)
    ├── test_history.py      # 14 analytics tests (totals, daily buckets, streaks, breakdown, dialog)
    ├── test_session_repo.py # 10 SessionRepository query tests (incl. v3 migration)
    ├── test_shell.py        # 18 shell tests (navigation, banner, settings, history/goals/stats views)
    ├── test_group4.py       # 20 tests (async services, menus, mini timer, System theme, streak)
    └── test_mini_interactions.py # 17 mini-timer interaction tests (task gate, skip, toggle routing)
```

The layered design keeps timekeeping (`core/`), persistence (`database.py`, `persistence/`), cross-cutting services (`services/`), and presentation (`ui/`, dialogs, menus) separate. `MainWindow` composes these pieces rather than implementing them; `timer.py` and `settings.py` remain as thin compatibility aliases so existing imports keep working.

## Requirements

- macOS (notifications, floating-window behavior, and tray integration are macOS-oriented)
- Python 3.13
- A display for the GUI; tests run headless via the `offscreen` platform

## Local development setup

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## How to run the application

```bash
.venv/bin/python main.py
```

## How to run tests

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
```

A single test:

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest tests.test_regressions.<TestClass>.<test_name>
```

All GUI tests require `QT_QPA_PLATFORM=offscreen` when no display is available. Window-level tests isolate user state by patching `app.main_window.Database` and `app.settings.QSettings` with a temporary directory (see `tests/test_regressions.py`); follow that pattern for new tests.

## Current project status

Working local application, under active development. Known limitations:

- No `.app` bundle, installer, code signing, or sandbox/entitlements configuration — run from source only (see `packaging/` for preparation notes and an `Info.plist` template).
- Notifications are dispatched on a worker thread but still go through `osascript`; there is no `UNUserNotificationCenter` integration yet.
- The legacy SQLite `goals` table is retained read-only for migration reference; the live daily-goal store is `daily_goals` via `GoalManager`/`GoalService`.
- `widgets/` contains empty legacy placeholder modules that are not used; the active views live in `app/ui/`.
- CI runs `compileall` plus the headless `unittest` suite (`.github/workflows/ci.yml`); no lint or typecheck configuration.

## Roadmap (planned, not implemented)

- Application packaging: `.app` bundle build, signing/notarization, and sandbox-compatible data and notification paths (prep work in `packaging/`)
- Modern macOS notifications with permission handling and actions (`UNUserNotificationCenter` to replace `osascript`)

## License

Focus Flow is proprietary software under a custom source-available license. See [LICENSE](LICENSE) for details.

## Security

To report a security vulnerability, see [SECURITY.md](SECURITY.md). Please report privately and do not open a public issue before it has been addressed.
