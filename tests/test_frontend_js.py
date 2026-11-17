"""Run the JavaScript unit tests of the panel (needs node, skipped otherwise)."""

from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).parent.parent
FRONTEND = ROOT / "custom_components" / "energy_tracker" / "frontend"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_price_format_node_tests() -> None:
    """node --test tests/js/*.test.mjs"""
    result = subprocess.run(
        ["node", "--test", *map(str, sorted((ROOT / "tests" / "js").glob("*.test.mjs")))],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
@pytest.mark.parametrize("name", ["energy-tracker-panel.js", "price-format.js"])
def test_frontend_syntax(name: str) -> None:
    """node --check for the panel modules."""
    result = subprocess.run(
        ["node", "--check", str(FRONTEND / name)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_module_import_is_versioned() -> None:
    """The panel imports the helpers with the integration version (cache busting)."""
    manifest = (ROOT / "custom_components" / "energy_tracker" / "manifest.json").read_text()
    version = re.search(r'"version": "([^"]+)"', manifest).group(1)
    panel = (FRONTEND / "energy-tracker-panel.js").read_text()
    assert f'from "./price-format.js?v={version}"' in panel
