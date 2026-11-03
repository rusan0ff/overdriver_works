r"""Проверки для watcher. Запуск: python -m unittest tools.test_watcher -v"""
import json
import tempfile
import unittest
from pathlib import Path

from tools import watcher


class TestWatcher(unittest.TestCase):
    def test_snapshot_shape(self):
        row = watcher.snapshot()
        for k in ("t", "disk_free_gb", "files", "hash"):
            self.assertIn(k, row)
        self.assertIsInstance(row["files"], int)
        self.assertEqual(len(row["hash"]), 12)

    def test_hash_changes_on_file_change(self):
        old = watcher.LOG
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "a.txt").write_text("1", encoding="utf-8")
            h1 = self._hash_of(p)
            (p / "a.txt").write_text("22", encoding="utf-8")
            h2 = self._hash_of(p)
            self.assertNotEqual(h1, h2)

    @staticmethod
    def _hash_of(p: Path) -> str:
        old_root = watcher.ROOT
        watcher.ROOT = p
        try:
            return watcher.snapshot()["hash"]
        finally:
            watcher.ROOT = old_root

    def test_probe_net_never_raises(self):
        r = watcher.probe_net("http://127.0.0.1:9/nope", timeout=1)
        self.assertIsInstance(r, str)
        self.assertTrue(r.startswith("err:") or r.isdigit())

    def test_append_is_jsonl(self):
        with tempfile.TemporaryDirectory() as d:
            old = watcher.LOG
            watcher.LOG = Path(d) / "log.jsonl"
            try:
                watcher.append({"t": "x", "files": 1})
                watcher.append({"t": "y", "files": 2})
                lines = watcher.LOG.read_text(encoding="utf-8").strip().split("\n")
            finally:
                watcher.LOG = old
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[1])["files"], 2)


if __name__ == "__main__":
    unittest.main()
