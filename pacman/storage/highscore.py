import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Self

from pydantic import BaseModel, Field, ValidationError


class ScoreEntry(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=10,
        pattern=r"^[A-Za-z0-9 ]+$",
    )
    score: int = Field(..., ge=0)


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

    def clear(self) -> None:
        self.scores.scores.clear()
        self.save()

    def save(self) -> None:
        temporary_path: Path | None = None
        try:
            json_data = self.scores.model_dump_json(indent=2)
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.save_path.parent,
                prefix=f".{self.save_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as f:
                temporary_path = Path(f.name)
                f.write(json_data)
            os.replace(temporary_path, self.save_path)
        except OSError as err:
            print(f"Highscore data save failed: {err}")
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError as err:
                    print(f"Highscore temporary file cleanup failed: {err}")

    def load(self) -> None:
        if not self.save_path.exists():
            return
        try:
            with self.save_path.open("r", encoding="utf-8") as f:
                json_data = f.read()
            data = HighscoreData.model_validate_json(json_data)
            self.scores = data
            self._sort_scores()
        except ValidationError as err:
            print(f"Invalid JSON File loaded: {err.errors()[0]['msg']}")
        except (OSError, ValueError) as err:
            print(f"Invalid JSON File loaded: {err}")

    def _sort_scores(self) -> None:
        self.scores.scores.sort(
            key=lambda entry: entry.score,
            reverse=True,
        )
        self.scores.scores = self.scores.scores[:10]

    def _add_new_entry(self, entry: ScoreEntry) -> None:
        self.scores += entry
        self._sort_scores()
