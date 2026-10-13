from pydantic import BaseModel, Field


class Config(BaseModel):
    highscore_filename: str
    level: list[int]
    width: list[int]
    height: list[int]
    lives: int = Field(3, ge=1)
    pacgum: int = Field(42, ge=1)
    points_per_pacgum: int = Field(10, ge=1)
    points_per_super_pacgum: int = Field(50, ge=1)
    points_per_ghost: int = Field(200, ge=1)
    seed: int = Field(42, ge=1)
    level_max_type: int = Field(90, ge=1)
