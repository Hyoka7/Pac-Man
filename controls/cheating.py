class CheatHandler:
    def __init__(self, command: list[int]) -> None:
        self.command = command
        self.index = 0

    def consume(self, key: int) -> bool:
        if self.command[self.index] == key:
            self.index += 1
            if self.index == len(self.command):
                self.index = 0
                return True
            return False
        else:
            self.index = 0
            return False
