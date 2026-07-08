# Vents VUT 250 → Home Assistant (ESPHome)

A reverse-engineered ESPHome integration for the **Vents VUT 250 VB EC A14**
ventilation unit — external components that bring its STM32F100-based controller
into Home Assistant.

Because it drives ventilation, fans, bypass dampers, filter/service counters, and
frost-protection settings, treat it as experimental control software. See
[Safety and disclaimer](#safety-and-disclaimer) below.

## What this project does

- Documents the controller's USB/PC register protocol and the separate front
  panel UART protocol.
- Provides the `ventilation_unit` ESPHome component for sensors, numbers,
  switches, buttons, and firmware diagnostics over the USB/PC link.
- Provides the `ventilation_panel_bridge` ESPHome component for panel-level
  mode and bypass control through the separate front panel UART.
- Provides `cli/ventilation_unit.py`, a small Python CLI for reading, writing,
  and polling the USB/PC application registers directly.

## Hardware at a glance

The controller has two application-level serial links: USB/PC control through a
CP210x bridge at `38400 8N1`, and a separate front panel UART at `600 8N1`. The
`ventilation_unit` component uses ESPHome's `usb_uart` support and expects an
ESP32 with a USB host interface (the sample config uses an
`esp32-s3-devkitc-1`).

Full wiring and serial-link details: **[docs/HARDWARE.md](docs/HARDWARE.md)**.

## Quick start

1. Wire up the ESP32 and the unit — **[docs/HARDWARE.md](docs/HARDWARE.md)**.
2. Flash and configure ESPHome, or use the CLI — **[docs/INSTALL.md](docs/INSTALL.md)**.

## How it was reverse-engineered

The unit ships with no public protocol spec — everything here was worked out
from the author's own hardware:

- **Dumped the firmware** — read the STM32F100 controller's flash out through
  its ROM bootloader over the CP210x USB-UART bridge.
- **Captured the USB link** — recorded the unit's stock Windows configuration
  app talking to the controller and decoded the register read/write protocol
  from the traffic.
- **Disassembled in Ghidra** — analyzed both the controller firmware and the
  Windows app to pin down the register map, scaling formulas, panel byte layout,
  and firmware quirks (freeze protection, humidity boost, the filter counter,
  and the commit-to-flash command).

The reverse-engineering tooling, firmware dumps, and notes are kept locally and
aren't part of this repository.

## Documentation

| Doc | What |
| --- | --- |
| **[docs/HARDWARE.md](docs/HARDWARE.md)** | Serial links, board requirements, and wiring |
| **[docs/INSTALL.md](docs/INSTALL.md)** | ESPHome flashing, configuration, and usage (entities, modes, bypass), plus the CLI tool and development checks |
| **[docs/PROTOCOL.md](docs/PROTOCOL.md)** | Protocol reference: register map, scaling formulas, panel byte layout, startup behavior, and firmware quirks |
| **[enclosure/](enclosure/)** | A parametric, 3D-printable enclosure — the author's build, ready to adapt |

## Safety and disclaimer

- This project is the result of **reverse-engineering hardware the author owns**.
  It is **not affiliated with, authorized by, or endorsed by Vents**. "Vents" and
  "VUT" are trademarks of their respective owners, used here only to describe
  compatibility.
- You connect this at your own risk. Connecting or configuring it incorrectly can
  damage your controller or the connected hardware.
- Provided **as-is, without warranty of any kind**. See [`LICENSE`](LICENSE).

## AI usage

AI was used extensively across this project — to work through the disassembly
and USB captures, and to write the ESPHome components, the CLI, the tests, and
this documentation. None of it is guesswork: every claim is grounded in the
reverse-engineering described above — firmware disassembly, USB captures, and
observed device behavior.

## License

The code and documentation in this repository are released under the MIT
License; see [`LICENSE`](LICENSE).
