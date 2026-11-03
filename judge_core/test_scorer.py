"""Self-checks for judge_core.scorer. Run: python -m judge_core.test_scorer"""
import unittest
from decimal import Decimal

from .scorer import Criterion, Scorer, ScoringConfigError


class TestScorer(unittest.TestCase):
    def setUp(self):
        self.s = Scorer([Criterion.of("logic", 2, 10), Criterion.of("style", 1, 5)])

    def test_full_score(self):
        r = self.s.score({"logic": 10, "style": 5})
        self.assertEqual(r.total, Decimal("100.00"))
        self.assertTrue(r.complete)

    def test_partial_is_weighted(self):
        r = self.s.score({"logic": 8, "style": 4})
        self.assertEqual(r.total, Decimal("80.00"))

    def test_no_data_is_not_zero(self):
        r = self.s.score({"logic": 11})
        self.assertIsNone(r.total)          # the bug I fixed
        self.assertFalse(r.complete)
        self.assertIn("out of range", " ".join(r.errors))

    def test_empty_input(self):
        r = self.s.score({})
        self.assertIsNone(r.total)
        self.assertEqual(len(r.errors), 2)

    def test_order_does_not_change_result(self):
        a = self.s.score({"logic": 7, "style": 3}).total
        b = Scorer([Criterion.of("style", 1, 5), Criterion.of("logic", 2, 10)]) \
            .score({"style": 3, "logic": 7}).total
        self.assertEqual(a, b)

    def test_zero_weight_raises(self):
        with self.assertRaises(ScoringConfigError):
            Criterion.of("bad", 0, 10)

    def test_zero_max_raises(self):
        with self.assertRaises(ScoringConfigError):
            Criterion.of("bad", 1, 0)

    def test_no_criteria_raises(self):
        with self.assertRaises(ScoringConfigError):
            Scorer([])

    def test_csv_roundtrip_shape(self):
        csv_text = self.s.score({"logic": 8, "style": 4}).to_csv()
        self.assertIn("criterion,value,max,weight,share,weighted,error", csv_text)
        self.assertIn("TOTAL,80.00", csv_text)


if __name__ == "__main__":
    unittest.main()
