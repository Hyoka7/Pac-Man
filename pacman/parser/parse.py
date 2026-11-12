import json
import sys
from pathlib import Path

from pydantic import ValidationError

from ..models import Config
from ..models.models import LevelConfig


class ConfigParser:
    """Read a commented JSON configuration into a validated Config."""

    def __init__(self, config_path: Path | str) -> None:
        """Remember the configuration file path.

        Args:
            config_path: Path to the JSON configuration file.
        """
        if not isinstance(config_path, Path):
            self.config_path = Path(config_path)
        else:
            self.config_path = config_path

    def parse_config(self) -> Config:
        """Read commented JSON, replacing invalid settings with defaults.

        Returns:
            The validated configuration.

        Raises:
            OSError: If the file cannot be read.
            ValueError: If the file is not valid UTF-8 JSON.
            TypeError: If the JSON root is not an object.
        """
        config_parts = []
        with self.config_path.open("r", encoding="utf-8") as f:
            for line in f:
                # Preserve line numbers for JSON syntax error messages.
                config_parts.append(
                    "\n" if line.strip().startswith("#") else line
                )
        combined_config = "".join(config_parts)
        json_parsed_config = json.loads(combined_config)
        if not isinstance(json_parsed_config, dict):
            raise TypeError("The configuration must be a JSON object")
        levels = json_parsed_config.get("levels")
        if isinstance(levels, list) and levels:
            json_parsed_config["levels"] = [
                self._validate_level(level, index)
                for index, level in enumerate(levels)
            ]
        return self._validate_config(json_parsed_config)

    @staticmethod
    def _validate_config(values: dict[str, object]) -> Config:
        """Validate game settings, replacing only missing or invalid fields.

        Args:
            values: Parsed top-level JSON object.

        Returns:
            A Config with invalid or missing fields set to defaults.
        """
        corrected = values.copy()
        for name, field in Config.model_fields.items():
            if name not in corrected:
                default = field.get_default(call_default_factory=True)
                corrected[name] = default
                print(
                    f"Warning: config.{name}: missing; using {default!r}",
                    file=sys.stderr,
                )
        try:
            return Config.model_validate(corrected)
        except ValidationError as err:
            for error in err.errors():
                name = str(error["loc"][0])
                default = Config.model_fields[name].get_default(
                    call_default_factory=True
                )
                corrected[name] = default
                print(
                    f"Warning: config.{name}: {error['msg']}; "
                    f"using {default!r}",
                    file=sys.stderr,
                )
            return Config.model_validate(corrected)

    @staticmethod
    def _validate_level(values: object, index: int) -> LevelConfig:
        """Validate one level without changing settings in other levels.

        Args:
            values: Parsed level entry.
            index: Position of the level, used in warnings.

        Returns:
            A LevelConfig with invalid or missing fields set to defaults.
        """
        location = f"levels[{index}]"
        if not isinstance(values, dict):
            print(
                f"Warning: {location}: expected an object; using defaults",
                file=sys.stderr,
            )
            return LevelConfig.model_validate({})
        for name, field in LevelConfig.model_fields.items():
            if name not in values:
                default = field.get_default(call_default_factory=True)
                values[name] = default
                print(
                    f"Warning: {location}.{name}: missing; using {default!r}",
                    file=sys.stderr,
                )
        try:
            return LevelConfig.model_validate(values)
        except ValidationError as err:
            for error in err.errors():
                name = str(error["loc"][0])
                default = LevelConfig.model_fields[name].get_default(
                    call_default_factory=True
                )
                values[name] = default
                print(
                    f"Warning: {location}.{name}: {error['msg']}; "
                    f"using {default!r}",
                    file=sys.stderr,
                )
            return LevelConfig.model_validate(values)
