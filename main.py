import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app import __version__
from app.main_window import MainWindow

LOG_FILE_NAME = "focus_flow.log"
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 3


def configure_logging():
    """Log to the macOS log folder and the console (idempotent).

    Group 4 polish: rotating file handler (1 MB x 3) so long-running
    use never grows the log unboundedly, plus ``captureWarnings`` so
    Qt/Python warnings land in the same sinks.
    """
    log_dir = (
        Path.home() / "Library" / "Logs" / "Focus Flow"
    )
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s %(name)s %(levelname)s: %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            log_dir / LOG_FILE_NAME,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        pass

    try:
        logging.captureWarnings(True)
    except Exception:
        pass

    logging.getLogger(__name__).info(
        "Focus Flow %s starting", __version__
    )


def main():
    configure_logging()

    app = QApplication(sys.argv)

    # Hiding the mini overlay (or the main window during mini mode)
    # must never quit the application.
    app.setQuitOnLastWindowClosed(False)

    app.setApplicationName(
        "Focus Flow"
    )

    app.setOrganizationName(
        "Focus Flow"
    )

    window = MainWindow()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()
