import csv
import unittest
from pathlib import Path

from scripts.comment_text_analysis import (
    EXPECTED_COMMENT_FIELDS,
    build_group_summary,
    compare_keywords,
    load_comments_rows,
    rank_group_from_rank,
    tokenize_text,
)


class CommentTextAnalysisTests(unittest.TestCase):
    def test_rank_group_from_rank(self) -> None:
        self.assertEqual(rank_group_from_rank(1), "top_100")
        self.assertEqual(rank_group_from_rank(100), "top_100")
        self.assertEqual(rank_group_from_rank(250), "rank_101_299")
        self.assertEqual(rank_group_from_rank(300), "rank_300_500")
        self.assertEqual(rank_group_from_rank(500), "rank_300_500")

    def test_tokenize_text_filters_stopwords(self) -> None:
        tokens = tokenize_text("This mod is amazing and useful for every server.")
        self.assertIn("amazing", tokens)
        self.assertIn("useful", tokens)
        self.assertIn("server", tokens)
        self.assertNotIn("this", tokens)
        self.assertNotIn("mod", tokens)

    def test_compare_keywords_prefers_group_specific_terms(self) -> None:
        rows = [
            {"mod_id": "1", "rank_group": "top_100", "content_text": "great useful amazing"},
            {"mod_id": "1", "rank_group": "top_100", "content_text": "amazing useful quality"},
            {"mod_id": "2", "rank_group": "rank_300_500", "content_text": "bug broken crash"},
            {"mod_id": "2", "rank_group": "rank_300_500", "content_text": "crash issue broken"},
            {"mod_id": "2", "rank_group": "rank_300_500", "content_text": "bug issue lag"},
        ]
        comparison = compare_keywords(
            rows,
            left_group="top_100",
            right_group="rank_300_500",
            min_comment_count=2,
        )
        dominant = {row["token"]: row["dominant_group"] for row in comparison}
        self.assertEqual(dominant["amazing"], "top_100")
        self.assertEqual(dominant["broken"], "rank_300_500")

    def test_build_group_summary(self) -> None:
        rows = [
            {"mod_id": "1", "rank_group": "top_100", "content_text": "great"},
            {"mod_id": "1", "rank_group": "top_100", "content_text": "great"},
            {"mod_id": "2", "rank_group": "rank_300_500", "content_text": "bad"},
        ]
        summary = build_group_summary(rows, ["top_100", "rank_300_500"])
        self.assertEqual(summary[0]["comment_count"], 2)
        self.assertEqual(summary[0]["mod_count"], 1)
        self.assertEqual(summary[1]["comment_count"], 1)
        self.assertEqual(summary[1]["mod_count"], 1)

    def test_load_comments_rows_handles_headerless_csv(self) -> None:
        row = [
            "batch_1",
            "2026-03-19T12:00:00+00:00",
            "376333686",
            "Combined Status",
            "9509495",
            "1",
            "top_100",
            "1",
            "123",
            "tester",
            "https://example.com",
            "7656119",
            "111",
            "1773779314",
            "2026-03-17T20:28:34+00:00",
            "17 Mar @ 1:28pm",
            "reliable useful",
            "reliable useful",
            "data/raw/example.html",
        ]
        path = Path(__file__).resolve().parents[1] / ".codex_tmp" / "headerless_top_comments_test.csv"
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            path.unlink()
        try:
            with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(row)
            rows = load_comments_rows(path)
        finally:
            if path.exists():
                path.unlink()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["rank_group"], "top_100")
        self.assertEqual(list(rows[0].keys()), EXPECTED_COMMENT_FIELDS)


if __name__ == "__main__":
    unittest.main()
