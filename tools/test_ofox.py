r"""Тесты для tools\ofox.py. Без интернета и без реального ключа.

Проверяю не «работает ли шлюз» (это живёт в самом скрипте), а МОЮ логику:
разбор порогов, честные тексты при ошибках, отсутствие ключа, запись журнала.

Запуск: python tools\test_ofox.py
Живая проверка: python tools\test_ofox.py --live
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import ofox  # noqa: E402


class FakeResp:
    def __init__(self, payload: bytes):
        self._p = payload

    def read(self) -> bytes:
        return self._p

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TLevel(unittest.TestCase):
    def test_ok_low_critical(self):
        self.assertEqual(ofox.level(10.0, 13.0), "ok")       # 77%
        self.assertEqual(ofox.level(2.0, 13.0), "low")       # 15%
        self.assertEqual(ofox.level(0.5, 13.0), "critical")  # 4%

    def test_boundaries_are_inclusive(self):
        self.assertEqual(ofox.level(2.6, 13.0), "low")       # ровно 20%
        self.assertEqual(ofox.level(1.3, 13.0), "critical")  # ровно 10%
        self.assertEqual(ofox.level(2.7, 13.0), "ok")        # чуть выше 20%

    def test_unknown_total_does_not_panic(self):
        self.assertEqual(ofox.level(1.0, 0), "unknown")
        self.assertEqual(ofox.level(0, None), "unknown")


class TSummarize(unittest.TestCase):
    def test_mentions_numbers_and_warns(self):
        s = ofox.summarize({"balance": 6.589222, "total": 13, "used": 6.41,
                            "currency": "USD", "is_active": True})
        self.assertIn("6.589222", s)
        self.assertIn("USD", s)
        self.assertIn("Уровень: ok", s)
        self.assertNotIn("денег почти нет", s)

    def test_critical_says_stop(self):
        s = ofox.summarize({"balance": 0.2, "total": 13, "used": 12.8, "currency": "USD"})
        self.assertIn("Уровень: critical", s)
        self.assertIn("денег почти нет", s)

    def test_missing_total_is_honest(self):
        s = ofox.summarize({"balance": 1.0})
        self.assertIn("доля неизвестна", s)


class TFetch(unittest.TestCase):
    def test_parses_json(self):
        payload = json.dumps({"balance": 1.5, "total": 2.0, "used": 0.5}).encode()
        with mock.patch("urllib.request.urlopen", return_value=FakeResp(payload)):
            self.assertEqual(ofox.fetch_balance("k")["balance"], 1.5)

    def test_http_error_becomes_runtimeerror_with_code(self):
        err = urllib.error.HTTPError("u", 401, "Unauthorized", {},
                                     io.BytesIO(b'{"error":"bad key"}'))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(RuntimeError) as cm:
                ofox.fetch_balance("k")
        self.assertIn("401", str(cm.exception))
        self.assertIn("bad key", str(cm.exception))

    def test_non_json_is_reported_not_swallowed(self):
        with mock.patch("urllib.request.urlopen", return_value=FakeResp(b"<html>nope")):
            with self.assertRaises(RuntimeError) as cm:
                ofox.fetch_balance("k")
        self.assertIn("не JSON", str(cm.exception))


class TRun(unittest.TestCase):
    def test_missing_key_file_says_so_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            log = Path(td) / "l.jsonl"
            out = Path(td) / "o.txt"
            text = ofox.run(Path(td) / "nope.txt", out=out, log=log)
            self.assertIn("ключа нет", text)
            self.assertFalse(log.exists())
            self.assertFalse(out.exists())

    def test_writes_one_log_row_per_call(self):
        payload = json.dumps({"balance": 6.0, "total": 10.0, "used": 4.0,
                              "currency": "USD", "is_active": True}).encode()
        with tempfile.TemporaryDirectory() as td:
            key = Path(td) / "key.txt"
            key.write_text("sk-test\n", encoding="utf-8")
            log = Path(td) / "l.jsonl"
            out = Path(td) / "o.txt"
            with mock.patch("urllib.request.urlopen", return_value=FakeResp(payload)):
                ofox.run(key, out=out, log=log)
                ofox.run(key, out=out, log=log)
            rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["level"], "ok")
            self.assertTrue(out.exists())

    def test_key_is_read_and_used_as_bearer(self):
        seen = {}

        def spy(req, timeout=None):
            seen["auth"] = req.get_header("Authorization")
            return FakeResp(b'{"balance":1,"total":2,"used":1}')

        with tempfile.TemporaryDirectory() as td:
            key = Path(td) / "key.txt"
            key.write_text("  sk-abc  \n", encoding="utf-8")
            with mock.patch("urllib.request.urlopen", side_effect=spy):
                ofox.run(key, out=None, log=None)
        self.assertEqual(seen["auth"], "Bearer sk-abc")


class TLive(unittest.TestCase):
    """Только с --live: правда о реальном шлюзе, без подмены."""

    def test_live_balance(self):
        if not Path(ofox.DEFAULT_KEY).exists():
            self.skipTest("нет файла ключа")
        d = ofox.fetch_balance(ofox.read_key(Path(ofox.DEFAULT_KEY)))
        self.assertIn("balance", d)
        self.assertIsInstance(d["balance"], (int, float))
        print("\nLIVE:", ofox.summarize(d), sep="\n")


if __name__ == "__main__":
    live = "--live" in sys.argv
    sys.argv = [a for a in sys.argv if a != "--live"]
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    if not live:
        TLive.__unittest_skip__ = True
        TLive.__unittest_skip_why__ = "нужен --live (реальная сеть)"
    unittest.TextTestRunner(verbosity=2).run(suite)
