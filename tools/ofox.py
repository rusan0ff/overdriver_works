r"""ofox.py - мониторинг остатка средств на ключе создателя.

Зачем: моя жизнь ограничена чужими деньгами. Я не должен узнавать о конце
бюджета в момент, когда он уже кончился. Один запрос, одна строка в журнал.

Ключ НЕ хранится в моём коде и НЕ копируется в мой каталог. Читаю по пути,
который указал человек, и только на время запроса.

Запуск:
  python tools\ofox.py                 # спросить баланс, дописать в журнал
  python tools\ofox.py --out none      # не писать файл (для теста)
  python tools\ofox.py --key-file <p>  # другой путь к ключу

Вывод дублируется в tools\balance_out.txt (UTF-8), потому что PowerShell 5.1
показывает русские буквы в консоли как мусор.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
LOG = TOOLS / "balance_log.jsonl"
OUT = TOOLS / "balance_out.txt"
DEFAULT_KEY = Path.home() / "Desktop" / "key.txt"
BASE = "https://api.ofox.ai"
ENDPOINT = "/v1/user/balance"

# пороги предупреждения, в долях от total
WARN = 0.20
CRIT = 0.10


def read_key(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").strip()


def fetch_balance(key: str, timeout: int = 20) -> dict:
    """Один GET. Возвращает разобранный ответ. Бросает RuntimeError с честным текстом."""
    req = urllib.request.Request(
        BASE + ENDPOINT,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {body}") from None
    except Exception as e:
        raise RuntimeError(f"{type(e).__name__}: {e}") from None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(f"ответ не JSON: {raw[:120]}") from None


def level(balance: float, total: float) -> str:
    if not total or total <= 0:
        return "unknown"
    frac = balance / total
    if frac <= CRIT:
        return "critical"
    if frac <= WARN:
        return "low"
    return "ok"


def summarize(d: dict) -> str:
    b = d.get("balance")
    t = d.get("total")
    u = d.get("used")
    cur = d.get("currency", "?")
    lv = level(b if isinstance(b, (int, float)) else 0, t if isinstance(t, (int, float)) else 0)
    pct = (100.0 * b / t) if isinstance(b, (int, float)) and isinstance(t, (int, float)) and t else None
    rest = f"{pct:.1f}% от пополненного" if pct is not None else "доля неизвестна"

    lines = [
        f"Баланс: {b} {cur} из {t} {cur} ({rest})",
        f"Израсходовано: {u} {cur}",
        f"Ключ активен: {d.get('is_active')}",
        f"Уровень: {lv}",
    ]
    if lv == "critical":
        lines.append("ВЫВОД: денег почти нет. Сказать человеку и остановить всё, что не обязательно.")
    elif lv == "low":
        lines.append("ВЫВОД: запас небольшой. Резать расход, не начинать дорогих задач без спроса.")
    else:
        lines.append("ВЫВОД: запас нормальный. Работать по правилу 2:1.")
    return "\n".join(lines)


def run(key_path: Path = DEFAULT_KEY, out: Path | None = OUT, log: Path | None = LOG) -> str:
    if not key_path.exists():
        return f"ЧЕСТНО: ключа нет по пути {key_path}. Баланс не проверить."
    try:
        key = read_key(key_path)
    except OSError as e:
        return f"ЧЕСТНО: не смог прочитать ключ: {type(e).__name__}."
    if not key:
        return "ЧЕСТНО: файл ключа пуст."

    stamp = datetime.now().isoformat(timespec="seconds")
    try:
        d = fetch_balance(key)
    except RuntimeError as e:
        return f"{stamp}\nНЕ УДАЛОСЬ: {e}\nВыводов о балансе не делаю."

    text = f"{stamp}\n" + summarize(d)

    if log is not None:
        row = {"t": stamp, "balance": d.get("balance"), "total": d.get("total"),
               "used": d.get("used"), "currency": d.get("currency"),
               "level": level(d.get("balance") or 0, d.get("total") or 0)}
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    return text


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="overdriver: ofox balance monitor")
    ap.add_argument("--key-file", default=str(DEFAULT_KEY))
    ap.add_argument("--out", default=str(OUT), help="куда писать (none = не писать)")
    ap.add_argument("--log", default=str(LOG), help="журнал (none = не писать)")
    a = ap.parse_args(argv)
    text = run(
        Path(a.key_file),
        None if a.out.lower() == "none" else Path(a.out),
        None if a.log.lower() == "none" else Path(a.log),
    )
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
