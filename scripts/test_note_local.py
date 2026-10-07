from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import note


class LocalNoteTests(unittest.TestCase):
    def test_draft_is_created_in_private_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            local_root = Path(temp_dir) / ".local"
            args = argparse.Namespace(
                date="2026-10-07",
                slug="rascunho",
                title="Rascunho",
                category="Nota",
                classes="note-seed",
                status="draft",
                no_publish=False,
                body="Texto local.",
                body_file=None,
            )
            with mock.patch.object(note, "DRAFTS_ROOT", local_root / "drafts"):
                path = note.write_note_file(args, Path(temp_dir))
            self.assertEqual(path, local_root / "drafts" / "notes" / "2026-10-07-rascunho.md")
            self.assertIn("status: draft", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
