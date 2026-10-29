"""Keyboard symbols and actions requested from the window owner."""

from enum import Enum, IntEnum, auto


class KeyEnum(IntEnum):
    A = 97
    C = 99
    D = 100
    F = 102
    H = 104
    I = 105
    K = 107
    L = 108
    M = 109
    N = 110
    O = 111
    P = 112
    R = 114
    S = 115
    T = 116
    V = 118
    W = 119
    X = 120
    Y = 121
    BACKSPACE = 65288
    ENTER = 65293
    ESC = 65307
    LEFT = 65361
    UP = 65362
    RIGHT = 65363
    DOWN = 65364
    SHIFT_L = 65505
    SHIFT_R = 65506


class WindowAction(Enum):
    Close = auto()
    CycleColors = auto()
