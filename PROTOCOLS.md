# Ventilation Unit Protocol Notes

Reverse-engineered notes for the STM32F100 controller firmware and the
official Windows service application used by the Vents VUT 250 VB EC A14
ventilation unit.

The unit has two application-level serial links:

- USB/PC control via a CP210x USB-to-UART bridge.
- Front panel/control-board UART.

## Serial Links

| Link | MCU peripheral | Pins | Settings | Purpose |
| --- | --- | --- | --- | --- |
| USB/PC | USART1, `0x40013800` | PA9 TX, PA10 RX | 38400 8N1 | Register read/write protocol used by the Windows app |
| Panel | USART2, `0x40004400` | PA2 TX, PA3 RX | 600 8N1 | One-byte panel command/status protocol |

The firmware configures both UARTs for 8 data bits, no parity, 1 stop bit, RX
and TX enabled. No hardware flow control was found.

No UART polarity inversion was found in the firmware. The panel link is
configured as a normal STM32 USART2 peripheral: PA2 is alternate-function
push-pull TX, PA3 is floating RX, and the USART is initialized at 600 baud.

## USB/PC Register Protocol

The PC protocol is byte-oriented. The official app sends bytes as separate USB
serial writes; a reimplementation should keep a small inter-byte delay such as
2 ms.

### Read Register

Request:

```text
FF 01 rr
```

Response:

```text
hh ll
```

The response is a 16-bit big-endian value.

### Write Register

Request:

```text
FF 00 rr hh ll
```

There is no response. The written value is a 16-bit big-endian value.

Unsupported reads return `0x0000`. Unsupported writes are ignored but still set
the firmware's internal dirty flag.

### Register Map

| Register | Canonical name | Access | Firmware default | Meaning |
| --- | --- | --- | ---: | --- |
| `0x10` | `inflow_standby_setpoint` | R/W | 0 | Inflow setpoint, panel mode 0 / standby |
| `0x11` | `inflow_speed_1_setpoint` | R/W | 400 | Inflow setpoint, panel mode 1 |
| `0x12` | `inflow_speed_2_setpoint` | R/W | 700 | Inflow setpoint, panel mode 2 |
| `0x13` | `inflow_speed_3_setpoint` | R/W | 1000 | Inflow setpoint, panel mode 3 |
| `0x14` | `inflow_force_input_setpoint` | R/W | 1000 | Inflow force-input setpoint |
| `0x15` | `inflow_humidity_boost_setpoint` | R/W | 1000 | Inflow humidity-boost minimum setpoint |
| `0x20` | `outflow_standby_setpoint` | R/W | 0 | Outflow setpoint, panel mode 0 / standby |
| `0x21` | `outflow_speed_1_setpoint` | R/W | 400 | Outflow setpoint, panel mode 1 |
| `0x22` | `outflow_speed_2_setpoint` | R/W | 700 | Outflow setpoint, panel mode 2 |
| `0x23` | `outflow_speed_3_setpoint` | R/W | 1000 | Outflow setpoint, panel mode 3 |
| `0x24` | `outflow_force_input_setpoint` | R/W | 1000 | Outflow force-input setpoint |
| `0x25` | `outflow_humidity_boost_setpoint` | R/W | 1000 | Outflow humidity-boost minimum setpoint |
| `0x30` | `bypass` | R/W | 0 | Current bypass state/readback; USB writes do not actuate the damper |
| `0x31` | `bypass_hardware_present` | R/W | 1 | Bypass hardware present |
| `0x32` | `bypass_polarity_invert` | R/W | 1 | Bypass polarity/invert |
| `0x40` | `inflow_rpm` | R | runtime | Inflow fan tachometer value; display RPM = raw * 60 / PPR |
| `0x41` | `outflow_rpm` | R | runtime | Outflow fan tachometer value; display RPM = raw * 60 / PPR |
| `0x50` | `humidity_sensor_input` | R | runtime | 0-10 V humidity sensor input; displayed as both voltage and humidity level |
| `0x51` | `temperature` | R | runtime | Temperature value, stored as degrees C + 40 |
| `0x52` | `force_input_state` | R | runtime | Force input indicator / derived force state |
| `0x53` | `filter_runtime` | R | runtime | Filter runtime counter, `hours = raw / 6` |
| `0x54` | `filter_replacement_reset` | W | n/a | Filter replacement reset command: clears `0x53` |
| `0x55` | `filter_replacement_interval` | R/W | 52560 | Filter replacement interval, `hours = raw / 6`; app range 1-9999 hours |
| `0x60` | `commit_config_to_flash` | R | n/a | Special command: commits config to flash, returns `0xFFFF` |
| `0x70` | `freeze_protection_threshold` | R/W | 3 | Freeze/frost protection threshold, degrees C; app range 1-31 C |
| `0x72` | `humidity_boost_threshold` | R/W | 60 | Humidity boost threshold, percent RH; app range 30-80 |
| `0x80` | `unused_80` | R/W | 3540 | Persisted register; no firmware consumer found |
| `0x81` | `unused_81` | R/W | 3540 | Persisted register; no firmware consumer found |
| `0x82` | `unused_82` | R/W | 150 | Persisted register; no firmware consumer found |
| `0x83` | `fan_output_change_delay` | R/W | 20 | Fan output change delay, in output-update ticks |
| `0x90` | `fan_output_override` | W | volatile 0 | Fan-output override/test flag; write `0` to ensure normal operation |
| `0xFF` | `firmware_version` | R/W | `0x0204` | Firmware/config version |

