"""Opt-in restore of the bridge's mode and bypass across a reboot (no physical panel)."""

from __future__ import annotations

import asyncio
from pathlib import Path

from conftest import API_PORT, CTRL_PORT
from harness import Node
import pytest
from vent_sim import ControllerSide

pytestmark = pytest.mark.asyncio


async def wait_until(pred, timeout: float = 5.0) -> None:
    for _ in range(int(timeout / 0.05)):
        if pred():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition not met in time")


async def test_mode_and_bypass_restore_after_reboot(
    firmware_restore: Path, tmp_path, request: pytest.FixtureRequest
):
    prefs = tmp_path / "prefs"
    controller = ControllerSide().attach(CTRL_PORT)
    try:
        node = Node(firmware_restore, API_PORT, prefs)
        request.node._e2e_node = node  # the failure report shows this node's log
        await node.start()
        try:
            # First boot, nothing saved: mode RESTORE_DEFAULT_ON -> speed 1 (the startup command),
            # bypass RESTORE_DEFAULT_OFF -> closed.
            await wait_until(lambda: controller.last_command() == 0x01)
            node.fan("mode", state=True, speed_level=3)
            node.switch("bypass", True)
            await wait_until(lambda: controller.last_command() == 0x0B)
            await node.wait_for("mode", 3, attr="speed_level")
            await node.wait_for("bypass", True)
            await asyncio.sleep(0.3)  # let the preference writes land
        finally:
            await node.stop()

        controller.received.clear()
        node = Node(firmware_restore, API_PORT, prefs)
        request.node._e2e_node = node  # the failure report shows this node's log
        await node.start()
        try:
            await wait_until(lambda: controller.last_command() == 0x0B)
            await node.wait_for("mode", 3, attr="speed_level")
            await node.wait_for("bypass", True)
        finally:
            await node.stop()
    finally:
        controller.close()
