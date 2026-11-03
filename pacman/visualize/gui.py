from collections.abc import Sequence

from pacman.game.state import GameState
from pacman.storage.highscore import ScoreEntry
from pacman.visualize.image_renderer import ImageRenderer
from pacman.visualize.sprites import ghost_image, player_image
from pacman.visualize.visualizerutils import VisualizerUtils


class GUI:
    RANKING_LIMIT = 10
    TEXT_COLOR = (255, 255, 255)
    ACCENT_COLOR = (255, 216, 74)
    BACKGROUND_COLOR = (8, 13, 28)
    PANEL_COLOR = (16, 25, 48)
    BORDER_COLOR = (73, 194, 221)
    BAR_TRACK_COLOR = (31, 44, 67)
    BAR_COLOR = (255, 216, 74)
    INSTRUCTION_LINES = (
        "Arrow keys or WASD: Move",
        "P: Pause/Resume",
        "H: Home while paused",
        "Eat all pacgums to clear the stage",
        "Enter: Back to home",
    )

    def __init__(self) -> None:
        self.text_renderer = ImageRenderer()

    def update_layout(self, width: int, height: int) -> None:
        side = min(width, height)
        self.font_size = max(1, round(side / 30))
        while self.font_size > 1:
            text_width = self._max_text_width(self.INSTRUCTION_LINES)
            if text_width + 4 * self.font_size <= width:
                break
            self.font_size -= 1
        self.text_height = self.text_renderer.text_size("Ag", self.font_size)[1]
        self.padding = self.font_size
        self.text_gap = max(1, round(self.font_size / 4))
        self.line_spacing = max(round(self.font_size * 1.4), self.text_height + 1)
        self.border_width = max(1, round(self.font_size / 10))
        self.hud_x = self.padding
        self.hud_y = round(self.font_size * 0.75)
        self.bar_width = min(self.font_size * 10, max(0, width - 2 * self.padding))
        self.bar_height = max(1, round(self.font_size / 2))
        self.bar_y = max(0, height - self.padding - self.bar_height)
        footer_height = (
            self.padding + self.bar_height + self.text_gap + self.text_height
        )
        self.maze_margin = max(
            self.hud_y + self.text_height + self.padding,
            footer_height + self.padding,
        )

    def _put_string_center(
        self,
        canvas: VisualizerUtils,
        window_width: int,
        y: int,
        text: str,
        color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        width, _ = self.text_renderer.text_size(text, self.font_size)
        self.text_renderer.draw_text(
            canvas, (window_width - width) // 2, y, text, color, self.font_size
        )

    def _put_lines_center(
        self,
        canvas: VisualizerUtils,
        width: int,
        height: int,
        lines: Sequence[str],
        colors: dict[int, tuple[int, int, int]] | None = None,
    ) -> None:
        """Center a text block using Pillow's actual glyph dimensions."""
        if not lines:
            return
        last_height = self.text_renderer.text_size(lines[-1], self.font_size)[1]
        top = self._block_top(height, len(lines), last_height)
        line_colors = colors if colors is not None else {}
        for row, text in enumerate(lines):
            if text:
                self._put_string_center(
                    canvas,
                    width,
                    top + row * self.line_spacing,
                    text,
                    line_colors.get(row, self.TEXT_COLOR),
                )

    def _block_height(self, line_count: int, last_height: int | None = None) -> int:
        if line_count <= 0:
            return 0
        return (line_count - 1) * self.line_spacing + (
            self.text_height if last_height is None else last_height
        )

    def _block_top(
        self,
        height: int,
        line_count: int,
        last_height: int | None = None,
    ) -> int:
        return (height - self._block_height(line_count, last_height)) // 2

    def _draw_panel_lines(
        self,
        canvas: VisualizerUtils,
        lines: Sequence[str],
    ) -> None:
        panel_width = min(
            self._max_text_width(lines) + 2 * self.padding,
            max(0, canvas.width - 2 * self.padding),
        )
        panel_height = min(
            self._block_height(len(lines)) + 2 * self.padding,
            max(0, canvas.height - 2 * self.padding),
        )
        panel_x = (canvas.width - panel_width) // 2
        panel_y = (canvas.height - panel_height) // 2
        self.background(
            canvas,
            panel_x,
            panel_y,
            panel_width,
            panel_height,
        )

    def draw_backdrop(
        self,
        canvas: VisualizerUtils,
        state: GameState,
    ) -> None:
        """Draw a static screen's navy backdrop and centered bordered panel."""
        if state in (
            GameState.Playing,
            GameState.Pause,
            GameState.Ready,
        ):
            return
        canvas.fill_rect(0, 0, canvas.width, canvas.height, self.BACKGROUND_COLOR)
        panel_heights = {
            GameState.Home: self.line_spacing * 15,
            GameState.Ranking: self.line_spacing * 16,
            GameState.Confirm_Clear: self.line_spacing * 5,
            GameState.Instruction: self.line_spacing * 7,
            GameState.GameOver: self.line_spacing * 6,
            GameState.All_Clear: self.line_spacing * 6,
            GameState.Stage_Clear: self.line_spacing * 4,
        }
        width = min(
            max(
                round(canvas.width * 0.8),
                self._max_text_width(self.INSTRUCTION_LINES) + 2 * self.padding,
            ),
            max(0, canvas.width - 2 * self.padding),
        )
        height = min(panel_heights[state], max(0, canvas.height - 2 * self.padding))
        self.background(
            canvas,
            (canvas.width - width) // 2,
            (canvas.height - height) // 2,
            width,
            height,
        )

    def _max_text_width(self, lines: Sequence[str]) -> int:
        return max(
            (self.text_renderer.text_size(line, self.font_size)[0] for line in lines),
            default=0,
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
        border = min(self.border_width, width, height)
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
        lines, menu_start = self._home_content()
        title_size = self.font_size * 2
        image = self.text_renderer._text_image(
            lines[0],
            self.ACCENT_COLOR,
            title_size,
        )
        image_range = image.getbbox()
        if image_range is not None:
            left, _, right, _ = image_range
            image = image.crop((left, 0, right, image.height))
            x = (width - image.width) // 2
            y = self._block_top(height, len(lines)) - image.height // 2
            self.text_renderer.draw_image(canvas, x, y, image)
        lines[0] = ""
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
        block_top = self._block_top(height, len(lines))
        self._draw_home_characters(canvas, width, block_top + self.line_spacing)
        target_char = lines[menu_start + focusing]
        target_width, _ = self.text_renderer.text_size(target_char, self.font_size)
        focus_width, _ = self.text_renderer.text_size(">", self.font_size)
        x = (width - target_width) // 2 - focus_width - self.text_gap
        y = block_top + (menu_start + focusing) * self.line_spacing
        self.text_renderer.draw_text(
            canvas,
            x,
            y,
            ">",
            self.ACCENT_COLOR,
            self.font_size,
        )

    def ready(
        self,
        canvas: VisualizerUtils,
        width: int,
        height: int,
    ) -> None:
        ready_lines = ["READY?", "Press any key to start"]
        self._draw_panel_lines(
            canvas,
            ready_lines,
        )
        self._put_lines_center(
            canvas,
            width,
            height,
            ready_lines,
            {0: self.ACCENT_COLOR},
        )

    def _home_content(
        self,
    ) -> tuple[list[str], int]:
        """Build the home title, menu and controls."""
        menu = [
            "Start",
            "Instruction",
            "Ranking",
            "Exit",
        ]
        lines = ["PAC-MAN", ""]
        menu_start = len(lines)
        lines.extend([*menu, "", "Up/Down: Select  Enter: OK"])
        return lines, menu_start

    def cheat_info(
        self,
        canvas: VisualizerUtils,
        width: int,
        height: int,
    ) -> None:
        cheat_lines = [
            "N: Next Level",
            "F: Ghost Freeze",
            "H: Wallhack",
            "K: No Death",
            "V: Speed Up",
            "L: Life +1",
            "T: Time +10",
            "X: Score x10",
        ]
        text_size = max(1, self.font_size // 2)
        text_height = self.text_renderer.text_size(cheat_lines[0], text_size)[1]
        cheat_spacing = text_height + self.text_gap
        base_y = height - self.padding - 4 * cheat_spacing
        right_width = max(
            self.text_renderer.text_size(line, text_size)[0]
            for line in cheat_lines[1::2]
        )
        for index, item in enumerate(cheat_lines):
            row = index // 2
            col = index % 2
            text_x = self.padding if col == 0 else width - self.padding - right_width
            text_y = base_y + row * cheat_spacing
            self.text_renderer.draw_text(canvas, text_x, text_y, item, size=text_size)

    def ranking(
        self,
        canvas: VisualizerUtils,
        width: int,
        height: int,
        scores: list[ScoreEntry],
    ) -> None:
        entries = scores[: self.RANKING_LIMIT]
        footer = "C: Clear  Enter: Home"
        lines = [
            "Highscore Ranking",
            "",
            *([""] * len(entries) if entries else ["No scores yet"]),
            "",
            footer,
        ]
        self._put_lines_center(
            canvas,
            width,
            height,
            lines,
            {0: self.ACCENT_COLOR},
        )
        if not entries:
            return
        # Spaces cannot align columns in a proportional font. Position each cell.
        rows = [
            (f"{rank}.", item.name, str(item.score))
            for rank, item in enumerate(entries, start=1)
        ]
        column_widths = [
            max(
                self.text_renderer.text_size(row[col], self.font_size)[0]
                for row in rows
            )
            for col in range(3)
        ]
        gap = self.font_size
        table_width = sum(column_widths) + gap * 2
        left = (width - table_width) // 2
        top = self._block_top(
            height, len(lines), self.text_renderer.text_size(footer, self.font_size)[1]
        )
        for index, row in enumerate(rows):
            x = left
            y = top + (index + 2) * self.line_spacing
            for column, text in enumerate(row):
                cell_x = x
                if column != 1:
                    cell_x += (
                        column_widths[column]
                        - self.text_renderer.text_size(text, self.font_size)[0]
                    )
                self.text_renderer.draw_text(
                    canvas, cell_x, y, text, self.TEXT_COLOR, self.font_size
                )
                x += column_widths[column] + gap

    def _draw_home_characters(
        self,
        canvas: VisualizerUtils,
        width: int,
        y: int,
    ) -> None:
        pacman_img = player_image(self.font_size / 2, "E", 10)
        ghost_colors = (
            (255, 0, 0),
            (128, 128, 128),
            (0, 255, 255),
            (0, 0, 255),
        )
        imgs = [pacman_img]
        radius = self.font_size / 2
        imgs.extend(ghost_image(radius, color, "E") for color in ghost_colors)
        total_width = sum(img.width for img in imgs) + self.text_gap * (len(imgs) - 1)
        x = (width - total_width) // 2
        for img in imgs:
            self.text_renderer.draw_image(
                canvas,
                x,
                y,
                img,
            )
            x += img.width + self.text_gap

    def gameover(
        self,
        canvas: VisualizerUtils,
        width: int,
        height: int,
        score: int,
        name: str,
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
        self,
        canvas: VisualizerUtils,
        width: int,
        height: int,
        score: int,
        name: str,
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
        self,
        canvas: VisualizerUtils,
        width: int,
        height: int,
    ) -> None:
        self._put_lines_center(
            canvas,
            width,
            height,
            [
                "Stage Clear!!",
                "Press any key to continue",
            ],
            {0: self.ACCENT_COLOR},
        )

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
        score_multiplier: int = 1,
    ) -> None:
        text = f"Lv:{level} Score:{score} Life:{lives} Time:{time:.1f}"
        if cheat_enabled:
            text += " CHEAT ON"
        if score_multiplier != 1:
            text += f" x{score_multiplier}"
        self.text_renderer.draw_numeric_text(
            canvas, x, y, text, self.TEXT_COLOR, self.font_size, slot="hud"
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
    ) -> None:
        canvas.fill_rect(x, y, width, height, self.BAR_TRACK_COLOR)
        fraction = max(0.0, min(1.0, remaining / max_time)) if max_time > 0 else 0.0
        remain_width = int(width * fraction)
        left = x + (width - remain_width) // 2
        canvas.fill_rect(left, y, remain_width, height, self.BAR_COLOR)

    def invincible_time(
        self,
        canvas: VisualizerUtils,
        width: int,
        bar_y: int,
        time: float,
    ) -> None:
        text = f"Invincible {time:.1f}"
        image = self.text_renderer.numeric_text_image(
            text,
            self.ACCENT_COLOR,
            self.font_size,
            slot="invincible",
        )
        x = (width - image.width) // 2
        y = bar_y - self.text_height - self.text_gap
        self.text_renderer.draw_numeric_text(
            canvas,
            x,
            y,
            text,
            self.ACCENT_COLOR,
            self.font_size,
            slot="invincible",
        )

    def pause(
        self,
        canvas: VisualizerUtils,
        width: int,
        height: int,
    ) -> None:
        pause_lines = ("PAUSED", "P: Resume", "H: Back to home")
        self._draw_panel_lines(
            canvas,
            pause_lines,
        )
        self._put_lines_center(
            canvas,
            width,
            height,
            pause_lines,
            {0: self.ACCENT_COLOR},
        )

    def instruction(
        self,
        canvas: VisualizerUtils,
        width: int,
        height: int,
    ) -> None:
        self._put_lines_center(canvas, width, height, self.INSTRUCTION_LINES)

    def confirm_clear(
        self,
        canvas: VisualizerUtils,
        width: int,
        height: int,
    ) -> None:
        self._put_lines_center(
            canvas,
            width,
            height,
            [
                "Clear Rankings?",
                "Y: Yes",
                "N: No",
            ],
        )
