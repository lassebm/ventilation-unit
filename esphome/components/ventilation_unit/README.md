# Ventilation Unit ESPHome Component

This component exposes the ventilation controller's USB/PC register protocol to
ESPHome. The repository root `PROTOCOLS.md` is the protocol reference; this
document explains how the component is structured around it.

## Files

- `__init__.py`: ESPHome Python schema and code generation for the top-level
  `ventilation_unit` component.
- `ventilation_unit.h`: runtime implementation, entity helpers, serial
  protocol, connection handling, and polling state machine.

The sample ESPHome project lives in `../../ventilation-unit.yaml`.

The repository root also includes `ventilation_unit.py`, a standalone Python
CLI for reading, writing, and polling the same USB/PC application registers
without ESPHome.

## Transport

The controller is connected through a CP210x USB-to-UART bridge using ESPHome's
`usb_uart` component. The `ventilation_unit` schema expects a `usb_uart`
channel; a normal GPIO `uart` bus cannot drive the CP210x modem-control lines
used to reset the STM32 into application mode.

This requires an ESP32 model with a USB host interface, such as the ESP32-S3
used by the sample `esp32-s3-devkitc-1` configuration.

Application UART settings:

```text
38400 baud, 8 data bits, no parity, 1 stop bit
```

## Panel Bridge

The separate `ventilation_panel_bridge` component can sit between the physical
front panel and the controller's panel UART. It uses GPIO UARTs at `600 8N1`:

- Panel-side UART: receives command bytes from the physical panel and sends
  status bytes back to the panel. This UART is optional when no panel is
  installed.
- Controller-side UART: sends the effective command byte to the controller and
  receives the controller status byte.

The bridge treats the physical panel and ESPHome as command sources, then uses
one paced controller-side writer for the effective command. Physical panel bytes
update the bridge state instead of being forwarded directly; the effective
command is repeated every 100 ms so the controller keeps producing fresh status
even without a physical panel.

ESPHome can apply sticky overrides to the durable command fields:

| Field | Bits | Ownership |
| --- | --- | --- |
| Mode | `0x03` | ESPHome `fan` override persists until the physical panel changes mode bits |
| Bypass | `0x08` | ESPHome override persists until the physical panel changes bypass bit |
| Filter reset | `0x04` | Forwarded from the physical panel only |

The mode is exposed as a `fan` entity with three speed levels. Off maps to
Standby (panel mode 0); the three speeds map to the remaining panel modes:

| Fan state | Preset | Panel mode |
| --- | --- | ---: |
| Off | — | 0 (Standby) |
| Speed 1 (33%) | Speed 1 | 1 |
| Speed 2 (66%) | Speed 2 | 2 |
| Speed 3 (100%) | Speed 3 | 3 |

The same three modes are also exposed as fan **preset modes**, so they appear in
the automation preset picker and in voice assistants. Presets alias the speeds in
declared order, so the preset and the speed slider always reflect the same panel
mode. The names default to `Speed 1`/`Speed 2`/`Speed 3` and can be overridden
per device with `preset_modes` under `mode:`.

The controller firmware debounces panel command changes. It keeps a stability
counter of up to 10 repeated command bytes; a different command must be seen
enough times to count that stability down before it becomes active. The bridge
therefore repeats the effective command every 100 ms, which applies a changed
mode or bypass command in about a second while still leaving ample margin on the
600 baud UART.

Set `panel_connected: false` when the panel UART is configured but the physical
panel is disconnected. This keeps the bridge from treating a floating RX pin as
panel commands.

Filter reset from Home Assistant should keep using the USB register protocol
through `0x54`; the bridge does not synthesize panel filter-reset commands.
Bypass control must use this panel bridge. The USB `0x30` register is exposed as
bypass state/readback only; USB writes update the register backing value but do
not actuate the damper.

Controller status bytes are forwarded back to the physical panel and exposed as
binary sensors:

| Bit | Meaning |
| --- | --- |
| `0x01` | Filter/service due |
| `0x02` | Alarm/blink indicator |

## Startup

The component boots the ventilation controller into its normal application
firmware through the CP210x modem-control lines:

```text
RTS low  -> BOOT0 low, select user flash
DTR high -> NRST low, reset asserted
DTR low  -> NRST released, application boots
```

Startup sequence:

1. Wait for the USB UART transport to be connected.
2. Hold BOOT0 low with RTS.
3. Pulse reset with DTR.
4. Wait for the application to boot.
5. Read register `0xFF`.
6. Publish the firmware version when a response is received.
7. Start the normal refresh cycle.

No STM32 bootloader protocol is used.

## USB/PC Register Protocol

Reads:

```text
FF 01 rr -> hh ll
```

Writes:

```text
FF 00 rr hh ll
```

Values are unsigned 16-bit big-endian words. Writes do not return a response.

Most writable registers update firmware RAM only. To persist changes, the
component reads `0x60` after a normal write. The firmware treats that read as a
commit-to-flash command and returns `0xFFFF`.

## Entity Model

