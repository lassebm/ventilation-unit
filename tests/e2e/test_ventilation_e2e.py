"""End-to-end: the real components (host build) against the simulated controller links."""

from __future__ import annotations

import asyncio
import math

import pytest

pytestmark = pytest.mark.asyncio


def close(v: float, tol: float = 0.01):
    return lambda x: x is not None and math.isclose(x, v, abs_tol=tol)


async def wait_until(pred, timeout: float = 5.0) -> None:
    for _ in range(int(timeout / 0.05)):
        if pred():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition not met in time")


def connects(node) -> int:
    """How many times the node has (re)connected to the controller firmware."""
    return sum("Connected to ventilation firmware" in line for line in node.live_log())


# --- ventilation_unit (USB register link) ---------------------------------------------------


async def test_connects_and_publishes_registers(rig):
    n = rig.node
    await n.wait_for("firmware_version", "2.4", timeout=8)
    await n.wait_for("temperature", close(21.0))
    await n.wait_for("humidity", close(50.0))
    await n.wait_for("humidity_voltage", close(4.95))
    await n.wait_for("inflow_rpm", close(1500))
    await n.wait_for("outflow_rpm", close(1440))
    await n.wait_for("filter_runtime", close(1000.0))
    await n.wait_for("filter_replacement_interval", close(8760))
    await n.wait_for("filter_life_remaining", close(100 * (52560 - 6000) / 52560))
    await n.wait_for("filter_remaining_hours", close(7760.0))
    await n.wait_for("freeze_protection_threshold", close(3))
    await n.wait_for("humidity_boost_threshold", close(60))
    await n.wait_for("inflow_speed_1", close(40))
    await n.wait_for("inflow_humidity_boost", close(100))
    await n.wait_for("outflow_speed_3", close(100))
    await n.wait_for("bypass_hardware_present", True)
    await n.wait_for("bypass_polarity_invert", True)
    await n.wait_for("force_input", False)
    await n.wait_for("bypass_state", False)
    await n.wait_for("edit_mode", False)
    assert n.log_has("Connected to ventilation firmware v2.4")


async def test_live_values_follow_polling(rig):
    n = rig.node
    await n.wait_for("temperature", close(21.0), timeout=8)
    rig.unit.set(0x51, 45)  # 5 °C
    rig.unit.set(0x52, 1)
    await n.wait_for("temperature", close(5.0), timeout=4)
    await n.wait_for("force_input", True, timeout=4)


async def test_writes_are_ignored_without_edit_mode(rig):
    n = rig.node
    await n.wait_for("freeze_protection_threshold", close(3), timeout=8)
    n.number("freeze_protection_threshold", 5)
    await n.wait_log("Ignoring write to register 0x70 because edit mode is disabled")
    await asyncio.sleep(0.5)
    assert rig.unit.writes == []


async def test_number_writes_commit_to_flash(rig):
    n = rig.node
    await n.wait_for("freeze_protection_threshold", close(3), timeout=8)
    n.switch("edit_mode", True)
    await n.wait_for("edit_mode", True)
    n.number("freeze_protection_threshold", 5)
    n.number("inflow_speed_1", 55)
    n.number("filter_replacement_interval", 1000)
    await n.wait_for("freeze_protection_threshold", close(5))
    await n.wait_for("inflow_speed_1", close(55))
    await n.wait_for("filter_replacement_interval", close(1000))
    await wait_until(lambda: rig.unit.commits >= 3)
    assert (0x70, 5) in rig.unit.writes
    assert (0x11, 550) in rig.unit.writes
    assert (0x55, 6000) in rig.unit.writes
    assert rig.unit.regs[0x70] == 5
    # Derived filter sensors follow the new interval.
    await n.wait_for("filter_life_remaining", close(0.0))
    await n.wait_for("filter_remaining_hours", close(0.0))


