from enum import IntEnum, auto

from .highscore import ScoreEntry
from .text import TextRenderer
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
    RANKING_PAGE_SIZE = 10
    FONT_SIZE = 20
    LINE_SPACING = 28
    TEXT_COLOR = (255, 255, 255)
    ACCENT_COLOR = (255, 216, 74)
    BACKGROUND_COLOR = (8, 13, 28)
    PANEL_COLOR = (16, 25, 48)
    BORDER_COLOR = (73, 194, 221)
    BAR_TRACK_COLOR = (31, 44, 67)
    BAR_COLOR = (255, 216, 74)

    def __init__(self) -> None:
        self.text_renderer = TextRenderer()

    def _put_string_center(
        self,
        canvas: VisualizerUtils,
        window_width: int,
        y: int,
        text: str,
        color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        width, _ = self.text_renderer.text_size(text, self.FONT_SIZE)
        self.text_renderer.draw_text(canvas, (window_width - width) // 2, y, text, color, self.FONT_SIZE)

    def _put_lines_center(
        self, canvas: VisualizerUtils, width: int, height: int,
        lines: list[str],
        colors: dict[int, tuple[int, int, int]] | None = None,
    ) -> None:
        """Center a text block using Pillow's actual glyph dimensions."""
        if not lines:
            return
        last_height = self.text_renderer.text_size(lines[-1], self.FONT_SIZE)[1]
        top = self._block_top(height, len(lines), last_height)
        line_colors = colors if colors is not None else {}
        for row, text in enumerate(lines):
            if text:
                self._put_string_center(
                    canvas, width, top + row * self.LINE_SPACING, text,
                    line_colors.get(row, self.TEXT_COLOR),
                )

    def _block_top(self, height: int, line_count: int, last_height: int = 20) -> int:
        block_height = (line_count - 1) * self.LINE_SPACING + last_height
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
        canvas: VisualizerUtils,
        width: int,
        height: int,
        scores: list[ScoreEntry],
        focusing: int,
    ) -> None:
        lines, menu_start = self._home_content(scores, focusing)
        self._put_lines_center(
            canvas,
            width,
            height,
            lines,
            {
                0: self.ACCENT_COLOR,
                menu_start + focusing: self.ACCENT_COLOR,
            },
        )

    def _home_content(
        self, scores: list[ScoreEntry], focusing: int,
    ) -> tuple[list[str], int]:
        """Build the home title, menu and controls."""
        menu = [
            "Start",
            "Instruction",
            "Ranking",
        ]
        menu = [
            ("> " if index == focusing else "  ") + text
            for index, text in enumerate(menu)
        ]
        lines = ["PAC-MAN", ""]
        menu_start = len(lines)
        lines.extend([*menu, "", "Up/Down: Select  Enter: OK"])
        return lines, menu_start

    def ranking(
        self, canvas: VisualizerUtils, width: int, height: int,
        scores: list[ScoreEntry], page: int = 0,
    ) -> None:
        pages = max(1, (len(scores) + self.RANKING_PAGE_SIZE - 1) // self.RANKING_PAGE_SIZE)
        page = max(0, min(page, pages - 1))
        start = page * self.RANKING_PAGE_SIZE
        entries = scores[start:start+self.RANKING_PAGE_SIZE]
        footer = f"Left/Right: Page {page+1}/{pages}  Enter: Home"
        lines = [
            "Highscore Ranking", "", *([""] * len(entries) if entries else ["No scores yet"]),
            "", footer,
        ]
        self._put_lines_center(
            canvas, width, height, lines, {0: self.ACCENT_COLOR},
        )
        if not entries:
            return
        # Spaces cannot align columns in a proportional font. Position each cell.
        rows = [(f"{rank}.", item.name, str(item.score))
                for rank, item in enumerate(entries, start=start+1)]
        column_widths = [max(self.text_renderer.text_size(row[col], self.FONT_SIZE)[0] for row in rows)
                         for col in range(3)]
        gap = 20
        table_width = sum(column_widths) + gap * 2
        left = (width - table_width) // 2
        top = self._block_top(height, len(lines), self.text_renderer.text_size(footer, self.FONT_SIZE)[1])
        for index, row in enumerate(rows):
            x = left
            y = top + (index + 2) * self.LINE_SPACING
            for column, text in enumerate(row):
                cell_x = x
                if column != 1:
                    cell_x += column_widths[column] - self.text_renderer.text_size(text, self.FONT_SIZE)[0]
                self.text_renderer.draw_text(canvas, cell_x, y, text, self.TEXT_COLOR, self.FONT_SIZE)
                x += column_widths[column] + gap

    def gameover(
        self, canvas: VisualizerUtils, width: int, height: int,
        score: int, name: str,
    ) -> None:
        self._put_lines_center(
            canvas,
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
        self, canvas: VisualizerUtils, width: int, height: int,
        score: int, name: str,
    ) -> None:
        self._put_lines_center(
            canvas,
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
        self, canvas: VisualizerUtils, width: int, height: int,
    ) -> None:
        self._put_lines_center(canvas, width, height, [
            "Stage Clear!!", "Press any key to continue",
        ], {0: self.ACCENT_COLOR})

    def draw_stats(
        self,
        canvas: VisualizerUtils,
        x: int,
        y: int,
        level: int,
        score: int,
        lives: int,
        time: float,
        cheat_enabled: bool,
    ):
        text = f"Lv:{level} Score:{score} Life:{lives} Time:{time:.1f}"
        if cheat_enabled:
            text += " CHEAT ON"
        self.text_renderer.draw_text(canvas, x, y, text, self.TEXT_COLOR, self.FONT_SIZE)

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
        self, canvas: VisualizerUtils, width: int, height: int, time: float,
    ) -> None:
        self._put_string_center(
            canvas, width, height - 70, f"Invincible {time:.1f}",
            self.ACCENT_COLOR,
        )

    def pause(
        self, canvas: VisualizerUtils, width: int, height: int,
    ) -> None:
        self._put_lines_center(canvas, width, height, [
            "PAUSED", "P: Resume", "H: Back to home",
        ], {0: self.ACCENT_COLOR})

    def instruction(
        self, canvas: VisualizerUtils, width: int, height: int,
    ) -> None:
        self._put_lines_center(canvas, width, height, [
            "Arrow keys or WASD: Move", "P: Pause/Resume", "H: Home while paused",
            "Eat all pacgums to clear the stage", "Enter: Back to home",
        ])
