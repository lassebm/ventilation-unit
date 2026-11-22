# Installation

Get the ESP32 flashed, configured, and talking to Home Assistant. Wire up the
hardware first — see [HARDWARE.md](HARDWARE.md).

## Components

The ESPHome integration has two components:

- `ventilation_unit` talks to the USB/PC register protocol and exposes sensors,
  numbers, switches, and buttons over the CP210x link.
- `ventilation_panel_bridge` sits between the physical front panel and the
  controller's panel UART so ESPHome can control panel-level fields such as mode
  and bypass.

The `ventilation_unit` component requires ESPHome's `usb_uart` support and an
ESP32 with a USB host interface (a plain GPIO `uart` cannot drive the CP210x
modem-control lines that reset the STM32 into application mode). See
[HARDWARE.md](HARDWARE.md).

## Flash and configure

Start from [`../esphome/ventilation-unit.yaml`](../esphome/ventilation-unit.yaml),
a complete working example. Adjust Wi-Fi secrets, board, pins, and whether the
physical panel is connected, then compile and upload:

```sh
esphome run esphome/ventilation-unit.yaml
```

`esphome/secrets.yaml` is gitignored and local-only; keep your Wi-Fi credentials
there.

## Entities and control

Read-only sensors and binary sensors are published from a periodic refresh
cycle. Writable configuration is exposed as numbers, switches, and buttons.

**Edit mode.** Configuration writes are guarded by an `edit_mode` switch. Leave
it off during normal operation — while it's off, writes from numbers, switches,
and buttons are ignored. Enable it only while making intentional configuration
changes.

The entities expose values in human-facing units — percent, RPM, hours, °C —
rather than raw register values; [PROTOCOL.md](PROTOCOL.md) lists the scaling
behind each.

## Ventilation mode and speeds

`ventilation_panel_bridge` exposes the ventilation mode as a `fan` entity with
three speed levels:

| Fan state | Preset | Panel mode |
| --- | --- | ---: |
| Off | — | 0 (Standby) |
| Speed 1 (33%) | Speed 1 | 1 |
| Speed 2 (66%) | Speed 2 | 2 |
| Speed 3 (100%) | Speed 3 | 3 |

The 33/66/100% figures are just ESPHome's three-speed UI representation; they
select a panel mode, not an airflow percentage. The actual airflow for each mode
is set by the inflow/outflow speed setpoints — see
[PROTOCOL.md](PROTOCOL.md#speed-setpoints).

The same three modes are also exposed as fan **preset modes**, so they appear in
the fan entity's preset picker, in automations, and in voice assistants. Presets
alias the speeds in declared order, so the preset and the speed slider always
reflect the same panel mode. The names default to `Speed 1`/`Speed 2`/`Speed 3` and can be overridden
per device with `preset_modes` under `mode:`.

A mode set from ESPHome sticks until someone changes it on the physical panel.

Set `panel_connected: false` when the panel UART is wired but no physical panel
is attached. This keeps the bridge from treating a floating RX pin as panel
commands.

## Bypass and filter reset

- **Bypass** — the panel bridge exposes a writable bypass control (a setting
  from ESPHome sticks until the physical panel changes it); the USB link exposes
  a read-only bypass state. Use the panel bridge control to open or close the
  damper.
- **Filter reset** — reset the filter counter with the filter-reset button on
  `ventilation_unit`, or from the physical panel.
- **Filter life** — the optional `filter_life_remaining` (%) and
  `filter_remaining_hours` sensors are computed from the controller's own filter
  runtime and replacement interval, so they reach 0 exactly when the controller
  flags the filter as due and reset along with it. Like the due flag, they jump
  back up if the counter is left to wrap; see
  [PROTOCOL.md](PROTOCOL.md#filter-runtime-counter-rollover).

## CLI tool

Use `cli/ventilation_unit.py` for direct USB/PC register checks from a computer:

```sh
uv run --with pyserial cli/ventilation_unit.py read-all SERIAL_PORT
uv run --with pyserial cli/ventilation_unit.py --help
```

Example commands:

```sh
uv run --with pyserial cli/ventilation_unit.py read SERIAL_PORT firmware_version
uv run --with pyserial cli/ventilation_unit.py write SERIAL_PORT humidity_boost_threshold 60 --verify --save
uv run --with pyserial cli/ventilation_unit.py write SERIAL_PORT inflow_speed_1_setpoint 40 --verify --save
uv run --with pyserial cli/ventilation_unit.py write SERIAL_PORT filter_replacement_interval 9999 --verify --save
```

CLI writes use human-facing values by default: speed setpoints are percentages,
filter replacement interval is hours, and thresholds use their displayed units.
Use `--raw` for exact 16-bit register payloads, and `--force` for guarded
low-level writes.

## Development checks

```sh
script/test          # CLI tests, config validation, and host end-to-end tests (needs uv)
script/test --all    # plus a full ESP32-S3 compile of the example config
python3 -m py_compile cli/ventilation_unit.py
```
