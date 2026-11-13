UV = uv
VENV = .venv
CONFIG ?= config.json
FLAKE8 := .venv/bin/flake8
MYPY := .venv/bin/mypy
SRC = ./src
MLX = $(SRC)/mlx-2.2-py3-none-any.whl
MAZEGEN = $(SRC)/mazegenerator-2.1.0-py3-none-any.whl
MYPYFLAGS = --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

export UV_LINK_MODE = copy

# itch.io upload (butler must be installed and logged in).
BUTLER ?= butler
ITCH_TARGET ?= hyoka7/pac-man:linux
VERSION ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo dev)

.PHONY: install run debug build package check-butler upload clean fclean lint lint-strict

install: $(VENV)
	$(UV) sync --inexact
	$(UV) pip install $(MLX) $(MAZEGEN)

run: install
	$(UV) run pac-man.py $(CONFIG)

debug: install
	$(UV) run -m pdb pac-man.py $(CONFIG)

build: install
	$(UV) run pyinstaller --clean --noconfirm pac-man.spec
	cp $(CONFIG) dist/pac-man/config.json

# Linux build for itch.io: dist/pac-man-linux.zip (contents at the root).
package: build
	cp packaging/play.sh packaging/.itch.toml packaging/README.txt dist/pac-man/
	chmod +x dist/pac-man/play.sh dist/pac-man/pac-man
	rm -f dist/pac-man-linux.zip
	cd dist/pac-man && zip -qr ../pac-man-linux.zip .

check-butler:
	@command -v $(BUTLER) >/dev/null 2>&1 || { \
		echo "butler not found. Install it: https://itch.io/docs/butler/installing.html"; \
		exit 1; }

# Push dist/pac-man to itch.io; only changed files are sent.
upload: check-butler package
	$(BUTLER) push dist/pac-man $(ITCH_TARGET) --userversion $(VERSION)

$(VENV):
	uv venv $(VENV)

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache build dist
	find . -path "./$(VENV)" -prune -o -type d -name "__pycache__" -exec rm -rf {} +

fclean: clean
	rm -rf $(VENV)

lint:
	$(UV) run $(FLAKE8) .
	$(UV) run $(MYPY) . $(MYPYFLAGS)

lint-strict:
	$(UV) run $(FLAKE8) .
	$(UV) run $(MYPY) . --strict
