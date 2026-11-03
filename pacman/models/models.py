from pydantic import BaseModel, Field


class LevelConfig(BaseModel):
    width: int
    height: int
    max_time: float = Field(90.0)


class Config(BaseModel):
    highscore_filename: str
    levels: list[LevelConfig]
    lives: int = Field(3, ge=1)
    points_per_pacgum: int = Field(10, ge=1)
    points_per_super_pacgum: int = Field(50, ge=1)
    points_per_ghost: int = Field(200, ge=1)
    seed: int = Field(42, ge=1)
