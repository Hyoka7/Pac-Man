from pathlib import Path
from typing import Self

from pydantic import BaseModel


class ScoreEntry(BaseModel):
    name: str
    score: int


class HighscoreData(BaseModel):
    scores: list[ScoreEntry]

    def __iadd__(self, item: ScoreEntry) -> Self:
        self.scores.append(item)
        return self


class HighscoreManager:
    def __init__(self, save_path: str = "scores.json") -> None:
        self.scores: HighscoreData = HighscoreData(scores=[])
        self.save_path: Path = Path(save_path)
        self.load()

    def __iadd__(self, entry: ScoreEntry) -> Self:
        self._add_new_entry(entry)
        self.save()
        return self

    def save(self) -> None:
        json_data = self.scores.model_dump_json(indent=2)
        with self.save_path.open("w", encoding="utf-8") as f:
            f.write(json_data)

    def load(self) -> None:
        if not self.save_path.exists():
            return
        with self.save_path.open("r", encoding="utf-8") as f:
            json_data = f.read()
        data = HighscoreData.model_validate_json(json_data)
        self.scores = data

    def _add_new_entry(self, entry: ScoreEntry):
        self.scores += entry
        self.scores.scores.sort(
            key=lambda entry: entry.score,
            reverse=True,
        )
