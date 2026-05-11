#!/usr/bin/env python3
"""Small ventilation-unit CLI.

This talks only to the running application firmware. It does not use the STM32
ROM bootloader protocol.

Startup sequence:
  1. Open CP210x serial at 38400 8N1.
  2. Drive RTS low so BOOT0 is not requested.
  3. Pulse DTR to reset the MCU into flash application code.
  4. Poll application register 0xFF.

Application protocol:
  Read:   FF 01 rr       -> two response bytes, big-endian uint16
  Write:  FF 00 rr hh ll -> no response

Requires:
  pip install pyserial
"""

from __future__ import annotations

import argparse
import json
import math
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime

try:
    import serial
except ModuleNotFoundError:
    serial = None

SERIAL_EXCEPTION = serial.SerialException if serial is not None else OSError


BAUD = 38400
TIMEOUT = 1.0
INTER_BYTE_DELAY = 0.002

REG_COMMIT_CONFIG_TO_FLASH = 0x60

SETPOINT_REGS = {
    0x10, 0x11, 0x12, 0x13, 0x14, 0x15,
    0x20, 0x21, 0x22, 0x23, 0x24, 0x25,
}

DECODE_DISPLAY_KEYS = (
    "version",
    "setpoint_percent",
    "rpm",
    "voltage",
    "humidity_percent",
    "temperature_c",
    "filter_hours",
    "filter_interval_hours",
    "threshold_c",
    "threshold_percent",
    "state",
    "present",
    "polarity",
    "delay_ticks",
)


@dataclass(frozen=True)
class Register:
    addr: int
    name: str
    access: str
    note: str = ""
    min_value: int | None = None
    max_value: int | None = None
    raw_min_value: int | None = None
    raw_max_value: int | None = None
    raw_scale: float = 1.0
    unit_suffix: str = ""
    integer_display: bool = True
    force_required: bool = False

    @property
    def readable(self) -> bool:
        return "R" in self.access

    @property
    def writable(self) -> bool:
        return "W" in self.access

    @property
    def display_range(self) -> tuple[int | None, int | None]:
        return self.min_value, self.max_value

    @property
    def raw_range(self) -> tuple[int | None, int | None]:
        return (
            self.min_value if self.raw_min_value is None else self.raw_min_value,
            self.max_value if self.raw_max_value is None else self.raw_max_value,
        )

    def format_display_value(self, value: float | int) -> str:
        return f"{format_number(value)}{self.unit_suffix}"


def setpoint_register(addr: int, name: str) -> Register:
    return Register(
        addr,
        name,
        "R/W",
        "percent 0..100; raw setpoint = percent * 10",
        0,
        100,
        0,
        1000,
        10.0,
        "%",
        False,
    )


def boolean_register(addr: int, name: str, note: str) -> Register:
    return Register(addr, name, "R/W", note, 0, 1)


