class Strange:
    def __init__(self, value: int) -> None:
        self.value = value

    def __add__(self, item: int):
        self.value -= item
        return self

    def __str__(self) -> str:
        return str(self.value)


a = Strange(1)
print(a)
print(a + 1)
