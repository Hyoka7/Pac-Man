import json
import sys
from pathlib import Path

from pydantic import BaseModel, ValidationError

from ..models import Config
from ..models.models import LevelConfig


class Parser:
    def __init__(self, config_path: Path | str) -> None:
        if not isinstance(config_path, Path):
            self.config_path = Path(config_path)
        else:
            self.config_path = config_path

    def parse(self) -> Config:
        """Read commented JSON and recover invalid settings with model defaults."""
        config_parts = []
        with self.config_path.open("r", encoding="utf-8") as f:
            for line in f:
                # Preserve line numbers for JSON syntax error messages.
                config_parts.append("\n" if line.lstrip().startswith("#") else line)
        combined_config = "".join(config_parts)
        json_parsed_config = json.loads(combined_config)
        if not isinstance(json_parsed_config, dict):
            raise ValueError("The configuration must be a JSON object")
        levels = json_parsed_config.get("levels")
        if isinstance(levels, list) and levels:
            json_parsed_config["levels"] = [
                self._with_defaults(LevelConfig, level, f"levels[{index}]")
                for index, level in enumerate(levels)
            ]
        return self._with_defaults(Config, json_parsed_config, "config")

    @staticmethod
    def _with_defaults[T: BaseModel](
        model: type[T], values: object, location: str
    ) -> T:
        """Keep valid fields and replace missing or invalid fields independently."""
        if not isinstance(values, dict):
            print(f"Warning: {location}: expected an object; using defaults", file=sys.stderr)
            return model()
        corrected = values.copy()
        for name, field in model.model_fields.items():
            if name not in corrected:
                default = field.get_default(call_default_factory=True)
                corrected[name] = default
                print(
                    f"Warning: {location}.{name}: missing; using {default!r}",
                    file=sys.stderr,
                )
        try:
            return model.model_validate(corrected)
        except ValidationError as err:
            for error in err.errors():
                name = str(error["loc"][0])
                default = model.model_fields[name].get_default(call_default_factory=True)
                corrected[name] = default
                print(
                    f"Warning: {location}.{name}: {error['msg']}; using {default!r}",
                    file=sys.stderr,
                )
            return model.model_validate(corrected)
