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
    TEXT_COLOR = 0xFFFFFFFF
    ACCENT_COLOR = 0xFF4AD8FF  # MLX 2 text colors use ABGR byte order.
    BACKGROUND_COLOR = (8, 13, 28)
    PANEL_COLOR = (16, 25, 48)
    BORDER_COLOR = (73, 194, 221)
    BAR_TRACK_COLOR = (31, 44, 67)
    BAR_COLOR = (255, 216, 74)

    def _put_string_center(
        self,
        m: Mlx,
        p: int,
        win: int,
        window_width: int,
        y: int,
        text: str,
        color: int = 0xFFFFFFFF,
    ) -> None:
        text_width = len(text) * self.CHAR_WIDTH
        x_start = (window_width - text_width) // 2
        m.mlx_string_put(
            p,
            win,
            x_start,
            y,
            color,
            text,
        )

    def _put_lines_center(
        self, m: Mlx, p: int, win: int, width: int, height: int,
        lines: list[str],
        colors: dict[int, int] | None = None,
    ) -> None:
        """Center an ASCII text block, reserving spacing for blank lines."""
        if not lines:
            return
        top = self._block_top(height, len(lines))
        line_colors = colors if colors is not None else {}
        # Long static screens cross MLX's automatic 64-command flush. Complete
        # each row explicitly to keep every batch visible on this backend.
        wait_for_rows = 1 + sum(map(len, lines)) >= 64
        for row, text in enumerate(lines):
            if text:
                self._put_string_center(
                    m, p, win, width, top + row * self.LINE_SPACING, text,
                    line_colors.get(row, self.TEXT_COLOR),
                )
                if wait_for_rows:
                    m.mlx_sync(p, 3, win)  # MLX_SYNC_WIN_COMPLETED

    def _block_top(self, height: int, line_count: int) -> int:
        block_height = (line_count - 1) * self.LINE_SPACING + self.FONT_HEIGHT
        return (height - block_height) // 2

    def draw_backdrop(
        self, canvas: VisualizerUtils, state: GUIStateEnum,
    ) -> None:
        """Draw a static screen's navy backdrop and centered bordered panel."""
        if state in (GUIStateEnum.Playing, GUIStateEnum.Pause):
            return
        canvas.fill_rect(0, 0, canvas.width, canvas.height, self.BACKGROUND_COLOR)
        panel_heights = {
            GUIStateEnum.Home: 420,
            GUIStateEnum.Ranking: 448,
            GUIStateEnum.Instruction: 196,
            GUIStateEnum.GameOver: 168,
            GUIStateEnum.All_Clear: 168,
            GUIStateEnum.Stage_Clear: 112,
        }
        width = min(620, max(0, canvas.width - 48))
        height = min(panel_heights[state], max(0, canvas.height - 48))
        self.background(
            canvas, (canvas.width - width) // 2,
            (canvas.height - height) // 2, width, height,
        )

    def background(
        self,
        canvas: VisualizerUtils,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        if width <= 0 or height <= 0:
            return
        border = min(2, width, height)
        canvas.fill_rect(x, y, width, height, self.PANEL_COLOR)
        canvas.fill_rect(x, y, width, border, self.BORDER_COLOR)
        canvas.fill_rect(x, y + height - border, width, border, self.BORDER_COLOR)
        canvas.fill_rect(x, y, border, height, self.BORDER_COLOR)
        canvas.fill_rect(x + width - border, y, border, height, self.BORDER_COLOR)

    def home(
        self,
        m: Mlx,
        p: int,
        win: int,
        width: int,
        height: int,
        scores: list[ScoreEntry],
        focusing: int,
    ) -> None:
        lines, menu_start = self._home_content(scores, focusing)
        self._put_lines_center(
            m, p, win, width, height, lines,
            {0: self.ACCENT_COLOR, menu_start + focusing: self.ACCENT_COLOR},
        )

    def _home_content(
        self, scores: list[ScoreEntry], focusing: int,
    ) -> tuple[list[str], int]:
        """Share the home rows between full and menu-only rendering."""
        ranking = [
            f"{rank:>2}. {item.name:<12} {item.score:>7}"
            for rank, item in enumerate(scores[:5], start=1)
        ]
        menu = [
            "Game Start", "I: Instruction", "H: Highscore Ranking",
        ]
        menu = [
            ("> " if index == focusing else "  ") + text
            for index, text in enumerate(menu)
        ]
        lines = [
            "PAC-MAN", "", *(ranking or ["No scores yet"]), "",
        ]
        menu_start = len(lines)
        lines.extend([*menu, "", "Up/Down: Select  Enter: OK"])
        return lines, menu_start

    def home_menu(
        self, m: Mlx, p: int, win: int, width: int, height: int,
        scores: list[ScoreEntry], focusing: int,
    ) -> None:
        """Redraw only the three menu rows after a selection change."""
        lines, menu_start = self._home_content(scores, focusing)
        top = self._block_top(height, len(lines))
        for index, text in enumerate(lines[menu_start:menu_start+3]):
            color = self.ACCENT_COLOR if index == focusing else self.TEXT_COLOR
            self._put_string_center(
                m, p, win, width,
                top + (menu_start + index) * self.LINE_SPACING, text, color,
            )

    def draw_home_menu_background(
        self, canvas: VisualizerUtils, scores: list[ScoreEntry],
    ) -> None:
        """Erase the menu rows without touching the title, scores or border."""
        lines, menu_start = self._home_content(scores, 0)
        text_width = max(len(text) for text in lines[menu_start:menu_start+3])
        width = min(text_width * self.CHAR_WIDTH + 16, 616,
                    max(0, canvas.width - 52))
        top = self._block_top(canvas.height, len(lines))
        canvas.fill_rect(
            (canvas.width - width) // 2, top + menu_start * self.LINE_SPACING,
            width, 2 * self.LINE_SPACING + self.FONT_HEIGHT, self.PANEL_COLOR,
        )

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
        self._put_lines_center(
            m, p, win, width, height, lines, {0: self.ACCENT_COLOR},
        )

    def gameover(
        self, m: Mlx, p: int, win: int, width: int, height: int,
        score: int, name: str,
    ) -> None:
        self._put_lines_center(
            m,
            p,
            win,
            width,
            height,
            [
                "Game Over!",
                f"Score: {score}",
                f"Enter Name: {name}",
                "Enter: Save",
            ],
            {0: self.ACCENT_COLOR},
        )

    def all_clear(
        self, m: Mlx, p: int, win: int, width: int, height: int,
        score: int, name: str,
    ) -> None:
        self._put_lines_center(
            m,
            p,
            win,
            width,
            height,
            [
                "All Clear!",
                f"Score: {score}",
                f"Enter Name: {name}",
                "Enter: Save",
            ],
            {0: self.ACCENT_COLOR},
        )

    def stage_clear(
        self, m: Mlx, p: int, win: int, width: int, height: int,
    ) -> None:
        self._put_lines_center(m, p, win, width, height, [
            "Stage Clear!!", "Press any key to continue",
        ], {0: self.ACCENT_COLOR})

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
        canvas.fill_rect(x, y, width, height, self.BAR_TRACK_COLOR)
        fraction = max(0.0, min(1.0, remaining / max_time)) if max_time > 0 else 0.0
        remain_width = int(width * fraction)
        left = x + (width - remain_width) // 2
        canvas.fill_rect(left, y, remain_width, height, self.BAR_COLOR)

    def invinsible_time(
        self, m: Mlx, p: int, win: int, width: int, height: int, time: float,
    ) -> None:
        self._put_string_center(
            m, p, win, width, height - 70, f"Invincible {time:.1f}",
            self.ACCENT_COLOR,
        )

    def pause(
        self, m: Mlx, p: int, win: int, width: int, height: int,
    ) -> None:
        self._put_lines_center(m, p, win, width, height, [
            "PAUSED", "P: Resume", "H: Back to home",
        ], {0: self.ACCENT_COLOR})

    def instruction(
        self, m: Mlx, p: int, win: int, width: int, height: int,
    ) -> None:
        self._put_lines_center(m, p, win, width, height, [
            "Arrow keys or WASD: Move", "P: Pause/Resume", "H: Home while paused",
            "Eat all pacgums to clear the stage", "Enter: Back to home",
        ])