### Firmware Defaults

The table above lists the compiled fallback defaults. On startup, the firmware
initializes RAM with those fallback values, then checks the flash config block.
If the block is valid, saved values replace the fallbacks. If the block is
blank, the firmware saves the fallback values to flash.

For an already-configured unit, values read over USB can differ from these
defaults because the saved flash config overrides them.

### Speed Setpoints

Fan setpoints use a 0-1000 scale:

```text
0    = 0%
400  = 40%
700  = 70%
1000 = 100%
```

The active normal ventilation mode is selected by the panel byte, not by a USB
register. The firmware selects setpoints as follows:

| Panel mode | Inflow register | Outflow register |
| ---: | --- | --- |
| 0 | `0x10` | `0x20` |
| 1 | `0x11` | `0x21` |
| 2 | `0x12` | `0x22` |
| 3 | `0x13` | `0x23` |

The force input and humidity logic can raise the selected setpoints to the
force or humidity boost setpoints.

### Bypass Registers

Register `0x30` exposes the current bypass state and can be written through the
USB register handler, but that write only changes the register backing value. It
does not call the damper open/close routines and does not actuate the physical
bypass damper.

The firmware calls the damper open/close routines from the panel command logic
when panel bit 3 changes. That path then updates the `0x30` backing value.

For bypass control, drive panel command bit `0x08`. Use register `0x30` as
state/readback only.

Registers `0x31` and `0x32` are configuration values:

- `0x31`: bypass hardware present/enabled.
- `0x32`: bypass polarity/invert.

### Filter Runtime Counter

The firmware treats `0x53` and `0x55` as raw counters. It does not count down,
and it does not convert the values to hours internally. The official Windows app
displays/edits these values as hours using:

```text
filter_hours = raw / 6
filter_raw = filter_hours * 6
```

The Windows app confirms the write-side filter conversion by parsing the filter
hours field and multiplying it by `6` before storing the raw value. Its accepted
UI range is `1..9999` hours, corresponding to raw values `6..59994`; out-of-range
high input is clamped to `59994`.

The firmware timer setup suggests one raw unit is 10 minutes, matching the app
conversion of six raw units per hour. Any display as hours/months is
consumer-side interpretation; the firmware register logic compares raw values.

### Tachometer Calculation

Registers `0x40` and `0x41` expose averaged pulse counters. The firmware does
not divide by pulses-per-revolution. The Windows app's "resolution/PPR" setting
appears to be client-side display scaling.

For PPR = 1:

```text
RPM = tach_value * 60
```

For another PPR value:

```text
RPM = tach_value * 60 / PPR
```

### Humidity Input Calculation

Register `0x50` is the humidity sensor input value. The official app uses it
for both the humidity readout and the manual's "Voltage: current voltage level
at the 0-10 V input" diagnostic readout.

The official Windows app displays this value as:

```text
voltage_V = raw_0x50 / 333.0
```

The app also derives the displayed humidity percentage from the same raw value:

```text
humidity_percent = raw_0x50 / 33
```

This is effectively the common 0-10 V sensor convention:

```text
0 V  ~= 0% RH
10 V ~= 100% RH
humidity_percent ~= voltage_V * 10
```

The formulas are not exactly identical because the Windows app uses integer
divisors `333` and `33` directly.

### Humidity Boost

The firmware humidity-boost decision uses the same ADC-derived signal as
register `0x50` and the threshold in register `0x72`. Internally it compares
`raw_0x50 / 3` against `reg_0x72 * 11`, which is equivalent to comparing
`raw_0x50 / 33` against the threshold percentage.

```text
boost_on  when raw_0x50 / 3 >  reg_0x72 * 11
boost_off when raw_0x50 / 3 <= (reg_0x72 - 4) * 11
```

When humidity boost is active, the selected fan setpoints are raised to at
least the humidity-boost setpoints. These registers are setpoints used while
boost is active; they are not ventilation modes:

