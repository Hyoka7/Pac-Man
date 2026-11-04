"""Recover configuration fields without discarding valid user settings."""

from contextlib import redirect_stderr
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pacman.models import Config
from pacman.parser import ConfigParser


class ParserTests(unittest.TestCase):
    def parse_text(self, text: str) -> tuple[Config, str]:
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text(text, encoding='utf-8')
            output = StringIO()
            with redirect_stderr(output):
                config = ConfigParser(path).parse_config()
            return config, output.getvalue()

    def test_valid_config_preserves_values_and_ignores_unknown_keys(self) -> None:
        config, _ = self.parse_text(json.dumps({
            'highscore_filename': 'custom.json', 'lives': 4, 'seed': 7,
            'points_per_pacgum': 12, 'points_per_super_pacgum': 60,
            'points_per_ghost': 300, 'unused': True,
            'levels': [{'width': 30, 'height': 15, 'max_time': 120, 'other': 1}],
        }))
        self.assertEqual(config.highscore_filename, 'custom.json')
        self.assertEqual((config.lives, config.seed), (4, 7))
        self.assertEqual((config.points_per_pacgum, config.points_per_super_pacgum,
                          config.points_per_ghost), (12, 60, 300))
        self.assertEqual(config.levels[0].model_dump(),
                         {'width': 30, 'height': 15, 'max_time': 120})

    def test_comments_do_not_remove_hashes_inside_strings(self) -> None:
        config, _ = self.parse_text(
            '# header\n{\n  # comment\n"highscore_filename": "scores#1.json"\n}\n')
        self.assertEqual(config.highscore_filename, 'scores#1.json')

    def test_comment_filter_preserves_syntax_error_line_number(self) -> None:
        with self.assertRaises(json.JSONDecodeError) as result:
            self.parse_text('# first\n{\n# third\n"lives": !\n}')
        self.assertEqual(result.exception.lineno, 4)

    def test_invalid_fields_fall_back_independently(self) -> None:
        config, warnings = self.parse_text(json.dumps({
            'lives': 0, 'seed': [], 'points_per_pacgum': 25,
            'levels': [{'width': 10, 'height': 25, 'max_time': -1},
                       {'width': 30, 'height': 31, 'max_time': 150}],
        }))
        self.assertEqual((config.lives, config.seed, config.points_per_pacgum), (3, 42, 25))
        self.assertEqual(config.levels[0].model_dump(),
                         {'width': 15, 'height': 25, 'max_time': 90.0})
        self.assertEqual(config.levels[1].model_dump(),
                         {'width': 30, 'height': 15, 'max_time': 150})
        for location in ('config.lives', 'config.seed', 'levels[0].width',
                         'levels[0].max_time', 'levels[1].height'):
            self.assertIn(location, warnings)

    def test_missing_empty_or_wrong_type_levels_have_a_playable_default(self) -> None:
        for values in ({}, {'levels': []}, {'levels': None}, {'levels': 'bad'}):
            with self.subTest(values=values):
                config, warnings = self.parse_text(json.dumps(values))
                self.assertEqual(len(config.levels), 1)
                self.assertEqual(config.levels[0].width, 15)
                self.assertIn('config.levels', warnings)

    def test_malformed_level_does_not_discard_other_levels(self) -> None:
        config, warnings = self.parse_text('{"levels":[null,{"width":25}]}')
        self.assertEqual([level.width for level in config.levels], [15, 25])
        self.assertIn('levels[0]', warnings)

    def test_non_finite_timer_uses_default(self) -> None:
        for timer in ('NaN', 'Infinity'):
            with self.subTest(timer=timer):
                config, warnings = self.parse_text(
                    '{"levels":[{"max_time":' + timer + '}]}')
                self.assertEqual(config.levels[0].max_time, 90.0)
                self.assertIn('levels[0].max_time', warnings)

    def test_non_object_root_is_rejected(self) -> None:
        for text in ('[]', 'null', '42', '"text"'):
            with self.subTest(text=text), self.assertRaisesRegex(TypeError, 'JSON object'):
                self.parse_text(text)
