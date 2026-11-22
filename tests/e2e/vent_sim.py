"""Simulated Vents controller links for host-platform end-to-end tests (per docs/PROTOCOL.md).

- `UnitSim`: the USB/PC register protocol (38400 8N1). Read `FF 01 rr` -> `hh ll`; write
  `FF 00 rr hh ll` (no reply, RAM only); reading 0x60 commits to flash and returns 0xFFFF; writing
  0x54 clears the filter runtime counter 0x53; unsupported reads return 0x0000 and writes to
  read-only or unsupported registers are ignored. The CP210X reset lines aren't modelled (a pty
  has no modem lines).
- `PanelSide` / `ControllerSide`: the 600-baud one-byte panel protocol, from the two ends the
  bridge sits between. The panel sends command bytes (mode bits 0-1, service reset bit 2, bypass
  bit 3); the controller answers with a status byte (bit 0 filter due, bit 1 alarm). The
  controller's debounce over ~10 repeated command bytes isn't modelled.

These encode our understanding of the protocol, so they catch regressions in the components but
can't prove the protocol model itself is right.
"""

from __future__ import annotations

from collections.abc import Callable
import contextlib
from dataclasses import dataclass, field
import os
from pathlib import Path
import select
import threading
import tty

# Firmware fallback defaults (docs/PROTOCOL.md register map) plus plausible runtime values.
DEFAULT_REGS: dict[int, int] = {
    0x10: 0,
    0x11: 400,
    0x12: 700,
    0x13: 1000,
    0x14: 1000,
    0x15: 1000,
    0x20: 0,
    0x21: 400,
    0x22: 700,
    0x23: 1000,
    0x24: 1000,
    0x25: 1000,
    0x30: 0,
    0x31: 1,
    0x32: 1,
    0x40: 25,  # 1500 RPM
    0x41: 24,  # 1440 RPM
    0x50: 1650,  # 4.95 V / 50.0 %
    0x51: 61,  # 21 °C
    0x52: 0,
    0x53: 6000,  # 1000 h
    0x55: 52560,  # 8760 h
    0x70: 3,
    0x72: 60,
    0xFF: 0x0204,
}
# Registers a USB write changes (docs/PROTOCOL.md, access R/W or W). Others are ignored.
WRITABLE_REGS = frozenset(
    [*range(0x10, 0x16), *range(0x20, 0x26), 0x30, 0x31, 0x32, 0x55, 0x70, 0x72]
    + [0x80, 0x81, 0x82, 0x83, 0x90, 0xFF]
)
REG_FILTER_RUNTIME = 0x53
REG_FILTER_RESET = 0x54
REG_COMMIT = 0x60


class Pty:
    """A pty pair whose terminal end is symlinked at `link_path`; `on_data` gets bytes the firmware
    writes, `write()` sends bytes to it."""

    def __init__(self, link_path: Path, on_data: Callable[[bytes], None]) -> None:
        self.link_path = link_path
        self.on_data = on_data
        self.ctrl_fd, self.uart_fd = os.openpty()
        tty.setraw(self.ctrl_fd)
        tty.setraw(self.uart_fd)
        if link_path.is_symlink() or link_path.exists():
            link_path.unlink()
        self.tty_name = os.ttyname(self.uart_fd)
        link_path.symlink_to(self.tty_name)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def write(self, data: bytes) -> None:
        os.write(self.ctrl_fd, data)

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)
        for fd in (self.ctrl_fd, self.uart_fd):
            with contextlib.suppress(OSError):
                os.close(fd)
        # Only remove the link if it is still ours (another run may have replaced it).
        if (
            self.link_path.is_symlink()
            and str(self.link_path.readlink()) == self.tty_name
        ):
            self.link_path.unlink()

    def _run(self) -> None:
        while not self._stop.is_set():
            r, _, _ = select.select([self.ctrl_fd], [], [], 0.05)
            if not r:
                continue
            try:
                data = os.read(self.ctrl_fd, 256)
            except OSError:
                return
            if data:
                self.on_data(data)


