from enum import IntEnum

from mlx import Mlx

from .highscore import ScoreEntry
from .visualizerutils import VisualizerUtils


class GUIStateEnum(IntEnum):
    Home = 1
    Playing = 2
    Pause = 3
    GameOver = 4
    Stage_Clear = 5
    All_Clear = 6


class GUI:
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
        self,
        m: Mlx,
        p: int,
        win: int,
        width: int,
        height: int,
        scores: list[ScoreEntry],
    ) -> None:

        m.mlx_string_put(
            p,
            win,
            width // 2 - 45,
            height // 2,
            0xFFFFFFFF,
            "Home Demo",
        )
        for rank, item in enumerate(scores[:5], start=1):
            m.mlx_string_put(
                p,
                win,
                width // 2 - 45,
                height // 2 + rank * 20,
                0xFFFFFFFF,
                f"{rank}:{item.name} : {item.score}",
            )

    def gameover(
        self,
        m: Mlx,
        p: int,
        win: int,
        width: int,
        height: int,
        score: int,
        name: str,
    ) -> None:
        m.mlx_string_put(
            p,
            win,
            width // 2 - 45,
            height // 2,
            0xFFFFFFFF,
            f"Game Over! Enter Your name: {name}",
        )
        m.mlx_string_put(
            p,
            win,
            width // 2 - 45,
            height // 2 + 20,
            0xFFFFFFFF,
            f"Score: {score}",
        )

    def all_clear(
        self,
        m: Mlx,
        p: int,
        win: int,
        width: int,
        height: int,
        score: int,
        name: str,
    ) -> None:
        m.mlx_string_put(
            p,
            win,
            width // 2 - 45,
            height // 2,
            0xFFFFFFFF,
            f"All Clear!! Conguratulations!! Enter your name: {name}",
        )
        m.mlx_string_put(
            p,
            win,
            width // 2 - 45,
            height // 2 + 20,
            0xFFFFFFFF,
            f"Score: {score}",
        )

    def stage_clear(
        self,
        m: Mlx,
        p: int,
        win: int,
        width: int,
        height: int,
    ) -> None:
        m.mlx_string_put(
            p,
            win,
            width // 2 - 45,
            height // 2,
            0xFFFFFFFF,
            "Stage Clear!!",
        )

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
    ):
        m.mlx_string_put(
            p,
            win,
            x,
            y,
            0xFFFFFFFF,
            f"Level: {level} Score: {score} Life: {lives} Remaining Time: {time:.1f}",
        )

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
        self,
        m: Mlx,
        p: int,
        win: int,
        width: int,
        height: int,
        time: float,
    ) -> None:
        m.mlx_string_put(
            p, win, width // 2 - 70, height - 70, 0xFFFFFFFF, f"Invincible {time:.1f}"
        )

    def pause(
        self,
        m: Mlx,
        p: int,
        win: int,
        width: int,
        height: int,
    ) -> None:
        m.mlx_string_put(
            p,
            win,
            width // 2 - 18,
            height // 2,
            0xFFFFFFFF,
            "PAUSED",
        )
        m.mlx_string_put(
            p,
            win,
            width // 2 - 18,
            height // 2 + 20,
            0xFFFFFFFF,
            "P: Resume",
        )
        m.mlx_string_put(
            p,
            win,
            width // 2 - 18,
            height // 2 + 40,
            0xFFFFFFFF,
            "H: Back to home",
        )