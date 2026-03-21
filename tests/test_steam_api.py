from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.steam_api import flatten_published_file


SAMPLE_ROOT = Path(__file__).resolve().parents[1] / "data" / "sample" / "steam_api"


class SteamApiTests(unittest.TestCase):
    def test_flatten_published_file_expands_vote_data(self) -> None:
        payload = json.loads((SAMPLE_ROOT / "queryfiles_response.json").read_text(encoding="utf-8"))
        first = payload["response"]["publishedfiledetails"][0]

        row = flatten_published_file(
            first,
            batch_id="test_batch",
            crawl_time_utc="2026-03-19T00:00:00+00:00",
            api_page=1,
        )

        self.assertEqual(row["publishedfileid"], "661253977")
        self.assertEqual(row["votes_up"], 84059)
        self.assertEqual(row["votes_down"], 426)
        self.assertGreater(row["score"], 0.9)
        self.assertEqual(row["api_page"], 1)


if __name__ == "__main__":
    unittest.main()
