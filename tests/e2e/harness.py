"""Run an ESPHome `host` build as a subprocess and drive it over the native API.

Entities are addressed by name: "object_id" for entities on the node itself and
"device/object_id" for entities on a sub-device (device name slugified).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import contextlib
import fcntl
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from typing import Any

from aioesphomeapi import APIClient, EntityInfo, EntityState

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def compile_host(config: Path, substitutions: dict[str, str]) -> Path:
    """Compile a host config with the ESPHome in this Python env; return the program path."""
    args = [sys.executable, "-m", "esphome"]
    for k, v in substitutions.items():
        args += ["-s", k, v]
    args += ["compile", str(config)]
    proc = subprocess.run(
        args, cwd=config.parent, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"host compile failed:\n{proc.stdout[-6000:]}\n{proc.stderr[-3000:]}"
        )
    name = None
    for line in config.read_text(encoding="utf-8").splitlines():
        if m := re.match(r"\s+name:\s*(\S+)", line):
            name = m.group(1).strip("\"'")
            break
    program = (
        config.parent / ".esphome" / "build" / name / ".pioenvs" / name / "program"
    )
    if not program.exists():
        raise RuntimeError(f"compiled program not found at {program}")
    return program


@contextlib.contextmanager
def exclusive(lock_path: Path, timeout: float = 900.0):
    """Hold an exclusive lock for the whole test session. The host builds use a fixed API port,
    pty path and build directory, so two concurrent runs (two terminals, an editor's test runner)
    would otherwise talk to each other's nodes. A second run waits its turn instead."""
    with lock_path.open("w", encoding="utf-8") as f:
        deadline = time.monotonic() + timeout
        announced = False
        while True:
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if not announced:
                    print(
                        f"waiting for another test run to release {lock_path}",
                        file=sys.stderr,
                    )
                    announced = True
                if time.monotonic() > deadline:
                    raise RuntimeError(
                        f"another test run still holds {lock_path}"
                    ) from None
                time.sleep(0.5)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


class Node:
    def __init__(self, program: Path, api_port: int, prefdir: Path) -> None:
        self.program = program
        self.api_port = api_port
        self.prefdir = prefdir
        self.proc: subprocess.Popen[str] | None = None
        self.client: APIClient | None = None
        self.log: list[str] = []
        self.infos: dict[str, EntityInfo] = {}
        self.states: dict[str, EntityState] = {}
        self._by_key: dict[tuple[int, int], str] = {}
        self._reader: threading.Thread | None = None

    # --- lifecycle ---------------------------------------------------------------------------
    async def start(self) -> Node:
        env = dict(os.environ, ESPHOME_PREFDIR=str(self.prefdir))
        self.proc = subprocess.Popen(
            [str(self.program)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        self._reader = threading.Thread(target=self._read_output, daemon=True)
        self._reader.start()
        self.client = APIClient("127.0.0.1", self.api_port, None)
        deadline = time.monotonic() + 15
        while True:
            try:
                await self.client.connect(login=True)
                break
            except Exception:  # noqa: BLE001 - retry until the node's API is up
                if time.monotonic() > deadline or self.proc.poll() is not None:
                    raise RuntimeError(
                        "node API did not come up:\n" + "\n".join(self.log[-40:])
                    ) from None
                await asyncio.sleep(0.2)
        # If the port was taken, the connection above went to some other process; fail loudly.
        await self.wait_log("setup() finished", timeout=5)
        if self.log_has("Socket bind"):
            raise RuntimeError(
                f"node could not bind API port {self.api_port} (in use?)"
            )
        info = await self.client.device_info()
        devices = {d.device_id: slug(d.name) for d in info.devices}
        entities, _ = await self.client.list_entities_services()
        for e in entities:
            dev = devices.get(e.device_id)
            name = f"{dev}/{e.object_id}" if dev else e.object_id
            self.infos[name] = e
            self._by_key[(e.device_id, e.key)] = name
        self.client.subscribe_states(self._on_state)
        return self

    async def stop(self) -> None:
        if self.client is not None:
            with contextlib.suppress(Exception):
                await self.client.disconnect()
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)
        if self._reader is not None:
            self._reader.join(timeout=2)

    def _read_output(self) -> None:
        assert self.proc is not None and self.proc.stdout is not None
        for line in self.proc.stdout:
            self.log.append(ANSI.sub("", line.rstrip("\n")))

    def _on_state(self, s: EntityState) -> None:
        name = self._by_key.get((s.device_id, s.key))
        if name is not None:
            self.states[name] = s

    # --- queries -----------------------------------------------------------------------------
    def info(self, name: str) -> EntityInfo:
        if name not in self.infos:
            raise KeyError(f"no entity {name!r}; have {sorted(self.infos)}")
        return self.infos[name]

    def state(self, name: str) -> Any:
        self.info(name)
        s = self.states.get(name)
        return None if s is None else getattr(s, "state", s)

    async def wait_for(
        self,
        name: str,
        pred: Callable[[Any], bool] | Any,
        timeout: float = 5.0,
        attr: str | None = None,
    ) -> Any:
        """Wait until the entity's state (or `attr` of its state object) satisfies `pred`
        (a callable, or a value to compare equal to). Returns the matching value."""
        self.info(name)
        check = pred if callable(pred) else (lambda v: v == pred)
        deadline = time.monotonic() + timeout
        last: Any = None
        while time.monotonic() < deadline:
            s = self.states.get(name)
            if s is not None:
                last = getattr(s, attr) if attr else getattr(s, "state", s)
                if check(last):
                    return last
            await asyncio.sleep(0.05)
        raise AssertionError(
            f"{name}{'.' + attr if attr else ''}: timed out, last={last!r}"
        )

    async def wait_log(
        self, needle: str | re.Pattern[str], timeout: float = 5.0
    ) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for line in list(self.log):
                if (
                    needle.search(line)
                    if isinstance(needle, re.Pattern)
                    else needle in line
                ):
                    return line
            await asyncio.sleep(0.05)
        raise AssertionError(
            f"log line {needle!r} not seen; tail:\n" + "\n".join(self.log[-30:])
        )

    def log_has(self, needle: str) -> bool:
        return any(needle in line for line in self.log)

    # --- commands ----------------------------------------------------------------------------
    def _target(self, name: str) -> dict[str, int]:
        e = self.info(name)
        return {"key": e.key, "device_id": e.device_id}

    def number(self, name: str, value: float) -> None:
        self.client.number_command(**self._target(name), state=value)

    def button(self, name: str) -> None:
        self.client.button_command(**self._target(name))

    def switch(self, name: str, on: bool) -> None:
        self.client.switch_command(**self._target(name), state=on)

    def fan(self, name: str, **kw: Any) -> None:
        self.client.fan_command(**self._target(name), **kw)
