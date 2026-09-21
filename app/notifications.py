import subprocess


class NotificationManager:
    """
    Handles macOS notifications for Focus Flow.
    """

    def __init__(self, app_name="Focus Flow"):
        self.app_name = app_name

    def show(self, title, message):
        """
        Show a macOS notification.

        Args:
            title (str): Notification title.
            message (str): Notification body.
        """

        script = f'''
        display notification "{self._escape(title)}"
        with title "{self._escape(self.app_name)}"
        subtitle "{self._escape(message)}"
        '''

        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    script,
                ],
                check=False,
            )

        except OSError:
            # If macOS notification is unavailable,
            # don't crash the application.
            pass

    @staticmethod
    def _escape(text):
        """
        Escape characters that could break
        the AppleScript command.
        """

        return (
            str(text)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", " ")
        )

    def focus_complete(self):
        """
        Notification shown when a focus session ends.
        """

        self.show(
            "Focus session complete",
            "Time for a break.",
        )

    def short_break_complete(self):
        """
        Notification shown when a short break ends.
        """

        self.show(
            "Break finished",
            "Ready to focus again?",
        )

    def long_break_complete(self):
        """
        Notification shown when a long break ends.
        """

        self.show(
            "Long break finished",
            "Ready for another focus session?",
        )