async def test_switch_write(rig):
    n = rig.node
    await n.wait_for("bypass_polarity_invert", True, timeout=8)
    n.switch("edit_mode", True)
    await n.wait_for("edit_mode", True)
    n.switch("bypass_polarity_invert", False)
    await n.wait_for("bypass_polarity_invert", False)
    await wait_until(lambda: (0x32, 0) in rig.unit.writes and rig.unit.commits >= 1)


async def test_disabling_edit_mode_drops_queued_writes(rig):
    n = rig.node
    await n.wait_log("Connected to ventilation firmware v2.4", timeout=8)
    n.switch("edit_mode", True)
    await n.wait_for("edit_mode", True)
    # Take the link down so the writes stay queued until it reconnects.
    rig.unit.responding = False
    await n.wait_log("did not answer register", timeout=8)
    n.number("humidity_boost_threshold", 70)
    n.number("freeze_protection_threshold", 9)
    await asyncio.sleep(0.3)
    assert not n.log_has("Ignoring write to register 0x70")  # accepted into the queue
    n.switch("edit_mode", False)
    await n.wait_for("edit_mode", False)
    rig.unit.responding = True
    await wait_until(
        lambda: connects(n) >= 2,
        timeout=15,
    )
    await asyncio.sleep(1.5)  # a full refresh cycle after reconnecting
    assert (0x72, 70) not in rig.unit.writes
    assert (0x70, 9) not in rig.unit.writes
    assert rig.unit.regs[0x72] == 60


async def test_filter_reset_button(rig):
    n = rig.node
    await n.wait_for("filter_runtime", close(1000.0), timeout=8)
    n.switch("edit_mode", True)
    await n.wait_for("edit_mode", True)
    n.button("filter_replacement_reset")
    await n.wait_for("filter_runtime", close(0.0))
    await n.wait_for("filter_life_remaining", close(100.0))
    assert (0x54, 1) in rig.unit.writes
    assert rig.unit.commits >= 1


async def test_reconnects_after_link_loss(rig):
    n = rig.node
    await n.wait_log("Connected to ventilation firmware v2.4", timeout=8)
    rig.unit.responding = False
    await n.wait_log("did not answer register", timeout=8)
    rig.unit.responding = True
    await wait_until(
        lambda: connects(n) >= 2,
        timeout=15,
    )


# --- ventilation_panel_bridge (600-baud panel link) -------------------------------------------


async def test_panel_command_passes_through(rig):
    n = rig.node
    rig.panel.command = 0x02
    await wait_until(lambda: rig.controller.last_command() == 0x02)
    await n.wait_for("mode", True)
    await n.wait_for("mode", 2, attr="speed_level")
    await n.wait_for("bypass", False)


async def test_controller_status_reaches_panel_and_sensors(rig):
    n = rig.node
    await n.wait_for("filter_due", False, timeout=5)
    rig.controller.status = 0x01
    await n.wait_for("filter_due", True)
    await wait_until(lambda: rig.panel.last_status() == 0x01)
    rig.controller.status = 0x02
    await n.wait_for("alarm", True)
    await n.wait_for("filter_due", False)


async def test_mode_override_until_panel_changes(rig):
    n = rig.node
    await wait_until(lambda: rig.controller.last_command() == 0x01)
    n.fan("mode", state=True, speed_level=3)
    await wait_until(lambda: rig.controller.last_command() == 0x03)
    await n.wait_for("mode", 3, attr="speed_level")
    await asyncio.sleep(0.5)  # the panel keeps sending 0x01; the override must hold
    assert rig.controller.last_command() == 0x03
    rig.panel.command = 0x02  # user presses the panel: override is released
    await wait_until(lambda: rig.controller.last_command() == 0x02)
    await n.wait_for("mode", 2, attr="speed_level")


async def test_fan_off_sends_standby(rig):
    n = rig.node
    await wait_until(lambda: rig.controller.last_command() == 0x01)
    n.fan("mode", state=False)
    await wait_until(lambda: rig.controller.last_command() == 0x00)
    await n.wait_for("mode", False)


