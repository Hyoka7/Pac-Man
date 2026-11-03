"""Run the game with the current development configuration."""

from mazegenerator import MazeGenerator

from pacman.models import Config
from pacman.models.models import LevelConfig
from pacman.visualize import MazeVisualizer


def main() -> None:
    config = Config(
        highscore_filename="scores.json",
        levels=[
            LevelConfig(width=15, height=15),
            LevelConfig(width=25, height=15),
            LevelConfig(width=15, height=25),
            *[LevelConfig(width=15, height=15) for _ in range(7)],
        ],
        lives=3,
    )

    first_level = config.levels[0]
    m = MazeGenerator(size=(first_level.width, first_level.height))
    m.generate(seed=config.seed)
    MazeVisualizer(m.maze, m, config).run()


if __name__ == "__main__":
    main()
