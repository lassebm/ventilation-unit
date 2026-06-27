# AGENTS.md

Guidance for coding agents (and contributors using them) working in this repo. End-user docs live
in [README.md](README.md) and [PROTOCOLS.md](PROTOCOLS.md); this file is about *working on the code*.

## What this is

Unofficial, experimental control software for the STM32F100-based controller in the **Vents
VUT 250 VB EC A14** ventilation unit: two ESPHome external components, a standalone Python CLI, and
the protocol reference they all share. Grounded in firmware disassembly, USB captures, and observed
device behavior — see the README for the full picture.

## Layout

- `PROTOCOLS.md` — authoritative protocol reference: USB/PC register map, scaling formulas,
  front-panel UART byte layout, startup behavior, firmware quirks. Source of truth for any protocol
  code; don't invent register addresses or scaling factors.
- `ventilation_unit.py` — standalone Python CLI for direct USB/PC register read/write/poll.
- `esphome/components/ventilation_unit/` — ESPHome component for the USB/PC register protocol
  (C++ runtime in `ventilation_unit.h` + Python codegen in `__init__.py`). Has its own `README.md`.
- `esphome/components/ventilation_panel_bridge/` — ESPHome component bridging the separate physical
  front-panel UART for mode/bypass control.
- `esphome/ventilation-unit.yaml` — the example / bring-up config. `esphome/secrets.yaml` is
  gitignored and local-only.
- `tests/` — unittest suite for CLI parsing, value scaling, and write guards.
- `reverse-engineering/` — **gitignored, local-only.** Firmware dumps, Ghidra analysis, Renode
  emulation, captures, RE notes. Never published; never reference these files from tracked code or docs.

## Two serial links

The controller exposes two independent application-level UARTs — keep them straight:

- **USB/PC link** via CP210x bridge at `38400 8N1` — used by `ventilation_unit.py` and the
  `ventilation_unit` component. Needs the CP210x modem-control lines to reset the STM32 into
  application mode, so it requires ESPHome `usb_uart` (a plain GPIO `uart` will not work) and an
  ESP32 with USB host (e.g. ESP32-S3).
- **Front-panel UART** at `600 8N1` — used by `ventilation_panel_bridge`.

## Build & test

- Python tests (no hardware needed): `python3 -m unittest discover -s tests`
- CLI (`uv` pulls in `pyserial` on the fly):
  `uv run --with pyserial ventilation_unit.py --help`
- Compile checks:
  - `python3 -m py_compile ventilation_unit.py`
  - `esphome compile esphome/ventilation-unit.yaml` (needs `esphome/secrets.yaml`).

## Formatting & linting

Mirrors upstream ESPHome's toolchain (configs at the repo root) — **run these before committing;
there is no CI to catch misses:**

- **C++** — `clang-format -i esphome/components/*/*.h` (uses `.clang-format`).
- **Python** — `ruff format . && ruff check .` (uses `pyproject.toml`).
- **YAML** — `yamllint .` (uses `.yamllint`).

If a tool isn't installed locally, run it ephemerally, e.g. `uvx ruff format .`, `uvx yamllint .`,
`uvx --from clang-format clang-format -i …`. The commented-out blocks in `ventilation-unit.yaml`
produce two `comments-indentation` *warnings* (intentional — they illustrate nesting); warnings
don't fail the lint.

## Conventions (keep consistent)

- **No RE references in published code/docs** — don't cite anything from the gitignored
  `reverse-engineering/` tree (notes, Ghidra symbols, capture/decoder scripts). Explain behavior
  self-containedly, citing `PROTOCOLS.md`.
- **CLI write units:** writes use human-facing units by default (speed setpoints as %, filter
  interval in hours, thresholds in displayed units). `--raw` writes exact 16-bit register payloads,
  `--force` bypasses guards on low-level writes, `--save` persists to flash. Register definitions
  and access flags live in `ventilation_unit.py`; the tests assert the scaling (e.g. 40% → raw 400).
- **ESPHome config writes** are gated behind an `edit_mode` switch — off during normal operation.
- Otherwise, match the style of the surrounding code and docs.

## Don't

- Commit `esphome/secrets.yaml`, the `.esphome/` build cache, or anything under
  `reverse-engineering/`.
- Change hardware-validated protocol/scaling logic without a clear reason — it drives real fans,
  bypass dampers, and frost protection. Prefer additive changes; cross-check `PROTOCOLS.md` and run
  the tests after touching register or scaling code.
