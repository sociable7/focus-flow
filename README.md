# Focus Flow

Focus Flow is a professional Pomodoro productivity desktop application built with Python and PySide6 for macOS.

## Features

### Focus Timer

- Customizable focus duration
- Customizable short break
- Customizable long break
- Configurable sessions before a long break
- Start, pause and reset controls
- Pomodoro session cycle tracking

### Focus Tasks

- Enter the task you are working on
- Associate completed focus sessions with tasks
- Track total focus time for individual tasks

### History & Statistics

- Persistent local focus history
- Today's completed sessions
- Weekly focus totals
- Total focus time per task
- SQLite-based local database

### Goals

- Daily focus-time goal
- Daily progress indicator
- Persistent goal settings

### Appearance

- Minimal theme
- Classic Tomato theme
- Forest theme
- Midnight theme
- Custom accent colour
- Custom background colour

### Sound

- System Bell
- Double Bell
- Custom WAV files

### macOS Experience

- Desktop notifications
- Keyboard shortcuts
- System status-bar controls
- Compact floating timer
- Always-on-top floating timer
- Native macOS-style interface

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl/Command + Space | Start / Pause |
| Ctrl/Command + R | Reset |

## Technologies

- Python 3
- PySide6
- Qt
- SQLite
- QSettings
- macOS AppleScript notifications

## Project Structure

```text
1.Focus Flow/
├── app/
│   ├── __init__.py
│   ├── main_window.py
│   ├── timer.py
│   ├── settings.py
│   ├── themes.py
│   ├── sounds.py
│   ├── database.py
│   ├── history.py
│   ├── goals.py
│   ├── notifications.py
│   ├── shortcuts.py
│   ├── menu_bar.py
│   └── floating_timer.py
│
├── assets/
│   ├── sounds/
│   └── icons/
│       └── settings.svg
│
├── main.py
├── README.md
├── requirements.txt
└── .gitignore
