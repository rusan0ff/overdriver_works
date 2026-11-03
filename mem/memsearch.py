r"""memsearch.py - ищет по локальному индексу моей памяти (fts5).

Зачем: не читать всю память в контекст, а доставать только релевантные куски.

Запуск:
  python mem\memsearch.py "слово или фраза" [--limit 5] [--db mem\index.db]
  python mem\memsearch.py "слово" --raw       # только совпавшие куски, без рамки

Возвращает куски с указанием источника. Если базы нет - честно говорит об этом.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "mem" / "index.db"


def search(db_path: Path, query: str, limit: int) -> list[tuple[str, str]]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT source, text FROM chunks WHERE chunks MATCH ? "
            "ORDER BY bm25(chunks) LIMIT ?",
            (query, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        # неверный синтаксис запроса fts5 -> пусто, а не падение
        rows = []
    conn.close()
    return rows


def render(rows: list[tuple[str, str]]) -> str:
    if not rows:
        return "НИЧЕГО НЕ НАШЛОСЬ (или индекса нет - запусти memindex.py)."
    lines = []
    for src, text in rows:
        lines.append(f"--- {src} ---")
        lines.append(text.strip()[:600])
        lines.append("")
    return "\n".join(lines).rstrip()


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="overdriver memsearch")
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--raw", action="store_true", help="только текст совпадений")
    a = ap.parse_args(argv)

    rows = search(Path(a.db), a.query, a.limit)
    if a.raw:
        print("\n\n".join(t for _, t in rows))
    else:
        print(render(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
