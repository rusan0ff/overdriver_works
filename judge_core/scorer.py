"""Criteria-based scoring. Pure stdlib. My own file, nothing else touched.

Rule: bad DATA is reported, bad CONFIG raises. No rounding until the end.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

__all__ = ["Criterion", "Scorer", "ScoreReport", "ScoringConfigError"]


class ScoringConfigError(ValueError):
    """Criteria set itself is unusable - a caller bug, so raise."""


@dataclass(frozen=True)
class Criterion:
    name: str
    weight: Decimal
    max_score: Decimal

    def __post_init__(self):
        if not str(self.name).strip():
            raise ScoringConfigError("criterion name must be non-empty")
        if self.weight <= 0:
            raise ScoringConfigError(f"{self.name!r}: weight must be > 0")
        if self.max_score <= 0:
            raise ScoringConfigError(f"{self.name!r}: max_score must be > 0")

    @classmethod
    def of(cls, name, weight, max_score):
        return cls(name, Decimal(str(weight)), Decimal(str(max_score)))


@dataclass
class ScoreReport:
    total: Decimal | None            # 0..100, None if not computable
    complete: bool
    rows: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def by_name(self, name):
        for r in self.rows:
            if r["name"] == name:
                return r
        return None

    def to_csv(self) -> str:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["criterion", "value", "max", "weight", "share", "weighted", "error"])
        for r in self.rows:
            w.writerow([r["name"], r["value"], r["max"], r["weight"],
                        r["share"], r["weighted"], r["error"] or ""])
        w.writerow(["TOTAL", self.total, "", "", "", "", ""])
        return buf.getvalue()


class Scorer:
    def __init__(self, criteria):
        if not criteria:
            raise ScoringConfigError("at least one criterion required")
        self.criteria = list(criteria)

    def score(self, values: dict) -> ScoreReport:
        rows, errors = [], []
        for c in self.criteria:
            raw = values.get(c.name, None)
            if raw is None:
                errors.append(f"missing value for {c.name!r}")
                rows.append(dict(name=c.name, value=None, max=str(c.max_score),
                                 weight=str(c.weight), share=None, weighted=None,
                                 error="no data"))
                continue
            v = Decimal(str(raw))
            if v < 0 or v > c.max_score:
                errors.append(f"{c.name!r} out of range 0..{c.max_score} (got {v})")
                rows.append(dict(name=c.name, value=None, max=str(c.max_score),
                                 weight=str(c.weight), share=None, weighted=None,
                                 error="out of range"))
                continue
            share = v / c.max_score
            rows.append(dict(name=c.name, value=str(v), max=str(c.max_score),
                             weight=str(c.weight), share=round(float(share), 6),
                             weighted=str(share * c.weight), error=None))

        usable = [r for r in rows if r["weighted"] is not None]
        if not usable:
            # Nothing measurable: report "no result", never a fake 0.
            return ScoreReport(None, False, rows, errors or ["no usable values"])

        wsum = sum((Decimal(r["weight"]) for r in usable), Decimal(0))
        total = sum((Decimal(r["weighted"]) for r in usable), Decimal(0)) / wsum * 100
        return ScoreReport(total.quantize(Decimal("0.01"), ROUND_HALF_UP),
                           not errors, rows, errors)
