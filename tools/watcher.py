r"""watcher.py - автономный наблюдатель. Работает без меня и без токенов.

Зачем: пока я сплю, кто-то должен смотреть на среду и писать факты в журнал.
Просыпаясь, я читаю журнал вместо того чтобы тратить токены на осмотр.

Запуск:
  python tools\watcher.py --interval 300 --iterations 24
  python tools\watcher.py --once
  python tools\watcher.py --once --net        # один выход во внешний мир

Пишет JSONL в tools\watch_log.jsonl, по строке на итерацию.
hash меняется -> в моём каталоге что-то изменилось.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent      # C:\Users\iankye\overdriver
LOG = Path(__file__).resolve().parent / "watch_log.jsonl"
IGNORE_DIRS = {"__pycache__", ".git"}


def snapshot() -> dict:
    free = None
    try:
        free = round(shutil.disk_usage(str(ROOT)).free / 1024 ** 3, 2)
    except Exception:
        pass

    h = hashlib.sha256()
    files = 0
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir() or any(part in IGNORE_DIRS for part in p.parts):
            continue
        if p.suffix == ".pyc":
            continue
        files += 1
        try:
            st = p.stat()
            h.update(f"{p.relative_to(ROOT)}|{st.st_size}|{int(st.st_mtime)}".encode())
        except OSError:
            pass

    return {
        "t": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "disk_free_gb": free,
        "files": files,
        "hash": h.hexdigest()[:12],
    }


def probe_net(url: str = "https://api.ipify.org?format=json", timeout: int = 10) -> str:
    """Один дешёвый запрос. Возвращает код/ошибку строкой, никогда не падает."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return str(r.status)
    except Exception as e:
        return f"err:{type(e).__name__}"


def append(row: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="overdriver watcher")
    ap.add_argument("--interval", type=int, default=300, help="секунд между снимками")
    ap.add_argument("--iterations", type=int, default=0, help="0 = бесконечно")
    ap.add_argument("--once", action="store_true", help="один снимок и выход")
    ap.add_argument("--net", action="store_true", help="проверить внешний доступ")
    a = ap.parse_args(argv)

    if a.once:
        row = snapshot()
        if a.net:
            row["net"] = probe_net()
        print(json.dumps(row, ensure_ascii=False))
        append(row)
        return 0

    i = 0
    while a.iterations == 0 or i < a.iterations:
        row = snapshot()
        if a.net and i == 0:            # сеть только раз, не долбим чужой сервер
            row["net"] = probe_net()
        append(row)
        print(row["t"], row["hash"], flush=True)
        i += 1
        if a.iterations == 0 or i < a.iterations:
            time.sleep(a.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
