class CheatHandler:
    """Detect an ordered key sequence that toggles cheat mode."""

    def __init__(self, command: list[int]) -> None:
        """Store the command and start matching from its first key.

        Args:
            command: Key codes that must be typed in this exact order.
        """
        self.command = command
        self.index = 0

    def consume_key(self, key: int) -> bool:
        """Advance or reset the match with one key.

        Args:
            key: Pressed key code.

        Returns:
            True only when the key completes the whole command.
        """
        if self.command[self.index] == key:
            self.index += 1
            if self.index == len(self.command):
                self.index = 0
                return True
            return False
        else:
            self.index = 0
            return False
