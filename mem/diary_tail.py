r"""diary_tail.py - выгружает хвост дневника в mem/diary_tail.txt.

Дневник живёт в инфраструктуре агента, вне <ROOT>,
поэтому memindex.py его не видит. Этот скрипт читает дневник, берёт
последние N символов и пишет их в mem/diary_tail.txt (UTF-8), чтобы
хвост попадал в локальный индекс.

Путь к дневнику берётся из переменной окружения OWNER_DIARY
(чтобы реальный путь не попадал в репозиторий). Если она не задана,
путь можно передать аргументом.

Запуск:
  python mem\diary_tail.py [путь_к_дневнику] [--chars 8000]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "mem" / "diary_tail.txt"

# путь по умолчанию — из окружения (не хардкодим в репо)
DEFAULT_DIARY = os.environ.get("OWNER_DIARY", "")


def tail(text: str, chars: int) -> str:
    if not text:
        return ""
    if chars <= 0:
        return ""
    return text[-chars:]


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="overdriver diary tail exporter")
    ap.add_argument("diary", nargs="?", default=DEFAULT_DIARY or None)
    ap.add_argument("--chars", type=int, default=8000)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)

    if not a.diary:
        print("diary_tail: путь к дневнику не задан (задай OWNER_DIARY или передай аргумент)", file=sys.stderr)
        return 1

    src = Path(a.diary)
    if not src.exists():
        print(f"diary_tail: не найден {src}", file=sys.stderr)
        return 1

    text = src.read_text(encoding="utf-8", errors="replace")
    body = tail(text, a.chars)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"diary_tail: {len(body)} символов -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
