"""States shared by game progression and its screen renderer."""

from enum import IntEnum, auto


class GUIStateEnum(IntEnum):
    Home = auto()
    Instruction = auto()
    Ranking = auto()
    Playing = auto()
    Pause = auto()
    GameOver = auto()
    Stage_Clear = auto()
    All_Clear = auto()
    Confirm_Clear = auto()
