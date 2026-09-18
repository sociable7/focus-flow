from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QApplication


class SoundManager:
    def __init__(self):
        self.effect = QSoundEffect()

    def play(self, sound_name, custom_sound=""):
        if sound_name == "System Bell":
            QApplication.beep()

        elif sound_name == "Double Bell":
            QApplication.beep()

            # Small delay is intentionally avoided here.
            # We use two system notifications.
            QApplication.beep()

        elif sound_name == "Custom WAV":
            if custom_sound and Path(custom_sound).exists():
                self.effect.setSource(
                    QUrl.fromLocalFile(custom_sound)
                )
                self.effect.setVolume(1.0)
                self.effect.play()
            else:
                QApplication.beep()

        else:
            QApplication.beep()

    def test(self, sound_name, custom_sound=""):
        self.play(sound_name, custom_sound)