REGISTERS = [
    setpoint_register(0x10, "inflow_standby_setpoint"),
    setpoint_register(0x11, "inflow_speed_1_setpoint"),
    setpoint_register(0x12, "inflow_speed_2_setpoint"),
    setpoint_register(0x13, "inflow_speed_3_setpoint"),
    setpoint_register(0x14, "inflow_force_input_setpoint"),
    setpoint_register(0x15, "inflow_humidity_boost_setpoint"),
    setpoint_register(0x20, "outflow_standby_setpoint"),
    setpoint_register(0x21, "outflow_speed_1_setpoint"),
    setpoint_register(0x22, "outflow_speed_2_setpoint"),
    setpoint_register(0x23, "outflow_speed_3_setpoint"),
    setpoint_register(0x24, "outflow_force_input_setpoint"),
    setpoint_register(0x25, "outflow_humidity_boost_setpoint"),
    boolean_register(
        0x30,
        "bypass",
        "0=closed, 1=open; USB write does not actuate damper",
    ),
    boolean_register(0x31, "bypass_hardware_present", "0=no, 1=yes"),
    boolean_register(0x32, "bypass_polarity_invert", "0=normal, 1=inverted"),
    Register(
        0x40,
        "inflow_rpm",
        "R",
        "rpm = value * 60 / ppr",
    ),
    Register(
        0x41,
        "outflow_rpm",
        "R",
        "rpm = value * 60 / ppr",
    ),
    Register(
        0x50,
        "humidity_sensor_input",
        "R",
        "0-10 V sensor; voltage = value / 333; humidity = value / 33",
    ),
    Register(0x51, "temperature", "R", "temp_C = value - 40"),
    Register(0x52, "force_input_state", "R"),
    Register(0x53, "filter_runtime", "R", "hours = value / 6"),
    Register(0x54, "filter_replacement_reset", "W", "write-only clear command", 1, 1),
    Register(
        0x55,
        "filter_replacement_interval",
        "R/W",
        "hours 1..9999; raw value = hours * 6",
        1,
        9999,
        6,
        59994,
        6.0,
        " hours",
    ),
    Register(
        0x60,
        "commit_config_to_flash",
        "R",
        "read has side effect: commits config to flash",
    ),
    Register(
        0x70,
        "freeze_protection_threshold",
        "R/W",
        "app range 1..31 C",
        1,
        31,
        unit_suffix=" C",
    ),
    Register(
        0x72,
        "humidity_boost_threshold",
        "R/W",
        "app range 30..80%",
        30,
        80,
        unit_suffix="%",
    ),
    Register(
        0x80,
        "unused_80",
        "R/W",
        "persisted; no firmware consumer found",
        force_required=True,
    ),
    Register(
        0x81,
        "unused_81",
        "R/W",
        "persisted; no firmware consumer found",
        force_required=True,
    ),
    Register(
        0x82,
        "unused_82",
        "R/W",
        "persisted; no firmware consumer found",
        force_required=True,
    ),
    Register(
        0x83,
        "fan_output_change_delay",
        "R/W",
        "fan output delay in update ticks",
    ),
    Register(
        0x90,
        "fan_output_override",
        "W",
        "volatile; write 0 for normal outputs",
        0,
        0,
    ),
    Register(0xFF, "firmware_version", "R/W", force_required=True),
]

REGISTER_BY_ADDR = {register.addr: register for register in REGISTERS}
REGISTER_BY_NAME = {register.name: register for register in REGISTERS}
NAME_COLUMN_WIDTH = max(len(register.name) for register in REGISTERS)

# Safe bulk reads exclude registers that are write-only or have read side effects.
SAFE_READ_REGISTERS = [
    register
    for register in REGISTERS
    if register.readable and register.addr != REG_COMMIT_CONFIG_TO_FLASH
]


class VentError(RuntimeError):
    pass


def parse_int(text: str) -> int:
    return int(text, 0)


def parse_number(text: str) -> float:
    try:
        value = float(parse_int(text))
    except ValueError:
        value = float(text)
    if not math.isfinite(value):
        raise argparse.ArgumentTypeError("value must be finite")
    return value


def parse_register(text: str) -> Register:
    key = text.lower()
    if key in REGISTER_BY_NAME:
        return REGISTER_BY_NAME[key]
    try:
        addr = parse_int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"unknown register {text!r}") from exc
    if not 0 <= addr <= 0xFF:
        raise argparse.ArgumentTypeError("register must be in range 0..0xff")
    return REGISTER_BY_ADDR.get(
        addr,
        Register(
            addr,
            f"reg_{addr:02x}",
            "?",
            "unknown register; use --raw --force for direct raw access",
            force_required=True,
        ),
    )


def coerce_write_value(
    register: Register,
    value: float,
    *,
    force: bool,
    raw: bool,
) -> int:
    if register.force_required and not raw:
        raise VentError(f"{register.name} is advanced/raw-only; use --raw to write it")
    if register.force_required and not force:
        raise VentError(f"{register.name} is advanced/raw-only; use --force to write it")
    if not register.writable and not force:
        raise VentError(
            f"{register.name} is not marked writable; use --force to try anyway"
        )

    if raw:
        raw_value = require_integer(value, "raw register value")
    else:
        validate_display_value(register, value, force=force)
        raw_value = display_to_raw_value(register, value)

    validate_raw_value(register, raw_value, force=force)
    return raw_value


def display_to_raw_value(register: Register, value: float) -> int:
    if register.integer_display:
        value = require_integer(value, register.name)
    raw_value = value * register.raw_scale
    if not raw_value.is_integer():
        raise VentError(
            f"{register.name} maps to fractional raw value {raw_value}; "
            "use --raw for exact register access"
        )
    return int(raw_value)


