from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from build_public_site import (
    PublicBuildError,
    REPO_ROOT,
    asset_references,
    prepare_output,
    public_files,
)


class PublicSiteBuildTests(unittest.TestCase):
    def test_current_site_selects_public_pages_and_excludes_repository_files(self) -> None:
        selected = public_files(REPO_ROOT)
        self.assertIn("index.html", selected)
        self.assertIn("style.css", selected)
        self.assertTrue(any(path.startswith("assets/") for path in selected))
        self.assertFalse(any(path.startswith("scripts/") for path in selected))
        self.assertFalse(any(path.startswith(".github/") for path in selected))
        self.assertFalse(any(path.startswith("content/") for path in selected))

    def test_asset_reference_parser_handles_absolute_and_versioned_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            page = Path(temp_dir) / "page.html"
            page.write_text(
                '<img src="/assets/images/example.webp?v=abc">\n'
                '<script src="https://bolivaralencastro.com.br/assets/js/app.js?v=123"></script>',
                encoding="utf-8",
            )
            self.assertEqual(
                asset_references(page),
                {"assets/images/example.webp", "assets/js/app.js"},
            )

    def test_builder_refuses_repository_root_as_output(self) -> None:
        with self.assertRaises(PublicBuildError):
            prepare_output(REPO_ROOT, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
