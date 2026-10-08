from __future__ import annotations

import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from build_site_metadata import (
    MAX_STABILIZATION_PASSES,
    stabilize_generated_metadata,
)


class MetadataStabilizationTests(unittest.TestCase):
    def test_check_mode_never_starts_another_pass(self) -> None:
        with mock.patch("build_site_metadata.subprocess.run") as run:
            status = stabilize_generated_metadata(
                repo_root=Path("/tmp/repo"),
                base_url="https://example.com",
                check=True,
                changed=[Path("sitemap.xml")],
                current_pass=1,
            )
        self.assertEqual(status, 0)
        run.assert_not_called()

    def test_clean_write_pass_does_not_start_another_pass(self) -> None:
        with mock.patch("build_site_metadata.subprocess.run") as run:
            status = stabilize_generated_metadata(
                repo_root=Path("/tmp/repo"),
                base_url="https://example.com",
                check=False,
                changed=[],
                current_pass=1,
            )
        self.assertEqual(status, 0)
        run.assert_not_called()

    def test_changed_write_pass_runs_the_generator_again(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            completed = subprocess.CompletedProcess([], 0)
            with mock.patch("build_site_metadata.subprocess.run", return_value=completed) as run:
                status = stabilize_generated_metadata(
                    repo_root=repo_root,
                    base_url="https://example.com",
                    check=False,
                    changed=[repo_root / "sitemap.xml"],
                    current_pass=1,
                )

        self.assertEqual(status, 0)
        command = run.call_args.args[0]
        self.assertIn("--base-url", command)
        self.assertIn("https://example.com", command)
        self.assertIn("--stabilization-pass", command)
        self.assertEqual(command[-1], "2")

    def test_non_converging_generation_stops_at_the_limit(self) -> None:
        with mock.patch("build_site_metadata.subprocess.run") as run:
            with contextlib.redirect_stderr(io.StringIO()) as stderr:
                status = stabilize_generated_metadata(
                    repo_root=Path("/tmp/repo"),
                    base_url="https://example.com",
                    check=False,
                    changed=[Path("sitemap.xml")],
                    current_pass=MAX_STABILIZATION_PASSES,
                )

        self.assertEqual(status, 1)
        self.assertIn("did not stabilize", stderr.getvalue())
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
