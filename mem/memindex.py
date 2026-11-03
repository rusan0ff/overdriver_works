r"""memindex.py - строит локальный полнотекстовый индекс моей памяти (fts5).

Зачем: long_memory и дневник растут, а читать их целиком в контекст дорого.
Индекс по кускам текста позволяет искать нужное по слову, не таская всё в промпт.

Запуск:
  python mem\memindex.py                       # пересобрать индекс из источников
  python mem\memindex.py --out mem\index.db    # другой путь к базе
  python mem\memindex.py --out none            # только вывести, не писать файл

Источники (txt в моём каталоге + хвост дневника берётся из mem\diary_tail.txt):
  overdriver\*.txt
  overdriver\judge_core\*.txt
  overdriver\tools\*.txt  (кроме огромных выводов)
  overdriver\mem\diary_tail.txt  (если есть)

Разбивает каждый файл на куски (по строкам, до ~CHARS_PER_CHUNK),
кладёт в таблицу chunks(id, source, chunk, text). Поиск - memsearch.py.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHARS_PER_CHUNK = 800
CHUNK_OVERLAP = 120
# выводы, которые не надо индексировать (огромные, мусор)
SKIP_NAMES = {"ofox_docs.txt", "balance_out.txt", "brief_out.txt", "watch_log.jsonl",
              "watch_stdout.log", "watch_stderr.log", "balance_log.jsonl"}


def chunk_text(text: str) -> list[str]:
    """Режет текст на перекрывающиеся куски по границам строк."""
    text = text.strip()
    if not text:
        return []
    lines = text.splitlines()
    chunks: list[str] = []
    cur = ""
    for ln in lines:
        if len(cur) + len(ln) + 1 > CHARS_PER_CHUNK and cur:
            chunks.append(cur)
            # перекрытие: хвост текущего куска в начало следующего
            cur = cur[-CHUNK_OVERLAP:] + "\n"
        cur += ln + "\n"
    if cur.strip():
        chunks.append(cur)
    return chunks


def sources(root: Path) -> list[Path]:
    out = []
    for pattern in ("*.txt", "judge_core/*.txt", "tools/*.txt"):
        for p in sorted((root).glob(pattern)):
            if p.name in SKIP_NAMES:
                continue
            out.append(p)
    return out


def build(db_path: Path, root: Path, diary_tail: Path) -> dict:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("DROP TABLE IF EXISTS chunks")
    conn.execute(
        "CREATE VIRTUAL TABLE chunks USING fts5(source, chunk, text, tokenize='unicode61')"
    )
    n_files = 0
    n_chunks = 0
    files = sources(root)
    if diary_tail.exists():
        files.append(diary_tail)
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        n_files += 1
        for i, ch in enumerate(chunk_text(text)):
            conn.execute(
                "INSERT INTO chunks(source, chunk, text) VALUES (?, ?, ?)",
                (str(p), i, ch),
            )
            n_chunks += 1
    conn.commit()
    conn.close()
    return {"files": n_files, "chunks": n_chunks, "db": str(db_path)}


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="overdriver memindex")
    ap.add_argument("--out", default=str(ROOT / "mem" / "index.db"))
    a = ap.parse_args(argv)

    if a.out.lower() == "none":
        db_path = Path(":memory:")
    else:
        db_path = Path(a.out)

    diary_tail = ROOT / "mem" / "diary_tail.txt"
    res = build(db_path, ROOT, diary_tail)

    print(f"memindex: проиндексировано файлов {res['files']}, кусков {res['chunks']}")
    print(f"база: {res['db']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
