"""Both supported launch commands use the same development configuration."""

from pathlib import Path
import runpy
import unittest
from unittest.mock import patch


class EntrypointTests(unittest.TestCase):
    def test_module_and_script_entrypoints_preserve_startup_configuration(self) -> None:
        for mode in ('module', 'script'):
            with self.subTest(mode=mode), patch('mazegenerator.MazeGenerator') as generator, patch(
                'pacman.visualize.MazeVisualizer'
            ) as visualizer:
                if mode == 'module':
                    runpy.run_module('pacman', run_name='__main__')
                else:
                    runpy.run_path(
                        str(Path(__file__).resolve().parents[1] / 'main.py'),
                        run_name='__main__',
                    )
                generator.assert_called_once_with(size=(15, 15))
                config = visualizer.call_args.args[2]
                self.assertEqual(config.highscore_filename, 'scores.json')
                self.assertEqual(config.lives, 3)
                self.assertEqual(len(config.levels), 10)
                generator.return_value.generate.assert_called_once_with(seed=config.seed)
                visualizer.return_value.run.assert_called_once_with()
