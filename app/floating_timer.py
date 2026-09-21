from PySide6.QtCore import (
    QPoint,
    Qt,
    Signal,
)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FloatingTimer(QWidget):
    """
    Small always-on-top timer window.

    It shares the same PomodoroTimer instance
    as the main window.
    """

    close_requested = Signal()
    position_changed = Signal(int, int)

    def __init__(
        self,
        timer,
        parent=None,
        toggle_callback=None,
        settings=None,
        on_moved=None,
        skip_callback=None,
        open_callback=None,
    ):
        super().__init__(parent)

        self.timer = timer
        self.toggle_callback = toggle_callback
        self.settings = settings
        self.on_moved = on_moved
        self.skip_callback = skip_callback
        self.open_callback = open_callback
        self.drag_position = QPoint()
        self._restoring_position = False

        self.setWindowTitle(
            "Focus Flow"
        )

        # Fixed width; the height hugs the visible rows (see
        # ``_fit_height``). The skip row and the task row come and go
        # (breaks, task capture, task hint), so a single fixed height
        # would either clip the 32pt time readout or leave a blank gap.
        self.setFixedWidth(236)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )

        # On macOS, Qt::Tool maps to NSPanel and is hidden when the owning
        # application deactivates unless this attribute is enabled.
        self.setAttribute(
            Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow,
            True,
        )
        self.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating,
            True,
        )
        # Rounded container over a transparent window so the corners
        # show the desktop, not the default window background.
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True,
        )
        # Clicking the mini window must never take keyboard focus or
        # activate the app (which the main window observes to hide the
        # mini and restore itself). Buttons already opt out of focus.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._dragging = False
        self._drag_offset = QPoint()

        self.build_ui()
        self.connect_signals()
        self._install_drag_filters()
        self.apply_theme()
        self._add_shadow()
        self.restore_position()

    # =========================================================
    # UI
    # =========================================================

    def build_ui(self):
        self.container = QFrame()

        self.container.setObjectName(
            "floatingContainer"
        )

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        main_layout.addWidget(
            self.container
        )

        container_layout = QVBoxLayout(
            self.container
        )

        container_layout.setContentsMargins(
            16,
            12,
            16,
            14,
        )

        container_layout.setSpacing(6)

        # -----------------------------------------------------
        # Top row
        # -----------------------------------------------------

        top_layout = QHBoxLayout()

        self.mode_label = QLabel(
            "FOCUS"
        )

        self.mode_label.setObjectName(
            "modeLabel"
        )

        self.close_button = QPushButton(
            "×"
        )

        self.close_button.setObjectName(
            "closeButton"
        )

        self.close_button.setFixedSize(
            24,
            24,
        )

        self.close_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_button.setAccessibleName("Hide compact timer")
        self.close_button.setAccessibleDescription(
            "Hides the compact timer. The session keeps running."
        )

        top_layout.addWidget(
            self.mode_label
        )

        top_layout.addStretch()

        top_layout.addWidget(
            self.close_button
        )

        container_layout.addLayout(
            top_layout
        )

        self.task_label = QLabel()
        self.task_label.setObjectName("taskLabel")
        self.task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.task_label.setWordWrap(False)
        self.task_label.hide()
        container_layout.addWidget(self.task_label)

        # -----------------------------------------------------
        # Timer
        # -----------------------------------------------------

        self.time_label = QLabel(
            "25:00"
        )

        self.time_label.setObjectName(
            "timeLabel"
        )

        self.time_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        font = QFont()

        font.setPointSize(32)
        font.setWeight(
            QFont.Weight.DemiBold
        )

        self.time_label.setFont(font)

        container_layout.addWidget(
            self.time_label
        )

        # -----------------------------------------------------
        # Progress (mirrors the main timer card)
        # -----------------------------------------------------

        self.mini_progress = QProgressBar()

        self.mini_progress.setObjectName(
            "miniProgressBar"
        )

        self.mini_progress.setTextVisible(False)

        self.mini_progress.setFixedHeight(5)

        self.mini_progress.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.mini_progress.setAccessibleName("Session progress")

        container_layout.addWidget(
            self.mini_progress
        )

        # -----------------------------------------------------
        # Pause button
        # -----------------------------------------------------

        self.pause_button = QPushButton(
            "Pause"
        )

        self.pause_button.setObjectName(
            "pauseButton"
        )

        self.pause_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.pause_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.pause_button.setAccessibleName("Start or pause timer")

        self.pause_button.setAccessibleDescription(
            "Starts or pauses the shared Pomodoro timer."
        )

        container_layout.addWidget(
            self.pause_button
        )

        # -----------------------------------------------------
        # Skip button (breaks only; hidden during focus)
        # -----------------------------------------------------

        self.skip_button = QPushButton(
            "Skip Break"
        )

        self.skip_button.setObjectName(
            "miniSkipButton"
        )

        self.skip_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.skip_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.skip_button.setAccessibleName("Skip break")

        self.skip_button.setAccessibleDescription(
            "Ends the current break and prepares the next focus session."
        )

        self.skip_button.hide()

        container_layout.addWidget(
            self.skip_button
        )

        # -----------------------------------------------------
        # Open-main-window button (always visible; explicit only)
        # -----------------------------------------------------

        self.open_button = QPushButton(
            "Open Main Window"
        )

        self.open_button.setObjectName(
            "miniOpenButton"
        )

        self.open_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.open_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.open_button.setAccessibleName("Open main window")

        self.open_button.setAccessibleDescription(
            "Shows the main Focus Flow window. The session keeps running."
        )

        container_layout.addWidget(
            self.open_button
        )

        self._fit_height()

    # =========================================================
    # Signals
    # =========================================================

    def connect_signals(self):
        self.timer.tick.connect(
            self.update_time
        )

        self.timer.finished.connect(
            self.timer_finished
        )

        self.pause_button.clicked.connect(
            self.toggle_timer
        )

        self.skip_button.clicked.connect(
            self.skip_break
        )

        self.open_button.clicked.connect(
            self.open_main_window
        )

        self.close_button.clicked.connect(
            self.close_requested.emit
        )

    # =========================================================
    # Timer
    # =========================================================

    def update_time(self, seconds):
        minutes = seconds // 60
        remaining_seconds = seconds % 60

        self.time_label.setText(
            f"{minutes:02d}:{remaining_seconds:02d}"
        )

        total = getattr(self.timer, "total_seconds", 0) or 0
        if total > 0:
            elapsed = max(0, total - seconds)
            self.mini_progress.setValue(int(elapsed / total * 100))
        else:
            self.mini_progress.setValue(0)

        self.update_pause_button()

    def skip_break(self):
        if self.skip_callback is not None:
            try:
                self.skip_callback()
            except Exception:
                pass
        self.set_break_visible(False)

    def set_break_visible(self, is_break):
        """Show the skip affordance only during breaks."""
        try:
            self.skip_button.setVisible(bool(is_break))
        except Exception:
            pass
        self._fit_height()

    def open_main_window(self):
        """Forward the explicit "Open Main Window" action to the owner.

        Visibility-only request: never touches the timer or session
        state. Unlike the activation guards, this always forwards —
        the user explicitly asked for the main window.
        """
        if self.open_callback is not None:
            try:
                self.open_callback()
            except Exception:
                pass

    def show_task_hint(self):
        """Mirror the main window's "task needed" prompt in the mini.

        Shown when Start is pressed with no focus task captured. Never
        touches the timer and never shows the main window; the next
        ``set_task_name`` (task capture, prepare, reset) replaces it.
        """
        try:
            self.task_label.setText("Add a task in the main window")
            self.task_label.setToolTip(
                "Open the main window to enter a focus task, "
                "then press Start."
            )
            self.task_label.setVisible(True)
        except Exception:
            pass
        self._fit_height()

    def _fit_height(self):
        """Fix the height to the visible rows (width stays 236).

        Keeps the window compact as the skip/task rows appear and
        disappear. Never touches the timer or other windows.
        """
        try:
            layout = self.container.layout()
            height = max(
                layout.totalSizeHint().height(),
                layout.totalMinimumSize().height(),
            )
            if height > 0:
                self.setFixedSize(236, height)
        except Exception:
            pass

    def toggle_timer(self):
        if self.toggle_callback is not None:
            self.toggle_callback()
            self.update_pause_button()
            return

        if self.timer.is_running():
            self.timer.pause()

        else:
            self.timer.start()

        self.update_pause_button()

    def update_pause_button(self):
        if self.timer.is_running():
            self.pause_button.setText(
                "Pause"
            )

        else:
            self.pause_button.setText(
                "Start"
            )

    def timer_finished(self):
        self.pause_button.setText(
            "Start"
        )

    def set_mode(self, mode):
        self.mode_label.setText(
            mode.upper()
        )

    def set_task_name(self, task_name):
        task_name = (task_name or "").strip()
        self.task_label.setText(task_name)
        self.task_label.setToolTip(task_name)
        self.task_label.setVisible(bool(task_name))
        self._fit_height()
        if task_name:
            elided = self.task_label.fontMetrics().elidedText(
                task_name,
                Qt.TextElideMode.ElideRight,
                self.width() - 40,
            )
            self.task_label.setText(elided)

    def show_without_activating(self):
        """Show above other apps without stealing keyboard focus.

        With WA_ShowWithoutActivating set, plain show() does not
        activate the app. Deliberately no raise_()/activateWindow()
        here: those re-activate Focus Flow and caused the
        focus-steal / blink loop when switching macOS apps.
        """
        self.apply_opacity()
        self._fit_height()
        self.show()

    # =====================================================
    # Opacity (Group 4; persisted via SettingsStore)
    # =====================================================

    def apply_opacity(self):
        """Apply the persisted mini-window opacity; never raises."""
        try:
            getter = getattr(self.settings, "get_mini_opacity", None)
            opacity = float(getter()) if callable(getter) else 1.0
        except Exception:
            opacity = 1.0
        try:
            self.setWindowOpacity(max(0.4, min(1.0, opacity)))
        except Exception:
            pass

    # =========================================================
    # Position: persist + restore, clamped to visible screens
    # =========================================================

    def default_top_right_position(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return QPoint(0, 0)
        area = screen.availableGeometry()
        margin = 16
        return QPoint(
            area.right() - self.width() - margin,
            area.top() + margin,
        )

    def clamp_to_visible_screen(self, pos):
        from PySide6.QtGui import QGuiApplication

        point = QPoint(int(pos.x()), int(pos.y()))
        geometry = self.frameGeometry()
        geometry.moveTopLeft(point)
        for screen in QGuiApplication.screens():
            if screen.availableGeometry().intersects(geometry):
                return point
        primary = QGuiApplication.primaryScreen()
        if primary is None:
            return point
        fallback = primary.availableGeometry()
        x = min(
            max(point.x(), fallback.left()),
            max(fallback.left(), fallback.right() - self.width()),
        )
        y = min(
            max(point.y(), fallback.top()),
            max(fallback.top(), fallback.bottom() - self.height()),
        )
        return QPoint(x, y)

    def restore_position(self):
        saved = None
        if self.settings is not None:
            getter = getattr(self.settings, "get_mini_position", None)
            if callable(getter):
                try:
                    saved = getter()
                except Exception:
                    saved = None
        if saved is None:
            pos = self.default_top_right_position()
        else:
            pos = QPoint(int(saved[0]), int(saved[1]))
        self._restoring_position = True
        try:
            self.move(self.clamp_to_visible_screen(pos))
        finally:
            self._restoring_position = False

    def _persist_position(self, pos):
        if self.settings is not None:
            setter = getattr(self.settings, "set_mini_position", None)
            if callable(setter):
                try:
                    setter(int(pos.x()), int(pos.y()))
                except Exception:
                    pass
        if self.on_moved is not None:
            try:
                self.on_moved(int(pos.x()), int(pos.y()))
            except Exception:
                pass
        try:
            self.position_changed.emit(int(pos.x()), int(pos.y()))
        except Exception:
            pass

    def moveEvent(self, event):
        super().moveEvent(event)
        if not self._restoring_position and self.isVisible():
            self._persist_position(self.pos())

    def closeEvent(self, event):
        # Hiding the mini window must never quit the application;
        # it can be re-shown from the main window / app activation.
        event.ignore()
        self.hide()
        try:
            self.close_requested.emit()
        except Exception:
            pass

    # =========================================================
    # Dragging
    # =========================================================

    def _install_drag_filters(self):
        """Let background presses (container/labels/progress) drag us.

        Child widgets swallow mouse events, so handling
        ``mousePressEvent`` on this widget alone never sees presses on
        the container or labels. An event filter on the non-button
        children recovers background dragging without touching button
        clicks (buttons are deliberately excluded).
        """
        seen = set()
        candidates = [self.container]
        try:
            candidates.extend(self.container.findChildren(QWidget))
        except Exception:
            pass
        for child in candidates:
            try:
                if isinstance(child, QPushButton):
                    continue
                if id(child) in seen:
                    continue
                seen.add(id(child))
                child.installEventFilter(self)
            except Exception:
                pass

    def eventFilter(self, watched, event):
        try:
            from PySide6.QtCore import QEvent

            if isinstance(watched, QPushButton):
                return super().eventFilter(watched, event)
            etype = event.type()
            if etype == QEvent.Type.MouseButtonPress and (
                event.button() == Qt.MouseButton.LeftButton
            ):
                self._begin_drag(event.globalPosition().toPoint())
                event.accept()
                return True
            if (
                etype == QEvent.Type.MouseMove
                and self._dragging
                and (event.buttons() & Qt.MouseButton.LeftButton)
            ):
                self._do_drag(event.globalPosition().toPoint())
                event.accept()
                return True
            if (
                etype == QEvent.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton
                and self._dragging
            ):
                self._end_drag()
                event.accept()
                return True
        except Exception:
            pass
        return super().eventFilter(watched, event)

    def _begin_drag(self, global_pos):
        self._dragging = True
        self.drag_position = global_pos - self.frameGeometry().topLeft()
        self._drag_offset = QPoint(self.drag_position)

    def _do_drag(self, global_pos):
        self.move(global_pos - self._drag_offset)

    def _end_drag(self):
        self._dragging = False
        self._persist_position(self.pos())

    def mousePressEvent(self, event):
        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            self._begin_drag(event.globalPosition().toPoint())

            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and (
            event.buttons()
            & Qt.MouseButton.LeftButton
        ):
            self._do_drag(event.globalPosition().toPoint())

            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._end_drag()

    # =========================================================
    # Native-feel polish (shadow only; colors stay in ThemeService)
    # =========================================================

    def _add_shadow(self):
        try:
            from PySide6.QtGui import QColor

            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(28)
            shadow.setOffset(0, 8)
            shadow.setColor(QColor(0, 0, 0, 90))
            self.container.setGraphicsEffect(shadow)
        except Exception:
            pass

    # =========================================================
    # Styling
    # =========================================================

    def apply_theme(self, resolved=None, theme=None, accent=None):
        """Style with the shared ThemeService; follows the user theme.

        Accepts the resolved dict from ``theme_service.resolve`` (as
        passed by ``MainWindow.apply_theme``) or, for backward
        compatibility, a tokens dict plus accent. With no arguments the
        theme is read from ``self.settings``. No hard-coded palette
        lives here; defaults come from ``theme_service.resolve``.
        """
        from app.services import theme_service

        if isinstance(resolved, dict) and "tokens" in resolved:
            effective = resolved
        elif isinstance(theme, dict) and "surface" in theme:
            effective = {
                "tokens": dict(theme),
                "accent": accent or theme.get("accent", ""),
                "background": theme.get("background", ""),
            }
            if not effective["accent"] or not effective["background"]:
                base = theme_service.resolve(
                    self._settings_theme_name(),
                    accent or self._settings_accent(),
                    self._settings_background(),
                )
                if not effective["accent"]:
                    effective["accent"] = base["accent"]
                if not effective["background"]:
                    effective["background"] = base["background"]
        else:
            name = theme if isinstance(theme, str) else None
            effective = theme_service.resolve(
                name or self._settings_theme_name(),
                accent or self._settings_accent(),
                self._settings_background(),
            )
        self.setStyleSheet(
            theme_service.build_floating_stylesheet(effective)
        )

    def _settings_theme_name(self):
        getter = getattr(self.settings, "get_theme", None)
        try:
            return getter() if callable(getter) else ""
        except Exception:
            return ""

    def _settings_accent(self):
        getter = getattr(self.settings, "get_accent_color", None)
        try:
            return getter() if callable(getter) else ""
        except Exception:
            return ""

    def _settings_background(self):
        getter = getattr(self.settings, "get_background_color", None)
        try:
            return getter() if callable(getter) else ""
        except Exception:
            return ""
