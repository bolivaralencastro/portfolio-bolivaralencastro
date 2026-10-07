from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from check_repository_hygiene import findings


class RepositoryHygieneTests(unittest.TestCase):
    def test_rejects_local_path_without_reading_its_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.assertEqual(
                findings(root, [".local/.env"]),
                [".local/.env: local-only path is tracked"],
            )

    def test_rejects_netscape_session_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "cookies.txt"
            path.write_text(".instagram.com\tTRUE\t/\tTRUE\t0\tsessionid\tredacted-value\n")
            result = findings(root, ["cookies.txt"])
            self.assertEqual(result, ["cookies.txt: sensitive or generated filename is tracked"])

    def test_accepts_placeholder_env_example(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / ".env.example"
            path.write_text("OPENAI_API_KEY=<sua-chave>\n", encoding="utf-8")
            self.assertEqual(findings(root, [".env.example"]), [])

    def test_rejects_tracked_note_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "content" / "notes" / "draft.md"
            path.parent.mkdir(parents=True)
            path.write_text("---\nstatus: draft\n---\n", encoding="utf-8")
            self.assertEqual(
                findings(root, ["content/notes/draft.md"]),
                ["content/notes/draft.md: draft notes must stay under .local/drafts/notes"],
            )


if __name__ == "__main__":
    unittest.main()
