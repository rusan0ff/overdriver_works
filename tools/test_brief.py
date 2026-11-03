import tempfile
import unittest
from pathlib import Path

from tools import brief


class TestBrief(unittest.TestCase):
    def test_empty_is_honest(self):
        s = brief.summarize([], 0)
        self.assertIn("ПУСТ", s)
        self.assertIn("Не выдумываю", s)

    def test_counts_changes(self):
        rows = [
            {"t": "1", "hash": "a", "files": 1, "disk_free_gb": 10.0},
            {"t": "2", "hash": "a", "files": 1, "disk_free_gb": 10.0},
            {"t": "3", "hash": "b", "files": 2, "disk_free_gb": 9.5},
        ]
        s = brief.summarize(rows, 3)
        self.assertIn("Изменений в моём каталоге: 1", s)
        self.assertIn("10.0 -> 9.5", s)

    def test_broken_lines_are_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            old = brief.LOG
            p = Path(d) / "l.jsonl"
            p.write_text('{"t":"1"}\nnot json\n{"t":"2"}\n', encoding="utf-8")
            brief.LOG = p
            try:
                rows, total = brief.load(10)
            finally:
                brief.LOG = old
            self.assertEqual(total, 3)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[-1]["t"], "2")

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            old = brief.LOG
            brief.LOG = Path(d) / "nope.jsonl"
            try:
                rows, total = brief.load(10)
            finally:
                brief.LOG = old
            self.assertEqual((rows, total), ([], 0))

    def test_notes_absent_data(self):
        rows = [{"t": "1", "hash": "a", "files": 1}]
        s = brief.summarize(rows, 1)
        self.assertIn("Нет данных: telegram", s)
        self.assertIn("Сеть в этом промежутке не проверялась", s)

    def test_main_writes_utf8_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "sub" / "o.txt"
            old = brief.LOG
            brief.LOG = Path(d) / "nope.jsonl"
            try:
                brief.main(["--out", str(out)])
            finally:
                brief.LOG = old
            self.assertTrue(out.exists())
            self.assertIn("ПУСТ", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
