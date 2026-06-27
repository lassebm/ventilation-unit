# Vents VUT 250 → Home Assistant (ESPHome)

A reverse-engineered ESPHome integration for the **Vents VUT 250 VB EC A14**
ventilation unit — external components that bring its STM32F100-based controller
into Home Assistant.

Because it drives ventilation, fans, bypass dampers, filter/service counters, and
frost-protection settings, treat it as experimental control software. See
[Safety And Disclaimer](#safety-and-disclaimer) below.

## What This Project Does

- Documents the controller's USB/PC register protocol and the separate front
  panel UART protocol.
- Provides the `ventilation_unit` ESPHome component for sensors, numbers,
  switches, buttons, and firmware diagnostics over the USB/PC link.
- Provides the `ventilation_panel_bridge` ESPHome component for panel-level
  mode and bypass control through the separate front panel UART.
- Provides `ventilation_unit.py`, a small Python CLI for reading, writing, and
  polling the USB/PC application registers directly.

The detailed protocol reference lives in [`PROTOCOLS.md`](PROTOCOLS.md).

## Hardware Assumptions

The protocol notes are based on one STM32F100 controller from a Vents VUT 250 VB
EC A14 unit. Other units may share parts of the protocol, but none have been
validated.

The controller has two application-level serial links:

- USB/PC control through a CP210x USB-to-UART bridge at `38400 8N1`.
- A separate front panel/control-board UART at `600 8N1`.

The ESPHome `ventilation_unit` component uses ESPHome's `usb_uart` support and
expects an ESP32 board with USB host capability. The sample configuration uses
an `esp32-s3-devkitc-1`.

## Physical Wiring

The ESP32 can bridge the front panel UART while also talking to the unit through
the USB/PC link. Keep the panel power and ground wiring direct between the
physical panel and the unit. When the ESP32 is connected to the unit through
USB, that path usually provides the ESP32's ground reference for the panel UART.

```text
+------------------------+        +------------------------+        +------------------------+
| Physical panel         |        | ESP32-S3               |        | Ventilation unit       |
|                        |        |                        |        |                        |
|                     TX |------->| Panel UART RX          |        |                        |
|                     RX |<-------| Panel UART TX          |        |                        |
|                        |        |                        |        |                        |
|                        |        |     Controller UART TX |------->| Panel UART RX          |
|                        |        |     Controller UART RX |<-------| Panel UART TX          |
|                        |        |               USB host |<======>| CP210x USB-UART        |
|                        |        |                        |        |                        |
|                        |        +------------------------+        |                        |
|                        |                                          |                        |
|                    GND |----------------------------------------->| GND                    |
|                +24V in |<-----------------------------------------| +24V panel power       |
+------------------------+                                          +------------------------+
```

## ESPHome Integration

The ESPHome integration has two components:

- `ventilation_unit` talks to the USB/PC register protocol and exposes sensors,
  numbers, switches, and buttons.
- `ventilation_panel_bridge` can sit between the physical front panel and the
  controller so ESPHome can control panel-level fields such as mode and bypass.

Start from
[`esphome/ventilation-unit.yaml`](esphome/ventilation-unit.yaml), adjust Wi-Fi
secrets, board, pins, and whether the physical panel is connected, then compile:

```sh
esphome compile esphome/ventilation-unit.yaml
```

Configuration writes in the ESPHome component are guarded by an `edit_mode`
switch. Leave edit mode off during normal operation; enable it only while making
intentional configuration changes.

For implementation details, see the component README:
[`esphome/components/ventilation_unit/README.md`](esphome/components/ventilation_unit/README.md).

## CLI Tool

Use the CLI for direct USB/PC register checks from a computer:

```sh
uv run --with pyserial ventilation_unit.py read-all SERIAL_PORT
uv run --with pyserial ventilation_unit.py --help
```

Example commands:

```sh
uv run --with pyserial ventilation_unit.py read SERIAL_PORT firmware_version
uv run --with pyserial ventilation_unit.py write SERIAL_PORT humidity_boost_threshold 60 --verify --save
uv run --with pyserial ventilation_unit.py write SERIAL_PORT inflow_speed_1_setpoint 40 --verify --save
uv run --with pyserial ventilation_unit.py write SERIAL_PORT filter_replacement_interval 9999 --verify --save
```

CLI writes use human-facing values by default: speed setpoints are percentages,
filter replacement interval is hours, and thresholds use their displayed units.
Use `--raw` for exact 16-bit register payloads, and `--force` for guarded
low-level writes.

## Repository Contents

- [`PROTOCOLS.md`](PROTOCOLS.md): protocol reference, including register map,
  scaling formulas, panel byte layout, startup behavior, and firmware quirks.
- [`esphome/components/ventilation_unit`](esphome/components/ventilation_unit):
  ESPHome component for the USB/PC register protocol.
- [`esphome/components/ventilation_panel_bridge`](esphome/components/ventilation_panel_bridge):
  ESPHome bridge for the separate physical panel UART.
- [`esphome/ventilation-unit.yaml`](esphome/ventilation-unit.yaml): example
  ESPHome configuration.
- [`ventilation_unit.py`](ventilation_unit.py): standalone CLI for direct USB/PC
  application-register access.
- [`tests`](tests): lightweight tests for CLI parsing, scaling, and write guards.

## Development Checks

```sh
python3 -m unittest discover -s tests
python3 -m py_compile ventilation_unit.py
esphome compile esphome/ventilation-unit.yaml
```

## Provenance And AI Assistance

This project is a human/AI collaboration and would not exist in its current form
without substantial AI assistance. AI assistance was used to analyze and iterate
on the reverse-engineering notes, ESPHome components, helper CLI, tests, and
documentation. The claims in the project are grounded in firmware disassembly,
USB captures, and observed device behavior.

The underlying evidence came from:

- The original Windows service application shipped with the unit.
- USB serial captures of the Windows application talking to the controller.
- A firmware image dumped from a physical device through the STM32 bootloader.

Both the dumped controller firmware and the Windows application were
disassembled with Ghidra.

## Safety And Disclaimer

- This project is the result of **reverse-engineering hardware the author owns**.
  It is **not affiliated with, authorized by, or endorsed by Vents**. "Vents" and
  "VUT" are trademarks of their respective owners, used here only to describe
  compatibility.
- You connect this at your own risk. Connecting or configuring it incorrectly can
  damage your controller or the connected hardware.
- Provided **as-is, without warranty of any kind**. See [`LICENSE`](LICENSE).

## License

The code and documentation in this repository are released under the MIT
License; see [`LICENSE`](LICENSE).
