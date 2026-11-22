from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness import Node, compile_host, exclusive
import pytest
import pytest_asyncio
from vent_sim import ControllerSide, PanelSide, UnitSim

HERE = Path(__file__).parent
API_PORT = 16054
# The host UART only accepts a two-level device path (/dir/name); the pty terminal ends are symlinked here.
USB_PORT = Path("/tmp/vent-e2e-usb.pty")
PANEL_PORT = Path("/tmp/vent-e2e-panel.pty")
CTRL_PORT = Path("/tmp/vent-e2e-ctrl.pty")


@pytest.fixture(scope="session")
def e2e_lock():
    with exclusive(Path("/tmp/vent-e2e.lock")):
        yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    """Attach the node's log to a failing test's report, for debugging (and CI)."""
    outcome = yield
    report = outcome.get_result()
    node = getattr(item, "_e2e_node", None)
    if report.failed and node is not None:
        report.sections.append(("node log (tail)", "\n".join(node.log[-300:])))


@pytest.fixture(scope="session")
def firmware(e2e_lock) -> Path:
    return compile_host(
        HERE / "configs" / "host-basic.yaml",
        {
            "api_port": str(API_PORT),
            "usb_port": str(USB_PORT),
            "panel_port": str(PANEL_PORT),
            "ctrl_port": str(CTRL_PORT),
        },
    )


@dataclass
class Rig:
    node: Node
    unit: UnitSim
    panel: PanelSide
    controller: ControllerSide


@pytest_asyncio.fixture
async def rig(firmware: Path, tmp_path: Path, request: pytest.FixtureRequest):
    unit = UnitSim().attach(USB_PORT)
    panel = PanelSide(command=0x01).attach(PANEL_PORT)
    controller = ControllerSide().attach(CTRL_PORT)
    node = Node(firmware, API_PORT, tmp_path / "prefs")
    request.node._e2e_node = node
    try:
        await node.start()
        yield Rig(node, unit, panel, controller)
    finally:
        await node.stop()
        for s in (unit, panel, controller):
            s.close()
