"""Configuration loading and error exits through both launch commands."""

from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import runpy
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


class EntrypointTests(unittest.TestCase):
    def launch(self, mode: str, args: list[str]) -> int:
        with patch('sys.argv', ['pacman.py', *args]):
            with self.assertRaises(SystemExit) as result:
                if mode == 'module':
                    runpy.run_module('pacman', run_name='__main__')
                else:
                    runpy.run_path(
                        str(Path(__file__).resolve().parents[1] / 'pacman.py'),
                        run_name='__main__',
                    )
        return result.exception.code

    def test_module_and_script_use_the_supplied_configuration(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            path.write_text('{"lives":4,"seed":99,"levels":[{"width":25,"height":15}]}')
            for mode in ('module', 'script'):
                with self.subTest(mode=mode), redirect_stderr(StringIO()), patch(
                    'mazegenerator.MazeGenerator'
                ) as generator, patch('pacman.visualize.MazeVisualizer') as visualizer:
                    with patch('pacman.__main__.MazeGenerator', generator), patch(
                        'pacman.__main__.MazeVisualizer', visualizer
                    ):
                        self.assertEqual(self.launch(mode, [str(path)]), 0)
                    generator.assert_called_once_with(size=(25, 15))
                    config = visualizer.call_args.args[2]
                    self.assertEqual(config.lives, 4)
                    generator.return_value.generate.assert_called_once_with(seed=99)
                    visualizer.return_value.run.assert_called_once_with()

    def test_input_failures_exit_without_starting_the_game(self) -> None:
        with TemporaryDirectory() as directory:
            invalid = Path(directory) / 'invalid.json'
            invalid.write_text('{broken')
            root_list = Path(directory) / 'list.json'
            root_list.write_text('[]')
            bad_encoding = Path(directory) / 'encoding.json'
            bad_encoding.write_bytes(b'\xff')
            cases = ([], ['a', 'b'], [str(Path(directory) / 'missing.json')],
                     [str(invalid)], [str(root_list)], [str(bad_encoding)])
            for mode in ('module', 'script'):
                for args in cases:
                    output = StringIO()
                    with self.subTest(mode=mode, args=args), redirect_stderr(output), patch(
                        'mazegenerator.MazeGenerator'
                    ) as generator, patch('pacman.visualize.MazeVisualizer') as visualizer:
                        with patch('pacman.__main__.MazeGenerator', generator), patch(
                            'pacman.__main__.MazeVisualizer', visualizer
                        ):
                            self.assertEqual(self.launch(mode, args), 1)
                        self.assertTrue(output.getvalue())
                        self.assertNotIn('Traceback', output.getvalue())
                        generator.assert_not_called()
                        visualizer.assert_not_called()