def validate_display_value(register: Register, value: float, *, force: bool) -> None:
    if force:
        return
    min_value, max_value = register.display_range
    if min_value is not None and value < min_value:
        raise VentError(
            f"{register.name} should be >= "
            f"{register.format_display_value(min_value)}; use --force to override"
        )
    if max_value is not None and value > max_value:
        raise VentError(
            f"{register.name} should be <= "
            f"{register.format_display_value(max_value)}; use --force to override"
        )


def validate_raw_value(register: Register, raw_value: int, *, force: bool) -> None:
    if not 0 <= raw_value <= 0xFFFF:
        raise VentError("register value must be in range 0..0xffff")
    if force:
        return
    min_value, max_value = register.raw_range
    if min_value is not None and raw_value < min_value:
        raise VentError(
            f"{register.name} raw value should be >= {min_value}; "
            "use --force to override"
        )
    if max_value is not None and raw_value > max_value:
        raise VentError(
            f"{register.name} raw value should be <= {max_value}; "
            "use --force to override"
        )


def require_integer(value: float, label: str) -> int:
    if not value.is_integer():
        raise VentError(f"{label} must be an integer")
    return int(value)


def format_number(value: float | int) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def suppress_hupcl(ser: serial.Serial) -> None:
    try:
        import termios

        attrs = termios.tcgetattr(ser.fileno())
        attrs[2] &= ~termios.HUPCL
        termios.tcsetattr(ser.fileno(), termios.TCSANOW, attrs)
    except (ImportError, AttributeError, OSError):
        pass


def write_byte(ser: serial.Serial, value: int) -> None:
    ser.write(bytes([value & 0xFF]))
    time.sleep(INTER_BYTE_DELAY)


def drain(ser: serial.Serial, timeout: float = 0.05) -> bytes:
    old_timeout = ser.timeout
    ser.timeout = timeout
    data = bytearray()
    while True:
        chunk = ser.read(256)
        if not chunk:
            break
        data.extend(chunk)
    ser.timeout = old_timeout
    return bytes(data)


def reset_into_app(ser: serial.Serial, reset_low: float, boot_wait: float) -> None:
    ser.rts = False  # BOOT0 low: select user flash/application
    ser.dtr = True  # NRST low: hold MCU in reset
    time.sleep(reset_low)
    ser.dtr = False  # NRST released/high: boot with BOOT0 sampled low
    time.sleep(boot_wait)
    drain(ser)


def read_register(ser: serial.Serial, reg: int) -> int:
    write_byte(ser, 0xFF)
    write_byte(ser, 0x01)
    write_byte(ser, reg)
    data = ser.read(2)
    if len(data) != 2:
        raise VentError(f"register 0x{reg:02X}: expected 2 bytes, got {len(data)}")
    return int.from_bytes(data, "big")


def write_register(ser: serial.Serial, reg: int, value: int) -> None:
    if not 0 <= value <= 0xFFFF:
        raise VentError("register value must be in range 0..0xffff")
    write_byte(ser, 0xFF)
    write_byte(ser, 0x00)
    write_byte(ser, reg)
    write_byte(ser, value >> 8)
    write_byte(ser, value)


def wait_for_app(ser: serial.Serial, timeout: float) -> int:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        drain(ser)
        try:
            return read_register(ser, 0xFF)
        except Exception as exc:
            last_error = exc
            time.sleep(0.1)
    raise VentError(f"application did not answer register 0xFF: {last_error}")


