import json
import tempfile
import time
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools import health


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


class TestHealth(unittest.TestCase):
    def setUp(self):
        self._orig = health.LOG
        self.tmp = Path(tempfile.mkdtemp())
        health.LOG = self.tmp / "watch_log.jsonl"

    def tearDown(self):
        health.LOG = self._orig

    def test_no_log_is_dead(self):
        st = health.state(60)
        self.assertFalse(st["alive"])
        self.assertEqual(st["reason"], "no_log")

    def test_fresh_log_is_alive(self):
        now = time.time()
        row = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now))}
        _write(health.LOG, [row])
        st = health.state(60)
        self.assertTrue(st["alive"])
        self.assertIsNone(st["reason"])

    def test_stale_log_is_dead(self):
        old = time.time() - 1000
        row = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(old))}
        _write(health.LOG, [row])
        st = health.state(60)
        self.assertFalse(st["alive"])
        self.assertGreater(st["age_s"], 900)

    def test_bad_timestamp_is_dead_not_crash(self):
        _write(health.LOG, [{"t": "not-a-time"}])
        st = health.state(60)
        self.assertFalse(st["alive"])
        self.assertEqual(st["reason"], "bad_ts")

    def test_last_line_skips_trailing_blank(self):
        now = time.time()
        row = {"t": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now))}
        _write(health.LOG, [row])
        # добиваем файл пустыми строками, как после trailing newline
        with health.LOG.open("a", encoding="utf-8") as f:
            f.write("\n\n")
        line = health.last_line(health.LOG)
        self.assertIn('"t"', line)

    def test_parse_ts_with_timezone(self):
        ts = health.parse_ts('{"t": "2026-11-04T00:00:00+07:00"}')
        self.assertIsNotNone(ts)


if __name__ == "__main__":
    unittest.main()
