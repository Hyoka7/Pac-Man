"""Validated game settings loaded from the configuration file."""

from pydantic import BaseModel, Field

DEFAULT_LEVEL_SIZES: tuple[tuple[int, int], ...] = (
    (15, 15),
    (17, 15),
    (19, 17),
    (21, 17),
    (21, 19),
    (23, 19),
    (25, 21),
    (25, 23),
    (27, 25),
    (30, 27),
)
"""Maze (width, height) for each default level, growing from 15x15."""


class LevelConfig(BaseModel):
    """Maze size and time limit of one level."""

    width: int = Field(15, ge=15, le=30)
    height: int = Field(15, ge=15, le=30)
    max_time: float = Field(90.0, ge=90.0, allow_inf_nan=False)


def default_levels() -> list[LevelConfig]:
    """Return the ten default levels; time grows by 10 seconds per level.

    Returns:
        Ten levels from 15x15 to 30x27 with 90 to 180 seconds.
    """
    return [
        LevelConfig(width=width, height=height, max_time=90.0 + 10.0 * index)
        for index, (width, height) in enumerate(DEFAULT_LEVEL_SIZES)
    ]


class Config(BaseModel):
    """Game-wide settings; invalid fields are replaced by these defaults."""

    highscore_filename: str = Field("scores.json")
    lives: int = Field(3, ge=1)
    levels: list[LevelConfig] = Field(
        default_factory=default_levels, min_length=1
    )
    points_per_pacgum: int = Field(10, ge=1)
    points_per_super_pacgum: int = Field(50, ge=1)
    points_per_ghost: int = Field(200, ge=1)
    seed: int = Field(42, ge=1)