| Fan | Humidity-boost setpoint |
| --- | --- |
| Inflow | `0x15` |
| Outflow | `0x25` |

### Temperature

Register `0x51` exposes the firmware's temperature value. The value is stored
with a `+40` offset:

```text
temperature_C = reg_0x51 - 40
```

For example, a register value of `53` means:

```text
temperature_C = 53 - 40 = 13 C
```

The `+40` offset is only a signed temperature encoding.

### Registers 0x80-0x83

Registers `0x80`, `0x81`, and `0x82` are exposed by the USB register
read/write handler and are included in the flash-persisted configuration block,
but no firmware logic was found that reads their backing RAM variables.

Register `0x83` is used by the fan output update function. When either computed
fan setpoint changes, the firmware reloads an internal delay counter from
`0x83`. While that counter is nonzero, the previous PWM output is held; after it
counts down, the new setpoint is applied.

### Saving Configuration

Most writes update RAM only. To persist configuration, read register `0x60`.
The firmware persists writable configuration and returns `0xFFFF`.

No user-accessible factory reset command was found in the application protocol.

`0x90` is not saved to flash. It is a volatile output override/test flag:

- `0x90 == 0`: normal computed fan outputs.
- `0x90 != 0`: firmware forces one PWM path to 1000 in the output update code.

The Windows app writes `0x90 = 0` continuously. A reimplementation can safely
skip the heartbeat if it never writes `0x90` nonzero; writing `0x90 = 0` once on
connect is a reasonable defensive cleanup.

## Panel Protocol

The panel link is a separate 600 baud UART protocol. It is not the USB register
protocol.

The firmware receives one byte from the panel, debounces it, interprets it as a
bitfield, and sends one status byte back.

### Panel Command Byte

| Bits | Mask | Meaning |
| --- | --- | --- |
| 0-1 | `0x03` | Active ventilation mode: 0, 1, 2, or 3 |
| 2 | `0x04` | Service/filter timer reset request, acted on only when service is due |
| 3 | `0x08` | Bypass command: 0 = closed/normal, 1 = open |
| 4-7 | `0xF0` | No application use found |

Common command bytes:

| Byte | Meaning |
| ---: | --- |
| `0x00` | Mode 0, bypass closed |
| `0x01` | Mode 1, bypass closed |
| `0x02` | Mode 2, bypass closed |
| `0x03` | Mode 3, bypass closed |
| `0x08` | Mode 0, bypass open |
| `0x09` | Mode 1, bypass open |
| `0x0A` | Mode 2, bypass open |
| `0x0B` | Mode 3, bypass open |
| `0x04`..`0x07` | Same modes, plus service reset request |
| `0x0C`..`0x0F` | Same modes with bypass open, plus service reset request |

### Command Repeat Cadence

The firmware debounces panel command changes with a stability counter. When the
received byte matches the currently accepted command, the counter increments up
to 10. When a different byte arrives while the counter is nonzero, the counter
is decremented and the old accepted command is still used. The new command is
accepted only after enough repeated different bytes have counted the stability
down to zero; the firmware then stores the new byte and reloads the counter to
10.

This means a replacement panel or bridge should repeat the current command byte
continuously, not only send it once on change. A 1 second cadence can make mode
or bypass changes take roughly 10 seconds to apply. Repeating every 100 ms gives
about a 1 second worst-case command-change latency while leaving ample margin on
the 600 baud UART.

### Panel Status Byte

The firmware sends:

```text
status = status_bit_1 | status_bit_0
```

Observed meanings:

| Bit | Mask | Meaning |
| --- | --- | --- |
| 0 | `0x01` | Service/filter timer due |
| 1 | `0x02` | Blinking/alarm indicator, toggled for sensor/communication/fan-health conditions |

## Entering the Application

The application protocol is available after the MCU boots from flash. On this
unit, CP210x control lines are wired so that:

| pyserial state | MCU pin state | Meaning |
| --- | --- | --- |
| `rts = True` | `BOOT0` high | Select STM32 system bootloader on reset release |
| `rts = False` | `BOOT0` low | Select user flash/application on reset release |
| `dtr = True` | `NRST` low | Reset asserted; MCU is held in reset |
| `dtr = False` | `NRST` released/high | Reset released; MCU runs/boots |

A minimal connection sequence is:

1. Open the serial port at `38400 8N1`.
2. Set `RTS = false` so `BOOT0` is low.
3. Pulse reset with `DTR = true` (`NRST` low), wait about `400 ms`, then
   `DTR = false` (`NRST` released/high).
4. Wait about `800 ms` for the application to boot.
5. Poll register `0xFF` with `FF 01 FF`; a two-byte response confirms the
   application protocol is active.

No STM32 bootloader command is required to enter the application when BOOT0 is
low.