async def test_bypass_override_until_panel_changes(rig):
    n = rig.node
    await wait_until(lambda: rig.controller.last_command() == 0x01)
    n.switch("bypass", True)
    await wait_until(lambda: rig.controller.last_command() == 0x09)
    await n.wait_for("bypass", True)
    await asyncio.sleep(0.5)  # the panel keeps sending 0x01; the override must hold
    assert rig.controller.last_command() == 0x09
    assert n.state("bypass") is True
    # The panel's bypass bit changes (closed -> open): the override is released and the panel's
    # command passes through from now on.
    rig.panel.command = 0x09
    await asyncio.sleep(0.3)
    rig.panel.command = 0x01
    await wait_until(lambda: rig.controller.last_command() == 0x01)
    await n.wait_for("bypass", False)


async def test_override_keeps_the_panels_other_bits(rig):
    """A mode override replaces only the mode bits; the service-reset bit (2) and bypass bit (3)
    from the panel still reach the controller."""
    n = rig.node
    await wait_until(lambda: rig.controller.last_command() == 0x01)
    n.fan("mode", state=True, speed_level=3)
    await wait_until(lambda: rig.controller.last_command() == 0x03)
    rig.panel.command = 0x0D  # mode 1 (unchanged) + service reset + bypass
    await wait_until(lambda: rig.controller.last_command() == 0x0F)
    await n.wait_for("mode", 3, attr="speed_level")
    await n.wait_for("bypass", True)


async def test_heartbeat_without_panel_bytes(rig):
    """With the panel silent the bridge keeps repeating its command (~every 100 ms), because the
    controller debounces commands over repeated bytes."""
    rig.panel.command = None
    await asyncio.sleep(0.3)
    start = len(rig.controller.received)
    await asyncio.sleep(1.0)
    sent = rig.controller.received[start:]
    # ~10 expected; the wide window tolerates a loaded machine but still catches a missing
    # heartbeat (~0) or flooding (hundreds).
    assert 3 <= len(sent) <= 20, f"{len(sent)} heartbeat bytes in 1 s"
    assert set(sent) == {0x01}


async def test_speed_setpoint_registers(rig):
    n = rig.node
    await n.wait_for("outflow_speed_3", close(100), timeout=8)
    n.switch("edit_mode", True)
    await n.wait_for("edit_mode", True)
    n.number("outflow_speed_3", 80)
    n.number("inflow_humidity_boost", 65)
    await n.wait_for("outflow_speed_3", close(80))
    await n.wait_for("inflow_humidity_boost", close(65))
    assert (0x23, 800) in rig.unit.writes
    assert (0x15, 650) in rig.unit.writes


async def test_number_publishes_only_after_flash_commit(rig):
    """A write is published once the controller acknowledges the flash commit (reading 0x60),
    not optimistically when it is sent."""
    n = rig.node
    await n.wait_for("freeze_protection_threshold", close(3), timeout=8)
    rig.unit.ignore_reads.add(0x60)
    n.switch("edit_mode", True)
    await n.wait_for("edit_mode", True)
    n.number("freeze_protection_threshold", 7)
    await n.wait_log("did not answer register 0x60", timeout=5)
    assert (0x70, 7) in rig.unit.writes
    assert n.state("freeze_protection_threshold") == 3


async def test_out_of_range_number_is_not_written(rig):
    n = rig.node
    await n.wait_for("freeze_protection_threshold", close(3), timeout=8)
    n.switch("edit_mode", True)
    await n.wait_for("edit_mode", True)
    n.number("freeze_protection_threshold", 40)  # max 31
    await n.wait_log("'Freeze Protection Threshold': 40.000000 > max 31.000000")
    await asyncio.sleep(0.5)
    assert not [w for w in rig.unit.writes if w[0] == 0x70]
