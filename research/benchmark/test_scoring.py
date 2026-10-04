"""python -m unittest research/benchmark/test_scoring.py   (from research/benchmark, with research/.venv)"""
import unittest

import bench
import scoring

S, O, D = scoring.SUBJ, scoring.OBJ, scoring.DAT


class Scoring(unittest.TestCase):
    def test_reordering_dependents_keeps_the_tree_for_the_unordered_match(self):
        a = ("ser", (O, ("doge",)), (S, ("kide",)))
        b = ("ser", (S, ("kide",)), (O, ("doge",)))
        self.assertTrue(scoring.tree_match(a, b))
        self.assertFalse(scoring.tree_match(a, b, ordered=True))

    def test_a_different_tree_does_not_match(self):
        a = ("ser", (O, ("doge",)), (S, ("kide",)))
        b = ("ser", (O, ("kide",)), (S, ("doge",)))
        self.assertFalse(scoring.tree_match(a, b))

    def test_unmarked_order(self):
        self.assertEqual(scoring.violations(("ser", (O, ("doge",)), ("vir",), (S, ("kide",)))), [])
        self.assertTrue(scoring.violations(("ser", (S, ("kide",)), (O, ("doge",)))))          # subject not last
        self.assertTrue(scoring.violations(("ser", ("vir",), (O, ("doge",)), (S, ("kide",)))))  # modifier before complement

    def test_the_of_phrase_comes_before_the_determiner(self):
        the, of = "l", "d"
        self.assertEqual(scoring.violations(("buk", (of, ("lor",)), (the,))), [])
        self.assertTrue(scoring.violations(("buk", (the,), (of, ("lor",)))))

    def test_duplicate_dependents_are_compared_as_a_multiset(self):
        self.assertTrue(scoring.tree_match(("s", ("tov",), ("tur",), ("tov",)), ("s", ("tur",), ("tov",), ("tov",))))
        self.assertFalse(scoring.tree_match(("s", ("tov",), ("tov",)), ("s", ("tov",), ("tur",))))


if __name__ == "__main__":
    unittest.main()