def decode_value(reg: int, value: int, ppr: int) -> dict[str, float | int | str]:
    decoded: dict[str, float | int | str] = {}
    if reg in SETPOINT_REGS:
        decoded["setpoint_percent"] = value / 10.0
    elif reg == 0x30:
        decoded["state"] = "open" if value else "closed"
    elif reg == 0x31:
        decoded["present"] = "yes" if value else "no"
    elif reg == 0x32:
        decoded["polarity"] = "inverted" if value else "normal"
    elif reg in (0x40, 0x41):
        decoded["rpm"] = value * 60.0 / ppr
    elif reg == 0x50:
        decoded["voltage"] = value / 333.0
        # Match the official app's direct raw-value scaling. This is roughly
        # the usual 0-10 V => 0-100% convention, but not exactly voltage * 10.
        decoded["humidity_percent"] = value / 33.0
    elif reg == 0x51:
        decoded["temperature_c"] = value - 40
    elif reg == 0x52:
        decoded["state"] = "active" if value else "inactive"
    elif reg == 0x53:
        decoded["filter_hours"] = value / 6.0
    elif reg == 0x55:
        decoded["filter_interval_hours"] = value / 6.0
    elif reg == 0x70:
        decoded["threshold_c"] = value
    elif reg == 0x72:
        decoded["threshold_percent"] = value
    elif reg == 0x83:
        decoded["delay_ticks"] = value
    elif reg == 0x90:
        decoded["state"] = "override" if value else "normal"
    elif reg == 0xFF:
        decoded["version"] = f"{value >> 8}.{value & 0xFF}"
    return decoded


def format_decoded_value(value: object) -> str:
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else f"{value:.2f}"
    return str(value)


def format_row(item: dict[str, object]) -> str:
    extra = ""
    for key in DECODE_DISPLAY_KEYS:
        if key in item:
            extra += f"  {key}={format_decoded_value(item[key])}"
    return (
        f"{item['register']:>4}  {item['name']:<{NAME_COLUMN_WIDTH}} "
        f"{item['access']:<3}  {item['value']:>5}  {item['hex']}{extra}"
    )


def open_serial(port: str) -> serial.Serial:
    if serial is None:
        raise VentError("pyserial is not installed; run: pip install pyserial")
    ser = serial.Serial(
        port=port,
        baudrate=BAUD,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=TIMEOUT,
        write_timeout=TIMEOUT,
    )
    ser.rts = False
    ser.dtr = False
    suppress_hupcl(ser)
    return ser


def connect(args: argparse.Namespace) -> serial.Serial:
    ser = open_serial(args.port)
    if not args.no_reset:
        reset_into_app(ser, args.reset_low, args.boot_wait)
    wait_for_app(ser, args.app_timeout)
    return ser


def make_item(register: Register, value: int, ppr: int) -> dict[str, object]:
    return {
        "register": f"0x{register.addr:02X}",
        "name": register.name,
        "access": register.access,
        "value": value,
        "hex": f"0x{value:04X}",
        "note": register.note,
        **decode_value(register.addr, value, ppr),
    }


def sample_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_items(ser: serial.Serial, registers: list[Register], ppr: int) -> list[dict[str, object]]:
    return [
        make_item(register, read_register(ser, register.addr), ppr)
        for register in registers
    ]


def print_items(items: list[dict[str, object]], args: argparse.Namespace, timestamp: str | None) -> None:
    if args.json:
        if timestamp is None:
            print(json.dumps(items[0] if len(items) == 1 else items, indent=2))
        else:
            print(json.dumps({"timestamp": timestamp, "registers": items}))
        sys.stdout.flush()
        return

    if args.interactive:
        print("\033[H\033[J", end="")

    if timestamp is not None:
        print(timestamp)
    for item in items:
        print(format_row(item))
    if args.interval is not None and not args.interactive:
        print()
    sys.stdout.flush()


def poll_items(
    ser: serial.Serial,
    registers: list[Register],
    args: argparse.Namespace,
) -> int:
    if args.interval is None:
        print_items(read_items(ser, registers, args.ppr), args, None)
        return 0

    stop_requested = False

    def request_stop(signum: int, frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, request_stop)
    while not stop_requested:
        print_items(read_items(ser, registers, args.ppr), args, sample_timestamp())
        deadline = time.monotonic() + args.interval
        while not stop_requested and time.monotonic() < deadline:
            time.sleep(min(0.1, deadline - time.monotonic()))
    return 130 if stop_requested else 0


def command_read_all(args: argparse.Namespace) -> int:
    ser = connect(args)
    try:
        return poll_items(ser, SAFE_READ_REGISTERS, args)
    finally:
        ser.close()


