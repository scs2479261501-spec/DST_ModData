import unittest

from scripts.dashboard_export import (
    build_author_bucket_summary,
    build_author_concentration_summary,
    build_comment_group_summary,
    bucket_author_mod_count,
    enrich_author_rows,
)


class DashboardExportTests(unittest.TestCase):
    def test_bucket_author_mod_count(self) -> None:
        self.assertEqual(bucket_author_mod_count(1), "1")
        self.assertEqual(bucket_author_mod_count(3), "2-3")
        self.assertEqual(bucket_author_mod_count(8), "4-9")
        self.assertEqual(bucket_author_mod_count(12), "10+")

    def test_enrich_author_rows_and_concentration(self) -> None:
        rows = [
            {
                "creator_id": "b",
                "mod_count": "12",
                "total_subscriptions": "2000",
                "avg_subscriptions": "166.67",
                "median_subscriptions": "120",
                "avg_positive_rate": "0.9",
                "avg_maintenance_days": "20",
                "tag_breadth": "4",
            },
            {
                "creator_id": "a",
                "mod_count": "1",
                "total_subscriptions": "5000",
                "avg_subscriptions": "5000",
                "median_subscriptions": "5000",
                "avg_positive_rate": "0.99",
                "avg_maintenance_days": "100",
                "tag_breadth": "1",
            },
            {
                "creator_id": "c",
                "mod_count": "2",
                "total_subscriptions": "1000",
                "avg_subscriptions": "500",
                "median_subscriptions": "500",
                "avg_positive_rate": "0.8",
                "avg_maintenance_days": "5",
                "tag_breadth": "2",
            },
        ]
        enriched = enrich_author_rows(rows)
        self.assertEqual(enriched[0]["creator_id"], "a")
        self.assertEqual(enriched[0]["author_rank"], 1)
        self.assertEqual(enriched[1]["productivity_bucket"], "10+")
        self.assertAlmostEqual(enriched[-1]["cumulative_share_pct"], 100.0)

        concentration = build_author_concentration_summary(enriched)[0]
        self.assertEqual(concentration["author_count"], 3)
        self.assertEqual(concentration["top_10_share_pct"], 100.0)

        bucket_summary = build_author_bucket_summary(enriched)
        summary_by_bucket = {row["productivity_bucket"]: row for row in bucket_summary}
        self.assertEqual(summary_by_bucket["1"]["author_count"], 1)
        self.assertEqual(summary_by_bucket["10+"]["author_count"], 1)

    def test_build_comment_group_summary(self) -> None:
        selected_rows = [
            {"mod_id": "1", "rank_group": "top_100"},
            {"mod_id": "2", "rank_group": "top_100"},
            {"mod_id": "3", "rank_group": "rank_300_500"},
        ]
        comment_rows = [
            {"mod_id": "1", "rank_group": "top_100", "content_text": "great reliable"},
            {"mod_id": "1", "rank_group": "top_100", "content_text": ""},
            {"mod_id": "3", "rank_group": "rank_300_500", "content_text": "love character"},
        ]
        summary = build_comment_group_summary(selected_rows, comment_rows)
        summary_by_group = {row["rank_group"]: row for row in summary}
        self.assertEqual(summary_by_group["top_100"]["selected_mod_count"], 2)
        self.assertEqual(summary_by_group["top_100"]["mods_with_comments"], 1)
        self.assertEqual(summary_by_group["top_100"]["comment_count"], 2)
        self.assertEqual(summary_by_group["top_100"]["tokenized_comment_count"], 1)
        self.assertEqual(summary_by_group["rank_300_500"]["mod_coverage_pct"], 100.0)


if __name__ == "__main__":
    unittest.main()
