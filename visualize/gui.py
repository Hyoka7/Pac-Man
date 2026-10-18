from enum import IntEnum

from mlx import Mlx


class GUIStateEnum(IntEnum):
    Home = 1
    Playing = 2
    Pause = 3
    GameOver = 4


class GUI:
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

    def draw_score(
        self,
        m: Mlx,
        p: int,
        win: int,
        x: int,
        y: int,
        score: int,
    ):
        m.mlx_string_put(
            p,
            win,
            x,
            y,
            0xFFFFFFFF,
            f"Score: {score}",
        )
