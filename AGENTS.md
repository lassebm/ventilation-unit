# AGENTS.md

Guidance for coding agents (and contributors using them) working in this repo. User-facing docs
live in [README.md](README.md) and [docs/](docs/); this file is about *working on the code*.

## What this is

Unofficial, experimental control software for the STM32F100-based controller in the **Vents
VUT 250 VB EC A14** ventilation unit: two ESPHome external components, a standalone Python CLI, and
the protocol reference they all share. Grounded in firmware disassembly, USB captures, and observed
device behavior — see the README for the full picture.

## Layout

- `docs/PROTOCOL.md` — authoritative protocol reference: USB/PC register map, scaling formulas,
  front panel UART byte layout, startup behavior, firmware quirks. Source of truth for any protocol
  code; don't invent register addresses or scaling factors.
- `docs/HARDWARE.md`, `docs/INSTALL.md` — end-user hardware/wiring and install/CLI/usage docs.
- `cli/ventilation_unit.py` — standalone Python CLI for direct USB/PC register read/write/poll.
- `esphome/components/ventilation_unit/` — ESPHome component for the USB/PC register protocol
  (C++ runtime in `ventilation_unit.h` + Python codegen in `__init__.py`).
- `esphome/components/ventilation_panel_bridge/` — ESPHome component bridging the separate physical
  front panel UART for mode/bypass control.
- `esphome/ventilation-unit.yaml` — the example / bring-up config. `esphome/secrets.yaml` is
  gitignored and local-only.
- `cli/tests/` — unittest suite for CLI parsing, value scaling, and write guards.
- `reverse-engineering/` — **gitignored, local-only.** Firmware dumps, Ghidra analysis, Renode
  emulation, captures, RE notes. Never published; never reference these files from tracked code or docs.

## Two serial links

The controller exposes two independent application-level UARTs — keep them straight:

- **USB/PC link** via CP210x bridge at `38400 8N1` — used by `cli/ventilation_unit.py` and the
  `ventilation_unit` component. Needs the CP210x modem-control lines to reset the STM32 into
  application mode, so it requires ESPHome `usb_uart` (a plain GPIO `uart` will not work) and an
  ESP32 with a USB host interface (e.g. an ESP32-S3).
- **Front panel UART** at `600 8N1` — used by `ventilation_panel_bridge`.

## Build & test

- Python tests (no hardware needed): `python3 -m unittest discover -s cli/tests -t cli`
- CLI (`uv` pulls in `pyserial` on the fly):
  `uv run --with pyserial cli/ventilation_unit.py --help`
- Compile checks:
  - `python3 -m py_compile cli/ventilation_unit.py`
  - `esphome compile esphome/ventilation-unit.yaml` (needs `esphome/secrets.yaml`).

## Formatting & linting

Mirrors upstream ESPHome's toolchain. The configs (`.clang-format`, `.yamllint`, and the ruff
sections of `pyproject.toml`) are copies of upstream's, and the tool versions are pinned to
upstream's. **Run these before committing.** There is no CI to catch misses:

- **C++** — `uvx --from clang-format==23.1.3 clang-format -i esphome/components/*/*.h`
- **Python** — `uvx ruff@0.17.5 format . && uvx ruff@0.17.5 check .`
- **YAML** — `uvx yamllint@1.38.0 .`

Use these pinned versions, not whatever is installed locally or the latest release. A newer tool can
stabilize a lint rule or reformat code, which changes results without any change here. After
touching register or scaling code, also re-run the Python tests above.

If a linter flags something new, check upstream's config before changing code. Upstream may already
ignore the rule. Sync the config rather than working around it.

## Conventions (keep consistent)

- **No RE references in published code/docs** — don't cite anything from the gitignored
  `reverse-engineering/` tree (notes, Ghidra symbols, capture/decoder scripts). Explain behavior
  self-containedly, citing `docs/PROTOCOL.md`.
- **CLI write units:** writes use human-facing units by default (speed setpoints as %, filter
  interval in hours, thresholds in displayed units). `--raw` writes exact 16-bit register payloads,
  `--force` bypasses guards on low-level writes, `--save` persists to flash. Register definitions
  and access flags live in `cli/ventilation_unit.py`; the tests assert the scaling (e.g. 40% → raw 400).
- **ESPHome config writes** are gated behind an `edit_mode` switch — off during normal operation.
- Otherwise, match the style of the surrounding code and docs.

## Keeping up with ESPHome releases

When bringing the components up to a new ESPHome release (or fixing a break caused by one):

- Read the release notes for **every** version since the last update, not just the latest. Start
  with the blog posts on esphome.io (upgrade checklist, breaking changes, developer-facing changes),
  and use the full changelogs or developers.esphome.io when you need more detail.
- **Use the replacement upstream recommends.** Don't use a shim or a local workaround. When
  something is removed, moved or deprecated, find what the release notes, the `ESPDEPRECATED`
  message, or the header comments point to, and migrate to that. For example, use the stack-based
  `*_to` / `snprintf` helpers instead of the heap-allocating ones now in `alloc_helpers.h`, and
  `make_entity_preference<T>()` instead of raw `make_preference(get_object_id_hash() ^ …)`. A
  successful compile isn't proof. Also check the headers for deprecations that still build.
- Update the example config and the docs for any new YAML requirements.
- Re-sync the tooling from upstream's `dev` branch:
  - Update the pinned versions in "Formatting & linting" from `requirements_test.txt` (ruff) and
    `requirements_dev.txt` (clang-format, yamllint).
  - Diff `.clang-format`, `.yamllint`, and the ruff sections of `pyproject.toml` against upstream's
    and adopt the changes.
  - Re-run the formatters and linters.
- Verify with a full `esphome compile` (check for warnings or deprecations from the components),
  the Python tests, and the linters.

## Don't

- Commit `esphome/secrets.yaml`, the `.esphome/` build cache, or anything under
  `reverse-engineering/`.
- Change hardware-validated protocol/scaling logic without a clear reason — it drives real fans,
  bypass dampers, and frost protection. Prefer additive changes; cross-check `docs/PROTOCOL.md` and run
  the tests after touching register or scaling code.
