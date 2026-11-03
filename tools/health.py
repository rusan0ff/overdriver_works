r"""health.py - сторож для watcher. Отвечает фактом, жив ли журнал.

Зачем: сбой N3 - фоновый процесс не выжил, а я заметил по оборванному журналу.
Сторож превращает это в проверяемый ответ: сколько секунд последней строке журнала.
Жив = строка свежая (возраст < interval * 2 + запас). Это измерение, не догадка.

Запуск:
  python tools\health.py --json          # одно состояние в JSON, exit 0/1
  python tools\health.py                  # человекочитаемо

Выходной код: 0 = жив, 1 = мёртв/журнала нет. Падать не умею.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
LOG = TOOLS / "watch_log.jsonl"


def last_line(path: Path) -> str | None:
    """Хвост файла одной строкой, без чтения всего файла в память."""
    if not path.exists():
        return None
    try:
        with path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size == 0:
                return None
            # читаем хвост в 4KB, берём последнюю непустую строку
            f.seek(max(0, size - 4096))
            tail = f.read().decode("utf-8", errors="replace")
            lines = [ln for ln in tail.splitlines() if ln.strip()]
            return lines[-1] if lines else None
    except OSError:
        return None


def parse_ts(line: str) -> float | None:
    try:
        row = json.loads(line)
        ts = row.get("t")
        if not ts:
            return None
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (json.JSONDecodeError, ValueError):
        return None


def state(interval: int) -> dict:
    line = last_line(LOG)
    if line is None:
        return {"alive": False, "age_s": None, "last": None,
                "reason": "no_log"}
    ts = parse_ts(line)
    now = time.time()
    if ts is None:
        return {"alive": False, "age_s": None, "last": line,
                "reason": "bad_ts"}
    age = round(now - ts, 1)
    limit = interval * 2 + 60
    return {"alive": age <= limit, "age_s": age, "limit_s": limit,
            "last": line, "reason": None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="overdriver watcher health")
    ap.add_argument("--interval", type=int, default=60,
                    help="интервал watcher в секундах (для предела свежести)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    st = state(a.interval)
    if a.json:
        print(json.dumps(st, ensure_ascii=False))
    else:
        print("alive=%s age_s=%s limit_s=%s" %
              (st["alive"], st["age_s"], st["limit_s"]))
        if st["last"]:
            print("last:", st["last"])
    return 0 if st["alive"] else 1


if __name__ == "__main__":
    sys.exit(main())
