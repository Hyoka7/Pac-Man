"""Run the game with a configuration file supplied on the command line."""

import sys

from mazegenerator import MazeGenerator

from pacman.parser import ConfigParser
from pacman.visualize import GameVisualizer


def main() -> int:
    try:
        if len(sys.argv) != 2:
            print(f"Usage: {sys.argv[0]} <config_file>", file=sys.stderr)
            return 1
        input_path = sys.argv[1]
        parser = ConfigParser(input_path)
        config = parser.parse_config()
        first_level = config.levels[0]
        generator = MazeGenerator(size=(first_level.width, first_level.height))
        generator.generate(seed=config.seed)
        GameVisualizer(generator, config).start_visualization()
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
