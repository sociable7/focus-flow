"""Left sidebar navigation: Focus / History / Stats / Goals + Settings."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

PAGES = ("focus", "history", "stats", "goals")

PAGE_TITLES = {
    "focus": "Focus",
    "history": "History",
    "stats": "Stats",
    "goals": "Goals",
}


class SideNav(QFrame):
    """Narrow app rail. Emits ``page_requested`` / ``settings_requested``."""

    page_requested = Signal(str)
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sideBar")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 14)
        layout.setSpacing(6)

        brand = QLabel("Focus Flow")
        brand.setObjectName("brandLabel")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(brand)

        layout.addSpacing(10)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons = {}

        for name in PAGES:
            button = QPushButton(PAGE_TITLES[name])
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setAccessibleName(f"{PAGE_TITLES[name]} page")
            button.clicked.connect(
                lambda _checked=False, page=name: self.page_requested.emit(
                    page
                )
            )
            self._group.addButton(button)
            layout.addWidget(button)
            self._buttons[name] = button

        layout.addStretch()

        self.settings_button = QPushButton("Settings")
        self.settings_button.setObjectName("settingsNavButton")
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_button.setAccessibleName("Open settings")
        self.settings_button.clicked.connect(
            self.settings_requested.emit
        )
        layout.addWidget(self.settings_button)

    def set_current(self, name):
        button = self._buttons.get(name)
        if button is not None:
            button.setChecked(True)

    def current(self):
        checked = self._group.checkedButton()
        for name, button in self._buttons.items():
            if button is checked:
                return name
        return "focus"
