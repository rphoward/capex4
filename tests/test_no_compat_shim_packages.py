"""Standalone gate — one-release shim packages must not exist in capex4."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPEX3_ROOT = REPO_ROOT / "src" / "capex3"

REMOVED_SHIM_PACKAGES = (
    "rental_capex_calculator",
    "teaching_display_plan",
    "bootstrap",
    "workbook_assumptions",
)


class NoCompatShimPackagesTest(unittest.TestCase):
    def test_removed_shim_packages_do_not_exist(self) -> None:
        existing = [
            name for name in REMOVED_SHIM_PACKAGES if (CAPEX3_ROOT / name).exists()
        ]
        self.assertEqual([], existing)

    def test_heartbeat_server_shim_is_removed(self) -> None:
        heartbeat = (
            CAPEX3_ROOT
            / "runtime"
            / "rental_capex_teaching_server"
            / "heartbeat_server.py"
        )
        self.assertFalse(heartbeat.exists())


if __name__ == "__main__":
    unittest.main()
