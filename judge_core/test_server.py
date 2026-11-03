"""Tests for judge_core.server (the HTTP interface). No deps, uses urllib."""
import json
import threading
import unittest
import urllib.error
import urllib.request

from judge_core.server import Handler, HTTPServer


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Handler)  # port 0 = random free
        cls.port = cls.srv.server_address[1]
        cls.t = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.t.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def url(self, path=""):
        return f"http://127.0.0.1:{self.port}{path}"

    def post(self, payload, expect=200):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.url("/score"), data=data,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def test_health(self):
        with urllib.request.urlopen(self.url("/health"), timeout=5) as r:
            self.assertEqual(r.status, 200)
            self.assertEqual(json.loads(r.read()), {"ok": True})

    def test_score_json(self):
        status, body = self.post({
            "criteria": [{"name": "logic", "weight": 2, "max": 10},
                         {"name": "style", "weight": 1, "max": 5}],
            "values": {"logic": 8, "style": 4}})
        self.assertEqual(status, 200)
        d = json.loads(body)
        self.assertEqual(d["total"], 80.0)
        self.assertTrue(d["complete"])
        self.assertEqual(d["errors"], [])

    def test_score_csv(self):
        status, body = self.post({
            "criteria": [{"name": "a", "weight": 1, "max": 10}],
            "values": {"a": 5}, "format": "csv"})
        self.assertEqual(status, 200)
        self.assertIn("criterion,value,max,weight", body)

    def test_bad_config_is_400(self):
        status, body = self.post({"criteria": []})
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

    def test_bad_data_is_200_with_errors(self):
        status, body = self.post({
            "criteria": [{"name": "a", "weight": 1, "max": 10}],
            "values": {"a": 99}})
        self.assertEqual(status, 200)
        d = json.loads(body)
        self.assertFalse(d["complete"])
        self.assertTrue(d["errors"])

    def test_missing_values_field_is_400(self):
        status, _ = self.post({"criteria": [{"name": "a", "weight": 1, "max": 10}]})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
