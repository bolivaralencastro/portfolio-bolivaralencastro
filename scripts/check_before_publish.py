#!/usr/bin/env python3
"""Run the complete local equivalent of publication CI."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMANDS = (
    (sys.executable, "scripts/build_site_metadata.py", "--check"),
    (sys.executable, "scripts/validate_site.py"),
    (sys.executable, "scripts/check_repository_hygiene.py"),
    (sys.executable, "-m", "unittest", "discover", "-s", "scripts", "-p", "test_*.py"),
)


def main() -> int:
    for command in COMMANDS:
        print(f"+ {' '.join(command)}", flush=True)
        if subprocess.run(command, cwd=ROOT).returncode:
            return 1
    with tempfile.TemporaryDirectory(prefix="portfolio-public-") as temp_dir:
        output = Path(temp_dir) / "site"
        command = (sys.executable, "scripts/build_public_site.py", "--output", str(output))
        print(f"+ {' '.join(command)}", flush=True)
        if subprocess.run(command, cwd=ROOT).returncode:
            return 1
    print("All pre-publication checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
