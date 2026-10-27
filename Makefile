UV = uv
VENV = .venv
FLAKE8 := .venv/bin/flake8
MYPY := .venv/bin/mypy
SRC = ./src
MLX = $(SRC)/mlx-2.2-py3-none-any.whl
MAZEGEN = $(SRC)/mazegenerator-2.1.0-py3-none-any.whl
MYPYFLAGS = --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

export UV_LINK_MODE = copy

.PHONY: install run debug clean fclean lint lint-strict

install: $(VENV)
	$(UV) sync
	$(UV) pip install flake8 mypy $(MLX) $(MAZEGEN)

run:
	$(UV) run main.py

debug:
	$(UV) run -m pdb main.py

$(VENV):
	uv venv $(VENV)

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache
	find . -path "./$(VENV)" -prune -o -type d -name "__pycache__" -exec rm -rf {} +

fclean: clean
	rm -rf $(VENV)

lint:
	$(UV) run $(FLAKE8) .
	$(UV) run $(MYPY) . $(MYPYFLAGS)

lint-strict:
	$(UV) run $(FLAKE8) .
	$(UV) run $(MYPY) . --strict