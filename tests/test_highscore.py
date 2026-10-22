"""Score validation, ordering, persistence and recoverable file errors."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pydantic import ValidationError

from visualize.highscore import HighscoreManager, ScoreEntry


class HighscoreTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'scores.json'

    def test_missing_file_starts_empty_without_creating_file(self) -> None:
        manager = HighscoreManager(str(self.path))
        self.assertEqual(manager.scores.scores, [])
        self.assertFalse(self.path.exists())

    def test_add_save_and_reload_keep_descending_scores(self) -> None:
        manager = HighscoreManager(str(self.path))
        for name, score in [('low', 10), ('high', 90), ('middle', 50)]:
            manager += ScoreEntry(name=name, score=score)
        restored = HighscoreManager(str(self.path))
        self.assertEqual([(e.name, e.score) for e in restored.scores.scores],
                         [('high', 90), ('middle', 50), ('low', 10)])

    def test_load_sorts_unsorted_file(self) -> None:
        self.path.write_text(
            '{"scores":[{"name":"low","score":10},{"name":"high","score":90}]}',
            encoding='utf-8',
        )
        manager = HighscoreManager(str(self.path))
        self.assertEqual([e.score for e in manager.scores.scores], [90, 10])

    def test_invalid_files_start_empty_and_are_not_rewritten(self) -> None:
        for data in ('{broken', '{"scores":[{"name":"bad","score":-1}]}'):
            with self.subTest(data=data):
                self.path.write_text(data, encoding='utf-8')
                with redirect_stdout(StringIO()) as output:
                    manager = HighscoreManager(str(self.path))
                self.assertEqual(manager.scores.scores, [])
                self.assertTrue(output.getvalue())
                self.assertEqual(self.path.read_text(encoding='utf-8'), data)

    def test_write_failure_keeps_in_memory_entry(self) -> None:
        manager = HighscoreManager(str(self.path))
        manager.save_path = self.path.parent  # A directory cannot be opened as a file.
        entry = ScoreEntry(name='retained', score=10)
        with redirect_stdout(StringIO()) as output:
            manager += entry
        self.assertTrue(output.getvalue())
        self.assertEqual(manager.scores.scores, [entry])

    def test_score_entry_boundaries(self) -> None:
        for name in ('a', 'a'*12):
            self.assertEqual(ScoreEntry(name=name, score=0).score, 0)
        for values in ({'name':'', 'score':0}, {'name':'a'*13, 'score':0},
                       {'name':'a', 'score':-1}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                ScoreEntry(**values)
