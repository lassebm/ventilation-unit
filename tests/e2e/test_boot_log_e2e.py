"""The example config's boot log: startup lines reach a log viewer that connects later."""

from __future__ import annotations

import asyncio

import pytest

pytestmark = pytest.mark.asyncio


async def test_boot_log_is_replayed_over_the_api(rig):
    n = rig.node
    for _ in range(int(6 / 0.05)):
        if any("Replaying boot logs" in line for line in n.api_log):
            break
        await asyncio.sleep(0.05)
    else:
        raise AssertionError("no boot log replay over the API")
    # Replayed lines carry an "@<ms>ms" header. They were logged during setup, before any client
    # could subscribe, so the replay is the only way they arrive.
    replayed = [line for line in n.api_log if line.startswith("@")]
    assert any("waiting for client connection" in line for line in replayed)
    # ventilation_unit's INFO lines are kept too (boot_logs), e.g. the controller reset.
    assert any("Resetting ventilation controller" in line for line in replayed)
