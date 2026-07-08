# Hardware

The protocol notes and this integration are based on one STM32F100 controller
from a **Vents VUT 250 VB EC A14** unit. Other units may share parts of the
protocol, but none have been validated.

This integration reuses the unit's own interfaces rather than adding a custom
board: an ESP32 connects to the controller's existing USB/PC port and, if you
want panel-level control, taps the front panel UART. Nothing inside the unit has
to be modified.

## What you need

- An **ESP32 with a USB host interface** — the sample configuration uses an
  `esp32-s3-devkitc-1`. The USB/PC link is driven as a USB host, so a
  USB-host-capable chip is required; see [Serial links](#serial-links).
- A **USB connection from the ESP32's host port to the controller's USB/PC
  port** — the same port the vendor Windows app plugs into.
- **Optional, for mode and bypass control:** wiring to interpose the ESP32 on
  the front panel UART, between the physical panel and the controller.

## Serial links

The controller exposes two independent application-level serial links:

- **USB/PC control** through a CP210x USB-to-UART bridge at `38400 8N1` — the
  port the vendor Windows app uses. ESPHome talks to it as a USB host and drives
  the CP210x modem-control lines to reset the STM32 into its application
  firmware; see [Entering the application](PROTOCOL.md#entering-the-application).
- A separate **front panel UART** at `600 8N1`.

The `ventilation_unit` component therefore needs ESPHome's `usb_uart` support; a
plain GPIO `uart` cannot drive those modem-control lines.

For the MCU peripherals and pin assignments behind each link, see the
[serial links table](PROTOCOL.md#serial-links) in the protocol reference.

## Wiring

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

The front panel tap is only needed for the `ventilation_panel_bridge` component.
For USB/PC register access alone — sensors, setpoints, and filter reset through
the `ventilation_unit` component — the USB connection to the controller is
enough.

## Enclosure

A parametric, 3D-printable enclosure for the assembled node lives in
**[../enclosure/](../enclosure/)** — the author's specific build (ESP32-S3-DevKitC-1 +
double RJ45 breakout), shared as a reference you can re-fit to your own parts.
