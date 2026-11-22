"""`esphome config` over the fixtures in tests/config: valid/ must pass, invalid/ must fail with
the message given on the fixture's `# expect-error:` first line."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

CONFIG = Path(__file__).parent / "config"


def _esphome_config(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "esphome", "config", str(path.relative_to(CONFIG))],
        cwd=CONFIG,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "path", sorted((CONFIG / "valid").glob("*.yaml")), ids=lambda p: p.stem
)
def test_valid(path: Path) -> None:
    proc = _esphome_config(path)
    assert proc.returncode == 0, proc.stdout[-4000:] + proc.stderr[-2000:]


@pytest.mark.parametrize(
    "path", sorted((CONFIG / "invalid").glob("*.yaml")), ids=lambda p: p.stem
)
def test_invalid(path: Path) -> None:
    first = path.read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("# expect-error:"), f"{path.name}: missing expect-error"
    expected = first.split(":", 1)[1].strip()
    proc = _esphome_config(path)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"{path.name} unexpectedly validated"
    assert expected in out, f"expected {expected!r} in:\n{out[-4000:]}"
