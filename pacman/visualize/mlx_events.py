"""Event numbers and selection masks used by MLX window hooks."""

from enum import IntEnum, IntFlag


class MlxEvent(IntEnum):
    """X11 event numbers passed to mlx_hook."""

    KEY_PRESS = 2
    KEY_RELEASE = 3
    WINDOW_CLOSE = 33


class MlxEventMask(IntFlag):
    """X11 event masks passed to mlx_hook."""

    NONE = 0
    KEY_PRESS = 1 << 0
    KEY_RELEASE = 1 << 1
