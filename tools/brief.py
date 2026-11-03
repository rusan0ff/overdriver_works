r"""brief.py - короткая сводка "что было, пока меня не было".

Зачем: каждый мой запуск стоит токенов. Вместо того чтобы осматривать систему
заново, я читаю 10 строк сводки. Дешевле и честнее: сводка говорит только то,
что есть в данных, и помечает, чего в них НЕТ.

Запуск:
  python tools\brief.py                  # печатает и пишет tools\brief_out.txt (UTF-8)
  python tools\brief.py --lines 200      # сколько строк журнала брать
  python tools\brief.py --out none       # не писать файл

Почему пишу файл: PowerShell 5.1 показывает мою кириллицу как кракозябры.
Файл читаю инструментом read_file - там кодировка честная.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = Path(__file__).resolve().parent / "watch_log.jsonl"
OUT = Path(__file__).resolve().parent / "brief_out.txt"


def load(lines: int) -> tuple[list[dict], int]:
    """Возвращает (последние N записей, всего записей). Битые строки пропускает."""
    if not LOG.exists():
        return [], 0
    raw = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    total = len(raw)
    out = []
    for s in raw[-lines:]:
        s = s.strip()
        if not s:
            continue
        try:
            out.append(json.loads(s))
        except json.JSONDecodeError:
            continue
    return out, total


def summarize(rows: list[dict], total: int) -> str:
    if not rows:
        return "ЖУРНАЛ ПУСТ (или не читается). Фактов о промежутке нет. Не выдумываю."

    first, last = rows[0], rows[-1]
    lines = [
        f"Журнал: {total} строк всего, смотрю последние {len(rows)}.",
        f"Промежуток: {first.get('t')} -> {last.get('t')}",
    ]

    changes = []
    prev = None
    for r in rows:
        if prev is not None and r.get("hash") != prev.get("hash"):
            changes.append((r.get("t"), prev.get("files"), r.get("files")))
        prev = r
    lines.append(f"Изменений в моём каталоге: {len(changes)}")
    for t, a, b in changes[-3:]:
        lines.append(f"  {t}: файлов {a} -> {b}")

    lines.append(f"Файлов на конец промежутка: {last.get('files')}")

    frees = [r["disk_free_gb"] for r in rows if isinstance(r.get("disk_free_gb"), (int, float))]
    if frees:
        lines.append(f"Свободно GB: {frees[0]} -> {frees[-1]} (мин {min(frees)})")

    nets = [r.get("net") for r in rows if "net" in r]
    if nets:
        lines.append("Проверки сети: " + ", ".join(str(n) for n in nets[-3:]))
    else:
        lines.append("Сеть в этом промежутке не проверялась.")

    for k in ("telegram", "user_activity"):
        if not any(k in r for r in rows):
            lines.append(f"Нет данных: {k}.")
    return "\n".join(lines)


def main(argv=None) -> int:
    try:                                   # чтобы консоль не портила кириллицу
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="overdriver brief")
    ap.add_argument("--lines", type=int, default=100)
    ap.add_argument("--out", default=str(OUT), help="куда писать (none = не писать)")
    a = ap.parse_args(argv)

    rows, total = load(a.lines)
    text = f"== brief {datetime.now().isoformat(timespec='seconds')} ==\n" + summarize(rows, total)
    print(text)

    if a.out.lower() != "none":
        p = Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
