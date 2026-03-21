from __future__ import annotations

import unittest
from pathlib import Path

from scripts.steam_workshop import (
    parse_workshop_browse_page,
    parse_workshop_comments_page,
    parse_workshop_detail_page,
)


FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "data" / "sample" / "steam_workshop" / "raw_validation"


class SteamWorkshopParserTests(unittest.TestCase):
    def test_parse_browse_page(self) -> None:
        html = (FIXTURE_ROOT / "browse_page_0001.html").read_text(encoding="utf-8")
        parsed = parse_workshop_browse_page(
            html,
            source_url="https://steamcommunity.com/workshop/browse/?appid=322330&p=1",
            page_number=1,
        )

        self.assertEqual(parsed["page_number"], 1)
        self.assertGreater(parsed["total_entries"], 1000)
        self.assertGreaterEqual(len(parsed["items"]), 30)
        self.assertEqual(parsed["items"][0]["mod_id"], "661253977")
        self.assertEqual(parsed["items"][0]["title"], "Don't Drop Everything")

    def test_parse_detail_page(self) -> None:
        html = (FIXTURE_ROOT / "detail_376333686.html").read_text(encoding="utf-8")
        parsed = parse_workshop_detail_page(
            html,
            source_url="https://steamcommunity.com/sharedfiles/filedetails/?id=376333686",
        )

        self.assertEqual(parsed["mod_id"], "376333686")
        self.assertEqual(parsed["title"], "Combined Status")
        self.assertEqual(parsed["owner_steam_id"], "76561198025931302")
        self.assertIsNotNone(parsed["current_subscribers"])
        self.assertIsNotNone(parsed["updated_at_naive"])
        self.assertGreater(parsed["ratings_count"], 0)

    def test_parse_comments_page(self) -> None:
        html = (FIXTURE_ROOT / "comments_661253977_ctp_1.html").read_text(encoding="utf-8")
        parsed = parse_workshop_comments_page(
            html,
            mod_id="661253977",
            comment_page=1,
        )

        self.assertGreaterEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["comment_id"], "805719856669380288")
        self.assertEqual(parsed[0]["commenter_name"], "local dumbass")
        self.assertIsNotNone(parsed[0]["comment_timestamp_epoch"])

        non_empty_comments = [comment for comment in parsed if comment["content_text"]]
        self.assertGreaterEqual(len(non_empty_comments), 1)


if __name__ == "__main__":
    unittest.main()
