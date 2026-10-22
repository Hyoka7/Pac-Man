from enum import IntEnum, auto

from mlx import Mlx

from .highscore import ScoreEntry
from .visualizerutils import VisualizerUtils


class GUIStateEnum(IntEnum):
    Home = auto()
    Instruction = auto()
    Ranking = auto()
    Playing = auto()
    Pause = auto()
    GameOver = auto()
    Stage_Clear = auto()
    All_Clear = auto()


class GUI:
    CHAR_WIDTH = 10
    FONT_HEIGHT = 20
    LINE_SPACING = 28

    def _put_string_center(
        self,
        m: Mlx,
        p: int,
        win: int,
        window_width: int,
        y: int,
        text: str,
    ) -> None:
        text_width = len(text) * self.CHAR_WIDTH
        x_start = (window_width - text_width) // 2
        m.mlx_string_put(
            p,
            win,
            x_start,
            y,
            0xFFFFFFFF,
            text,
        )

    def _put_lines_center(
        self, m: Mlx, p: int, win: int, width: int, height: int,
        lines: list[str],
    ) -> None:
        """Center an ASCII text block, reserving spacing for blank lines."""
        if not lines:
            return
        block_height = (len(lines) - 1) * self.LINE_SPACING + self.FONT_HEIGHT
        top = (height - block_height) // 2
        for row, text in enumerate(lines):
            if text:
                self._put_string_center(
                    m, p, win, width, top + row * self.LINE_SPACING, text,
                )

    def background(
        self,
        canvas: VisualizerUtils,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        for pixel_y in range(y, y + height):
            for pixel_x in range(x, x + width):
                canvas.draw_pixel(pixel_x, pixel_y, (128, 128, 128))

    def home(
        self, m: Mlx, p: int, win: int, width: int, height: int,
        scores: list[ScoreEntry],
    ) -> None:
        ranking = [
            f"{rank:>2}. {item.name:<12} {item.score:>7}"
            for rank, item in enumerate(scores[:5], start=1)
        ]
        lines = [
            "Home Demo", "", *(ranking or ["No scores yet"]), "",
            "I: Instruction", "H: Highscore Ranking", "Enter: Game Start!",
        ]
        self._put_lines_center(m, p, win, width, height, lines)

    def ranking(
        self, m: Mlx, p: int, win: int, width: int, height: int,
        scores: list[ScoreEntry],
    ) -> None:
        ranking = [
            f"{rank:>2}. {item.name:<12} {item.score:>7}"
            for rank, item in enumerate(scores[:10], start=1)
        ]
        lines = [
            "Highscore Ranking", "", *(ranking or ["No scores yet"]), "",
            "Enter: Back to Home",
        ]
        self._put_lines_center(m, p, win, width, height, lines)

    def gameover(
        self, m: Mlx, p: int, win: int, width: int, height: int,
        score: int, name: str,
    ) -> None:
        self._put_lines_center(m, p, win, width, height, [
            "Game Over!", f"Score: {score}", f"Enter your name: {name}",
            "Enter: Save and return home",
        ])

    def all_clear(
        self, m: Mlx, p: int, win: int, width: int, height: int,
        score: int, name: str,
    ) -> None:
        self._put_lines_center(m, p, win, width, height, [
            "All Clear!! Congratulations!!", f"Score: {score}",
            f"Enter your name: {name}", "Enter: Save and return home",
        ])

    def stage_clear(
        self, m: Mlx, p: int, win: int, width: int, height: int,
    ) -> None:
        self._put_lines_center(m, p, win, width, height, [
            "Stage Clear!!", "Press any key to continue",
        ])

    def draw_stats(
        self,
        m: Mlx,
        p: int,
        win: int,
        x: int,
        y: int,
        level: int,
        score: int,
        lives: int,
        time: float,
        cheat_enabled: bool,
    ):
        # MLX queues a draw per character and presents after 64 commands.
        # Keep room for the game image and the power timer in the same frame.
        text = f"Lv:{level} Score:{score} Life:{lives} Time:{time:.1f}"
        if cheat_enabled:
            text += " CHEAT ON"
        m.mlx_string_put(p, win, x, y, 0xFFFFFFFF, text)

    def draw_invincible_bar(
        self,
        canvas: VisualizerUtils,
        x: int,
        y: int,
        width: int,
        height: int,
        remaining: float,
        max_time: float,
    ):
        for pixel_y in range(y, y + height):
            for pixel_x in range(x, x + width):
                canvas.draw_pixel(pixel_x, pixel_y, (128, 128, 128))
        remain_width = int(width * (remaining / max_time))
        left = x + (width - remain_width) // 2
        for pixel_y in range(y, y + height):
            for pixel_x in range(left, left + remain_width):
                canvas.draw_pixel(pixel_x, pixel_y, (255, 255, 0))

    def invinsible_time(
        self, m: Mlx, p: int, win: int, width: int, height: int, time: float,
    ) -> None:
        self._put_string_center(
            m, p, win, width, height - 70, f"Invincible {time:.1f}",
        )

    def pause(
        self, m: Mlx, p: int, win: int, width: int, height: int,
    ) -> None:
        self._put_lines_center(m, p, win, width, height, [
            "PAUSED", "P: Resume", "H: Back to home",
        ])

    def instruction(
        self, m: Mlx, p: int, win: int, width: int, height: int,
    ) -> None:
        self._put_lines_center(m, p, win, width, height, [
            "Arrow keys or WASD: Move", "P: Pause/Resume", "H: Home while paused",
            "Eat all pacgums to clear the stage", "Enter: Back to home",
        ])
