"""Full firmware compile of the example config (slow: run with `-m compile`). Fails on any
compiler warning that points into this repo's component sources."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "esphome" / "ventilation-unit.yaml"
COMPONENT_DIRS = ("ventilation_unit", "ventilation_panel_bridge")


@pytest.mark.compile
def test_compile_example() -> None:
    # Build from a scratch copy so a real secrets.yaml is never needed (or touched).
    work = REPO / "tests" / ".build" / "compile"
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy(EXAMPLE, work / EXAMPLE.name)
    shutil.copy(REPO / "esphome" / "secrets.yaml.example", work / "secrets.yaml")
    link = work / "components"
    if (
        link.is_symlink() and not link.exists()
    ):  # dangling, e.g. a cache from another checkout
        link.unlink()
    if not link.exists():
        link.symlink_to(REPO / "esphome" / "components")
    # Drop our components' cached objects so they're recompiled and their warnings show up in this
    # run (an incremental build skips up-to-date files, and CI restores a cached build).
    for d in COMPONENT_DIRS:
        for obj in (work / ".esphome" / "build").glob(
            f"**/esphome/components/{d}/*.o*"
        ):
            obj.unlink()
    proc = subprocess.run(
        [sys.executable, "-m", "esphome", "compile", EXAMPLE.name],
        cwd=work,
        capture_output=True,
        text=True,
        check=False,
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0, out[-6000:]
    ours = "|".join(re.escape(d) for d in COMPONENT_DIRS)
    warnings = [
        line
        for line in out.splitlines()
        if re.search(rf"(?:{ours})/[^:\s]+:\d+(?::\d+)?: warning:", line)
    ]
    assert not warnings, "\n".join(warnings)