@dataclass
class UnitSim:
    regs: dict[int, int] = field(default_factory=lambda: dict(DEFAULT_REGS))
    reads: list[int] = field(default_factory=list)
    writes: list[tuple[int, int]] = field(default_factory=list)
    commits: int = 0
    # When False the controller stays silent (simulates a dead link / app not running).
    responding: bool = True
    # Registers whose reads go unanswered (e.g. 0x60, to withhold the flash-commit acknowledgement).
    ignore_reads: set[int] = field(default_factory=set)
    lock: threading.Lock = field(default_factory=threading.Lock)
    _buf: bytearray = field(default_factory=bytearray)
    pty: Pty | None = None

    def attach(self, link_path: Path) -> UnitSim:
        self.pty = Pty(link_path, self._on_data)
        return self

    def close(self) -> None:
        if self.pty is not None:
            self.pty.close()

    def _on_data(self, data: bytes) -> None:
        self._buf += data
        while True:
            while self._buf and self._buf[0] != 0xFF:
                self._buf.pop(0)
            if len(self._buf) < 3:
                return
            op, reg = self._buf[1], self._buf[2]
            if op == 0x01:  # read
                del self._buf[:3]
                reply = self._read(reg)
                if reply is not None and self.pty is not None:
                    self.pty.write(reply)
            elif op == 0x00:  # write
                if len(self._buf) < 5:
                    return
                value = (self._buf[3] << 8) | self._buf[4]
                del self._buf[:5]
                self._write(reg, value)
            else:
                self._buf.pop(0)

    def _read(self, reg: int) -> bytes | None:
        with self.lock:
            self.reads.append(reg)
            if not self.responding or reg in self.ignore_reads:
                return None
            if reg == REG_COMMIT:
                self.commits += 1
                value = 0xFFFF
            else:
                value = self.regs.get(reg, 0)
        return bytes([value >> 8, value & 0xFF])

    def _write(self, reg: int, value: int) -> None:
        with self.lock:
            self.writes.append((reg, value))
            if not self.responding:
                return
            if reg == REG_FILTER_RESET:
                self.regs[REG_FILTER_RUNTIME] = 0
            elif reg in WRITABLE_REGS:
                self.regs[reg] = value

    def set(self, reg: int, value: int) -> None:
        with self.lock:
            self.regs[reg] = value


@dataclass
class ControllerSide:
    """The controller's panel port: records command bytes the bridge sends, answers each with
    the current status byte."""

    status: int = 0x00
    received: list[int] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    pty: Pty | None = None

    def attach(self, link_path: Path) -> ControllerSide:
        self.pty = Pty(link_path, self._on_data)
        return self

    def close(self) -> None:
        if self.pty is not None:
            self.pty.close()

    def _on_data(self, data: bytes) -> None:
        with self.lock:
            self.received.extend(data)
            status = self.status
        if self.pty is not None:
            self.pty.write(bytes([status]) * len(data))

    def last_command(self) -> int | None:
        with self.lock:
            return self.received[-1] if self.received else None


@dataclass
class PanelSide:
    """The physical front panel: sends a command byte repeatedly (like the real panel) and
    records the status bytes the bridge forwards back."""

    command: int | None = None
    received: list[int] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    pty: Pty | None = None
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None

    def attach(self, link_path: Path, period: float = 0.1) -> PanelSide:
        self.pty = Pty(link_path, self._on_data)
        self._thread = threading.Thread(target=self._send, args=(period,), daemon=True)
        self._thread.start()
        return self

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        if self.pty is not None:
            self.pty.close()

    def _send(self, period: float) -> None:
        while not self._stop.wait(period):
            cmd = self.command
            if cmd is not None and self.pty is not None:
                self.pty.write(bytes([cmd]))

    def _on_data(self, data: bytes) -> None:
        with self.lock:
            self.received.extend(data)

    def last_status(self) -> int | None:
        with self.lock:
            return self.received[-1] if self.received else None
