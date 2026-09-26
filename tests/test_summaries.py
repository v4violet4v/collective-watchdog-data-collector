import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from summaries import enrich_snapshots, lightweight_events
from normalize import money_millions, first_present


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.events = [{"markets": [{"outcomes": [{"source_token_id": "yes", "probability": .55, "probability_source": "clob_midpoint"}], "price_history": [1], "volume_history": [2]}]}]
        self.now = "2026-09-26T00:00:00+00:00"
        self.ts = 1790380800

    def row(self, age, source="clob_midpoint"):
        return {"t": self.ts-age, "p": .4, "source": source}

    def test_same_outcome_source_and_percentage_points(self):
        enrich_snapshots(self.events, {"yes": [self.row(86400), self.row(86300)]}, self.now)
        outcome = self.events[0]["markets"][0]["outcomes"][0]
        self.assertEqual(outcome["change_24h_pp"], 15)
        self.assertEqual(outcome["comparison_at"], self.ts-86400)

    def test_missing_stale_or_incompatible_is_unavailable(self):
        for rows in ([], [self.row(86400+21601)], [self.row(86400,"gamma_outcome_price")], [self.row(86300)]):
            enrich_snapshots(self.events, {"yes": rows}, self.now)
            self.assertIsNone(self.events[0]["markets"][0]["outcomes"][0]["change_24h_pp"])

    def test_summary_has_no_charts(self):
        market = lightweight_events(self.events)[0]["markets"][0]
        self.assertNotIn("price_history", market)
        self.assertNotIn("volume_history", market)

    def test_missing_zero_and_small_amounts_are_distinct(self):
        self.assertIsNone(money_millions(None))
        self.assertIsNone(money_millions("bad"))
        self.assertEqual(money_millions(0), 0)
        self.assertEqual(money_millions(125), .000125)
        self.assertEqual(first_present(0, 100), 0)

if __name__ == "__main__":
    unittest.main()
