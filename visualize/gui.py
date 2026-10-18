from enum import IntEnum

from mlx import Mlx

from .visualizerutils import VisualizerUtils


class GUIStateEnum(IntEnum):
    Home = 1
    Playing = 2
    Pause = 3
    GameOver = 4
    Clear = 5


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
    ) -> None:

        m.mlx_string_put(
            p,
            win,
            width // 2 - 45,
            height // 2,
            0xFFFFFFFF,
            "Home Demo",
        )

    def gameover(
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
            "Game Over!",
        )

    def clear(
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
            "Clear!!",
        )

    def draw_stats(
        self,
        m: Mlx,
        p: int,
        win: int,
        x: int,
        y: int,
        score: int,
        lives: int,
    ):
        m.mlx_string_put(
            p,
            win,
            x,
            y,
            0xFFFFFFFF,
            f"Score: {score} Life: {lives}",
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