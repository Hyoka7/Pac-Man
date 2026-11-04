from pydantic import BaseModel, Field


class LevelConfig(BaseModel):
    width: int = Field(15, ge=15, le=30)
    height: int = Field(15, ge=15, le=30)
    max_time: float = Field(90.0, ge=90.0, allow_inf_nan=False)


class Config(BaseModel):
    highscore_filename: str = Field("scores.json")
    lives: int = Field(3, ge=1)
    levels: list[LevelConfig] = Field(
        default_factory=lambda: [LevelConfig.model_validate({})], min_length=1
    )
    points_per_pacgum: int = Field(10, ge=1)
    points_per_super_pacgum: int = Field(50, ge=1)
    points_per_ghost: int = Field(200, ge=1)
    seed: int = Field(42, ge=1)
