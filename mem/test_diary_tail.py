r"""Тесты для mem/diary_tail.py."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from diary_tail import main, tail  # noqa: E402


class TailTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(tail("", 10), "")

    def test_fits_untouched(self):
        self.assertEqual(tail("abc", 10), "abc")

    def test_tail_cut(self):
        self.assertEqual(tail("0123456789", 4), "6789")

    def test_chars_zero(self):
        self.assertEqual(tail("abc", 0), "")


class ExportTest(unittest.TestCase):
    def test_export_writes_tail(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "diary.txt"
            out = Path(d) / "tail.txt"
            src.write_text("HEAD" + "X" * 100, encoding="utf-8")
            rc = main([str(src), "--chars", "10", "--out", str(out)])
            self.assertEqual(rc, 0)
            self.assertEqual(out.read_text(encoding="utf-8"), "X" * 10)

    def test_missing_diary(self):
        rc = main([r"C:\nonexistent\no_such_file.txt", "--out", "t.txt"])
        self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
