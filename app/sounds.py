from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtMultimedia import QSoundEffect


class SoundManager(QObject):
    """Keeps sound effects alive and plays them once their media is loaded."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.sounds_dir = (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "sounds"
        )
        self.system_bell_sound = self.sounds_dir / "system_bell.wav"
        self._effects = {}
        self._pending_plays = {}

        # Start loading the bundled effect during application startup so the
        # first completion sound is not lost to asynchronous media loading.
        self._effect_for(self.system_bell_sound)

    def play(self, sound_name, custom_sound=""):
        if sound_name == "Custom WAV":
            path = Path(custom_sound) if custom_sound else self.system_bell_sound
            if not path.is_file():
                path = self.system_bell_sound
            return self._play_file(path)

        played = self._play_file(self.system_bell_sound)
        if sound_name == "Double Bell":
            # A gap creates two distinct bells rather than simultaneous audio.
            QTimer.singleShot(
                180,
                lambda: self._play_file(self.system_bell_sound),
            )
        return played

    def test(self, sound_name, custom_sound=""):
        self.play(sound_name, custom_sound)

    def _effect_for(self, path):
        path = Path(path).resolve()
        effect = self._effects.get(path)
        if effect is not None:
            return effect

        effect = QSoundEffect(self)
        # Cache before assigning the source: some backends can emit a status
        # change immediately when setSource() begins loading.
        self._effects[path] = effect
        self._pending_plays[path] = 0
        effect.setVolume(1.0)
        effect.statusChanged.connect(
            lambda path=path: self._play_when_loaded(path)
        )
        effect.setSource(QUrl.fromLocalFile(str(path)))
        return effect

    def _play_file(self, path):
        path = Path(path)
        if not path.is_file():
            return False

        path = path.resolve()
        effect = self._effect_for(path)
        if effect.status() == QSoundEffect.Status.Ready:
            effect.play()
        elif effect.status() == QSoundEffect.Status.Loading:
            self._pending_plays[path] += 1
        else:
            return False
        return True

    def _play_when_loaded(self, path):
        effect = self._effects[path]
        if effect.status() != QSoundEffect.Status.Ready:
            return

        pending = self._pending_plays[path]
        self._pending_plays[path] = 0
        for index in range(pending):
            QTimer.singleShot(index * 180, effect.play)
