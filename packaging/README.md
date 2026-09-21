# Packaging preparation (Group 4)

Focus Flow currently runs from source. This folder collects what a
future `.app` bundle needs so packaging work can start without digging
through the codebase.

## Current state

- Entry point: `main.py:main()` (`app.exec()` with
  `setQuitOnLastWindowClosed(False)` so the tray/mini window can
  outlive visible windows).
- Version: single source in `app/__init__.py::__version__`
  (keep `packaging/Info.plist`'s `CFBundleShortVersionString` in sync).
- Data files that must ship beside the bundle:
  - `assets/sounds/system_bell.wav` (fallback completion sound)
  - `assets/icons/settings.svg` (tray icon)
- Runtime locations (already sandbox-friendly patterns):
  - Database: `~/Library/Application Support/Focus Flow/focus_flow.db`
  - Logs: `~/Library/Logs/Focus Flow/focus_flow.log`
  - Preferences: macOS defaults via `QSettings("Focus Flow", "Focus Flow")`

## Suggested path (PyInstaller)

```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pip install pyinstaller
.venv/bin/pyinstaller \
  --name "Focus Flow" \
  --windowed \
  --osx-bundle-identifier "flow.focus.app" \
  --add-data "assets:assets" \
  main.py
```

Then codesign/notarize the resulting `dist/Focus Flow.app` with your
Apple Developer identity before distributing.

## Still to do (beyond Group 4)

- `.app` bundle build + Apple signing/notarization
- Sandbox entitlements review (notifications currently use `osascript`,
  which needs a hardened-runtime exception or replacement with
  `UNUserNotificationCenter`)
- Sparkle/auto-update or App Store packaging
