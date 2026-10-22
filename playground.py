# class Strange:
#     def __init__(self, value: int) -> None:
#         self.value = value

#     def __add__(self, item: int):
#         self.value -= item
#         return self

#     def __

#     def __matmul__(self, item: int):
#         self.value += item
#         return self

#     def __str__(self) -> str:
#         return str(self.value)


# a = Strange(1)
# print(a)
# print(a + 1)
# print(a @ 100)
def compress(s: str):
    prev = s[0]
    streak = 1
    ans = ""
    for c in s[1:]:
        if c != prev:
            if streak > 1:
                ans += f"{prev}{streak}"
            else:
                ans += prev
            prev = c
            streak = 1
        else:
            streak += 1
    ans += f"{prev}{streak}"
    return ans


def decompress(s: str):
    splited = []
    key1 = "?"
    key2 = 0
    for c in s:
        if c.isalpha():
            splited.append((key1, key2))
            key1 = c
            key2 = 0
        else:
            key2 = key2 * 10 + int(c)
    splited.append((key1, key2))
    ans = ""
    for c, v in splited[1:]:
        if v != 0:
            ans += c * v
        else:
            ans += c
    return ans