`__init__.py` defines the public YAML keys and maps them to C++ helper
entities. The register names follow the manual-facing terms used by
`PROTOCOLS.md`.

Read-only sensor and binary-sensor entities are published from the periodic
refresh cycle.

Writable configuration entities use small wrappers:

- `VentilationUnitNumber`: converts the user-facing value to a raw register
  value and queues a write.
- `VentilationUnitSwitch`: queues `0` or `1`.
- `VentilationUnitButton`: queues a fixed command value.
- `VentilationUnitEditModeSwitch`: toggles a local lock that allows or blocks
  configuration writes.

All entity writes go through the same command queue. This keeps Home Assistant
service calls from writing directly into the serial state machine. Configuration
writes are accepted only while `edit_mode` is on; with edit mode off, numbers,
switches, and buttons log and ignore write requests. Turning edit mode off also
drops queued writes that have not started yet.

## Register Scaling

The component exposes user-facing values and hides firmware scaling:

| Register | Entity | Conversion |
| --- | --- | --- |
| `0x10`..`0x15` | `inflow_speed_setpoints` | percent = raw / 10 |
| `0x20`..`0x25` | `outflow_speed_setpoints` | percent = raw / 10 |
| `0x40` | `inflow_rpm` | RPM = raw * 60 |
| `0x41` | `outflow_rpm` | RPM = raw * 60 |
| `0x50` | `humidity` | percent = raw / 33 |
| `0x50` | `humidity_voltage` | volts = raw / 333 |
| `0x51` | `temperature` | C = raw - 40 |
| `0x53` | `filter_runtime` | hours = raw / 6 |
| `0x55` | `filter_replacement_interval` | hours = raw / 6 |
| `0x70` | `freeze_protection_threshold` | C = raw |
| `0x72` | `humidity_boost_threshold` | percent = raw |

## Filter Reset

The ESPHome button writes `0x54 = 1`. The component then reads `0x60` to commit
the change and reads `0x53` back before publishing `filter_runtime`.

This readback is intentional. The component does not optimistically publish
zero; it publishes the value returned by the device after the reset and save
sequence.

## State Machine

The component is non-blocking except for the deliberate 2 ms inter-byte delay
used while writing command bytes.

States:

| State | Purpose |
| --- | --- |
| `IDLE` | No serial transaction active. Starts connection, refresh, or queued write. |
| `RESET_HIGH_WAIT` | DTR asserted, controller held in reset. |
| `RESET_LOW_WAIT` | DTR released, reset pulse finishing. |
| `STARTUP_WAIT` | Application boot delay before probing `0xFF`. |
| `WAIT_VERSION` | Waiting for the firmware-version read response. |
| `WAIT_REFRESH` | Waiting for a normal refresh-register response. |
| `WAIT_WRITE` | Short settle period after a normal write before saving. |
| `WAIT_SAVE` | Waiting for the `0x60` commit response. |
| `WAIT_FILTER_RUNTIME_READBACK` | Waiting for `0x53` after filter reset. |

Normal refresh flow:

```text
IDLE
  -> read next refresh register
  -> WAIT_REFRESH
  -> publish decoded value
  -> repeat until refresh list is done
  -> IDLE
```

Normal write flow:

```text
edit_mode on
  -> entity control
  -> queue command
  -> IDLE starts write
  -> WAIT_WRITE
  -> read 0x60 to commit
  -> WAIT_SAVE
  -> publish written value
  -> IDLE
```

Locked write flow:

```text
edit_mode off
  -> entity control
  -> log ignored write
  -> no serial write
```

Filter-reset write flow:

```text
button press
  -> write 0x54 = 1
  -> WAIT_WRITE
  -> read 0x60 to commit
  -> WAIT_SAVE
  -> read 0x53
  -> WAIT_FILTER_RUNTIME_READBACK
  -> publish actual device value
  -> IDLE
```

Connection retry flow:

```text
read register
  -> timeout
  -> status warning
  -> mark application disconnected
  -> drop queued configuration writes
  -> wait 2 seconds
  -> reset controller and re-probe 0xFF
```

## Refresh Set

The refresh loop reads the registers that back exposed entities, in this order:

| Group | Registers |
| --- | --- |
| Runtime inputs | `0x50`, `0x51`, `0x40`, `0x41`, `0x52` |
| Bypass state/config | `0x30`, `0x31`, `0x32` |
| Filter and thresholds | `0x53`, `0x55`, `0x70`, `0x72` |
| Inflow speed setpoints | `0x10`..`0x15` |
| Outflow speed setpoints | `0x20`..`0x25` |

`0xFF` is read during connection only, because the firmware version should not
change while running.

## Adding Entities

When adding another register:

1. Update root `PROTOCOLS.md` first.
2. Add or confirm the register constant in `ventilation_unit.h`.
3. Add the YAML key and schema in `__init__.py`.
4. Wire the generated entity to the component in `to_code`.
5. Add the register to `REFRESH_REGS` if it is read-backed.
6. Decode and publish it in `publish_register_`.
7. For writable values, choose the correct scale and whether the write should
   commit through `0x60`.