def command_read(args: argparse.Namespace) -> int:
    register = args.register
    if register.addr == REG_COMMIT_CONFIG_TO_FLASH and not args.allow_side_effect:
        raise VentError("0x60 commits config to flash; use --allow-side-effect to read it")
    if not register.readable and not args.force:
        raise VentError(f"{register.name} is not marked readable; use --force to try anyway")

    ser = connect(args)
    try:
        return poll_items(ser, [register], args)
    finally:
        ser.close()


def command_write(args: argparse.Namespace) -> int:
    register = args.register
    write_value = coerce_write_value(
        register,
        args.value,
        force=args.force,
        raw=args.raw,
    )

    ser = connect(args)
    try:
        write_register(ser, register.addr, write_value)
        result: dict[str, object] = {
            "register": f"0x{register.addr:02X}",
            "name": register.name,
            "written": write_value,
            "written_hex": f"0x{write_value:04X}",
        }
        if not args.raw:
            result["input_value"] = args.value
        if args.verify:
            if not register.readable:
                raise VentError(f"{register.name} is write-only; cannot verify")
            time.sleep(0.05)
            result["readback"] = read_register(ser, register.addr)
            result["readback_hex"] = f"0x{result['readback']:04X}"
        if args.save:
            result["save_response"] = read_register(ser, REG_COMMIT_CONFIG_TO_FLASH)
            result["save_response_hex"] = f"0x{result['save_response']:04X}"

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(
                f"wrote {result['written_hex']} to {result['register']} "
                f"({result['name']})"
            )
            if "input_value" in result:
                print(f"input {register.format_display_value(result['input_value'])}")
            if "readback_hex" in result:
                print(f"readback {result['readback_hex']}")
            if "save_response_hex" in result:
                print(f"save response {result['save_response_hex']}")
        return 0
    finally:
        ser.close()


def add_connection_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("port", metavar="SERIAL_PORT", help="Serial port path or device name")
    parser.add_argument("--no-reset", action="store_true", help="Assume app is already running")
    parser.add_argument("--reset-low", type=float, default=0.4, help="DTR reset pulse seconds")
    parser.add_argument("--boot-wait", type=float, default=0.8, help="Seconds to wait after reset")
    parser.add_argument("--app-timeout", type=float, default=3.0, help="Seconds to wait for app")
    parser.add_argument("--ppr", type=int, default=1, help="Pulses per revolution for RPM display")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")


def add_poll_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--interval",
        type=float,
        help="Poll repeatedly every N seconds; appends samples by default",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Refresh the same terminal view while polling; implies --interval 1",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ventilation unit application-protocol CLI")
    subcommands = parser.add_subparsers(dest="command")

    read_all = subcommands.add_parser("read-all", help="Read all safe confirmed registers")
    add_connection_args(read_all)
    add_poll_args(read_all)
    read_all.set_defaults(func=command_read_all)

    read = subcommands.add_parser("read", help="Read one register")
    add_connection_args(read)
    add_poll_args(read)
    read.add_argument("register", type=parse_register, help="Register address or known name")
    read.add_argument("--allow-side-effect", action="store_true", help="Allow reading 0x60 save trigger")
    read.add_argument("--force", action="store_true", help="Try even if register is not marked readable")
    read.set_defaults(func=command_read)

    write = subcommands.add_parser("write", help="Write one register")
    add_connection_args(write)
    write.add_argument("register", type=parse_register, help="Register address or known name")
    write.add_argument(
        "value",
        type=parse_number,
        help="Value in display units by default, or a raw 16-bit value with --raw",
    )
    write.add_argument(
        "--raw",
        action="store_true",
        help="Treat value as the exact raw 16-bit register value",
    )
    write.add_argument("--verify", action="store_true", help="Read the register back after writing")
    write.add_argument("--save", action="store_true", help="Persist config by reading 0x60 after writing")
    write.add_argument("--force", action="store_true", help="Try even if register is not marked writable")
    write.set_defaults(func=command_write)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 2
    if args.ppr < 1:
        parser.error("--ppr must be >= 1")
    if hasattr(args, "interval"):
        if args.interactive and args.interval is None:
            args.interval = 1.0
        if args.interval is not None and args.interval <= 0:
            parser.error("--interval must be > 0")
        if args.interactive and args.json:
            parser.error("--interactive cannot be combined with --json")
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print(file=sys.stderr)
        return 130
    except (VentError, SERIAL_EXCEPTION) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
