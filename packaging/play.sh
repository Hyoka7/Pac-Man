#!/bin/sh
# Start Pac-Man from its own folder so config.json and scores.json are found
# next to the game. An optional argument selects another configuration file.
cd "$(dirname "$0")" || exit 1
exec ./pac-man "${1:-config.json}"
