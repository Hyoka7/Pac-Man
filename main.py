from mazegenerator import MazeGenerator

from visualize import MazeVisualizer

m = MazeGenerator()
m.generate()
MazeVisualizer(m.maze, m).run()
