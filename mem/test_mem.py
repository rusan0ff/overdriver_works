r"""test_mem.py - тесты для memindex.py и memsearch.py.

Запуск:
  python -m unittest mem.test_mem -v
  (или python mem\test_mem.py)
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mem import memindex, memsearch  # noqa: E402


class ChunkTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(memindex.chunk_text(""), [])
        self.assertEqual(memindex.chunk_text("   \n  "), [])

    def test_small_fits_one(self):
        self.assertEqual(len(memindex.chunk_text("привет\nмир")), 1)

    def test_long_splits(self):
        big = "\n".join(f"строка номер {i}" for i in range(200))
        chunks = memindex.chunk_text(big)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= memindex.CHARS_PER_CHUNK + 200 for c in chunks))


class BuildSearchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.db = self.tmp / "index.db"
        src = self.tmp / "a.txt"
        src.write_text("альфа и бета. альфа важное слово.", encoding="utf-8")
        # строим вручную в маленьком root-каталоге
        self.db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db))
        conn.execute("CREATE VIRTUAL TABLE chunks USING fts5(source, chunk, text, tokenize='unicode61')")
        conn.execute("INSERT INTO chunks(source, chunk, text) VALUES (?,?,?)", (str(src), 0, "альфа и бета"))
        conn.execute("INSERT INTO chunks(source, chunk, text) VALUES (?,?,?)", (str(src), 1, "альфа важное слово"))
        conn.commit()
        conn.close()

    def test_search_finds(self):
        rows = memsearch.search(self.db, "альфа", 10)
        self.assertEqual(len(rows), 2)

    def test_search_missing_db(self):
        self.assertEqual(memsearch.search(self.tmp / "нет.db", "альфа", 10), [])

    def test_bad_query_no_crash(self):
        # кривой синтаксис fts5 не должен ронять поиск
        rows = memsearch.search(self.db, '"""', 10)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
