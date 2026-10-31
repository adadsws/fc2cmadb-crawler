"""验证制作人前文字保留和主程序目录格式复用。"""

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from fc2cmadb_crawler.naming import format_film_folder_name
from tools.update_fc2_folder_names import (
    FilmMetadata,
    build_target_name,
    extract_number,
    fetch_metadata,
    make_plan,
    run_root,
)


class FolderNameUpdaterTests(unittest.TestCase):
    def test_main_crawler_format_is_shared(self):
        self.assertEqual(
            format_film_folder_name("123", "Maker", "A/B?"),
            "fc2-ppv-123 Maker-A B",
        )
        long_name = format_film_folder_name("4165309", "Maker", "x" * 100)
        self.assertEqual(len(long_name), 80)
        self.assertTrue(long_name.endswith("+++"))

    def test_prefix_before_fc2_marker_is_untouched(self):
        source = "【TT】fc2-ppv-4165309 汁ハッピー☆-旧标题"
        metadata = FilmMetadata("4165309", "汁ハッピー☆", "新标题")
        self.assertEqual(
            build_target_name(source, metadata),
            "【TT】fc2-ppv-4165309 汁ハッピー☆-新标题",
        )

    def test_annotation_after_number_is_untouched_when_producer_changes(self):
        source = "fc2-ppv-3216009=111111111111111 KING POWER D-旧标题"
        metadata = FilmMetadata("3216009", "Dの計画", "新标题", "sangou")
        self.assertEqual(
            build_target_name(source, metadata, "KING POWER D-2 もも"),
            "fc2-ppv-3216009=111111111111111 Dの計画-新标题",
        )

    def test_spaced_annotation_uses_writer_slug_to_find_old_producer(self):
        source = "fc2-ppv-3899268_111 素人発掘隊！ 4610hakkutsu-旧标题"
        metadata = FilmMetadata("3899268", "かわいいしろうと Cute amateur", "新标题", "4610hakkutsu")
        self.assertEqual(
            build_target_name(source, metadata),
            "fc2-ppv-3899268_111 素人発掘隊！ かわいいしろうと Cute amateur-新标题",
        )

    def test_long_title_uses_main_length_limit_without_changing_prefix(self):
        source = "【TT】fc2-ppv-4165309 汁ハッピー☆-旧标题"
        metadata = FilmMetadata("4165309", "汁ハッピー☆", "新" * 100)
        target = build_target_name(source, metadata)
        self.assertEqual(len(target), 80)
        self.assertTrue(target.startswith("【TT】fc2-ppv-4165309 汁ハッピー☆-"))
        self.assertTrue(target.endswith("+++"))

    def test_long_preserved_prefix_is_not_truncated(self):
        source = "x" * 65 + "fc2-ppv-123 Maker-Old"
        metadata = FilmMetadata("123", "Maker", "New title")
        with self.assertRaisesRegex(ValueError, "标题无法放入"):
            build_target_name(source, metadata)

    def test_ambiguous_old_producer_is_not_guessed(self):
        source = "fc2-ppv-3899268_111 素人発掘隊！ 旧制作人-旧标题"
        metadata = FilmMetadata("3899268", "新制作人", "新标题", "unknown")
        with self.assertRaisesRegex(ValueError, "无法确定保留边界"):
            build_target_name(source, metadata)

    def test_missing_or_multiple_numbers_are_rejected(self):
        with self.assertRaises(ValueError):
            extract_number("fc2-ppv-abc Maker-Title")
        with self.assertRaises(ValueError):
            extract_number("fc2-ppv-123 fc2-ppv-456 Maker-Title")

    def test_site_article_must_match_requested_number(self):
        session = Mock()
        response = session.get.return_value
        response.text = (
            '<script data-page="app">'
            + json.dumps({"props": {"article": {"video_id": 123, "title": "Title", "writer": {"name": "Maker", "slug": "slug"}}}})
            + "</script>"
        )
        metadata = fetch_metadata(session, "123")
        self.assertEqual(metadata, FilmMetadata("123", "Maker", "Title", "slug"))
        with self.assertRaisesRegex(ValueError, "番号与目录番号不一致"):
            fetch_metadata(session, "456")

    def test_already_current_folder_is_a_successful_no_op(self):
        with patch("tools.update_fc2_folder_names.make_plan", return_value=([], ["已符合新名称"], 1, 0)):
            with redirect_stdout(StringIO()):
                self.assertEqual(run_root(Path(__file__).parent, Mock(), dry_run=True), 0)

    def test_existing_destination_is_skipped_without_overwrite(self):
        source = Path("sample/fc2-ppv-123 Old-Title")
        metadata = FilmMetadata("123", "New", "Title")
        with patch("tools.update_fc2_folder_names.find_folders", return_value=([source], [])), patch(
            "tools.update_fc2_folder_names.fetch_metadata", return_value=metadata
        ), patch.object(Path, "exists", return_value=True):
            plans, skipped, total, issues = make_plan(Path("sample"), Mock())
        self.assertEqual((plans, total, issues), ([], 1, 1))
        self.assertIn("目标目录已存在", skipped[0])


if __name__ == "__main__":
    unittest.main()
