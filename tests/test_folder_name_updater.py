"""验证制作人前文字保留和主程序目录格式复用。"""

import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from fc2cmadb_crawler.naming import format_film_folder_name
from fc2cmadb_crawler.site_state import CachedSeller
from tools import update_fc2_folder_names as updater
from tools.update_fc2_folder_names import (
    FilmMetadata,
    MetadataPacing,
    RenamePlan,
    SiteRateLimited,
    build_target_name,
    classify_rename_reasons,
    extract_number,
    fetch_metadata,
    fetch_metadata_with_pacing,
    make_plan,
    print_preview,
    run_root,
    writer_search_url,
)


class FolderNameUpdaterTests(unittest.TestCase):
    def setUp(self):
        for name in ("load_cached_seller", "save_cached_seller"):
            mocker = patch.object(updater, name, return_value=None)
            setattr(self, name, mocker.start())
            self.addCleanup(mocker.stop)
        auth_patch = patch.object(updater, "prepare_authenticated_session", return_value=True)
        self.auth = auth_patch.start()
        self.addCleanup(auth_patch.stop)

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
            source,
        )

    def test_annotation_after_number_is_untouched_when_producer_changes(self):
        source = "fc2-ppv-3216009=111111111111111 KING POWER D-旧标题"
        metadata = FilmMetadata("3216009", "Dの計画", "新标题", "sangou", ("KING POWER D",))
        self.assertEqual(
            build_target_name(source, metadata, "KING POWER D-2 もも"),
            "fc2-ppv-3216009=111111111111111 Dの計画-旧标题",
        )

    def test_spaced_annotation_uses_writer_slug_to_find_old_producer(self):
        source = "fc2-ppv-3899268_111 素人発掘隊！ 4610hakkutsu-旧标题"
        metadata = FilmMetadata(
            "3899268", "かわいいしろうと Cute amateur", "新标题", "4610hakkutsu",
            ("素人発掘隊！ 4610hakkutsu",),
        )
        self.assertEqual(
            build_target_name(source, metadata),
            "fc2-ppv-3899268_111 かわいいしろうと Cute amateur-旧标题",
        )

    def test_long_title_uses_main_length_limit_without_changing_prefix(self):
        source = "【TT】fc2-ppv-4165309 汁ハッピー☆-旧" + "标题" * 50
        metadata = FilmMetadata("4165309", "汁ハッピー☆", "新标题")
        target = build_target_name(source, metadata)
        self.assertEqual(len(target), 80)
        self.assertTrue(target.startswith("【TT】fc2-ppv-4165309 汁ハッピー☆-"))
        self.assertTrue(target.endswith("+++"))

    def test_long_preserved_prefix_is_not_truncated(self):
        source = "x" * 65 + "fc2-ppv-123 Maker-Old"
        metadata = FilmMetadata("123", "Maker", "New title")
        with self.assertRaisesRegex(ValueError, "标题无法放入"):
            build_target_name(source, metadata)

    def test_rename_reasons_allow_producer_and_truncation_overlap(self):
        self.assertEqual(
            classify_rename_reasons("fc2-ppv-123 Old-旧标题", FilmMetadata("123", "New", "新标题", old_names=("Old",)), ""),
            frozenset({"producer"}),
        )
        self.assertEqual(
            classify_rename_reasons("fc2-ppv-123 Maker-" + "旧" * 100, FilmMetadata("123", "Maker", "新标题"), ""),
            frozenset({"truncation"}),
        )
        self.assertEqual(
            classify_rename_reasons("fc2-ppv-123 Old-" + "旧" * 100, FilmMetadata("123", "New", "新标题", old_names=("Old",)), ""),
            frozenset({"producer", "truncation"}),
        )
        self.assertEqual(
            classify_rename_reasons("fc2-ppv-123 Maker-旧标题", FilmMetadata("123", "Maker", "新标题"), ""),
            frozenset({"other"}),
        )

    def test_preview_counts_skips_and_groups_producer_changes_before_other_details(self):
        root = Path("sample")
        plans = [
            RenamePlan(root / "a", root / "b", "1", frozenset({"producer", "truncation"}), ("Old", "New")),
            RenamePlan(root / "b", root / "c", "2", frozenset({"producer"}), ("Old", "New")),
            RenamePlan(root / "c", root / "d", "3", frozenset({"producer"}), ("Maker", "Studio")),
            RenamePlan(root / "d", root / "e", "4", frozenset({"other"}), None),
        ]
        with redirect_stdout(StringIO()) as output:
            print_preview(plans, ["已符合新名称: sample/old", "404: sample/missing"], 6)
        lines = output.getvalue().splitlines()
        self.assertEqual(lines[:9], [
            "待重命名预览:",
            "匹配目录: 6；待重命名: 4；跳过: 2",
            "改名原因统计（待重命名目录；前两项可重叠）:",
            "- 长度截断: 1",
            "- 制作人名称更新: 3",
            "制作人名称变动: 2 组",
            "- Maker -> Studio: 1 个目录",
            "- Old -> New: 2 个目录",
            "其他原因预览: 1 个目录",
        ])
        self.assertEqual(lines[-3:], ["- [目录] sample", "  d", "  -> e"])
        self.assertNotIn("404: sample/missing", output.getvalue())
        self.assertNotIn("已符合新名称: sample/old", output.getvalue())

    def test_preview_without_other_changes_still_shows_counts(self):
        plan = RenamePlan(Path("sample/old"), Path("sample/new"), "1", frozenset({"truncation"}), None)
        with redirect_stdout(StringIO()) as output:
            print_preview([plan], ["skip details"], 2)
        self.assertIn("其他原因预览: 0 个目录", output.getvalue())
        self.assertNotIn("skip details", output.getvalue())

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

    def test_wrong_straight_quotes_suggest_unique_existing_curly_quote_directory(self):
        parent = Path("sample")
        typed = parent / '千華繚乱"Next"_pure'
        actual = parent / "千華繚乱”Next”_pure"
        expected = typed.absolute()
        with patch.object(Path, "resolve", side_effect=OSError("invalid quote")):
            self.assertEqual(updater.resolve_path(str(typed)), expected)
        with patch.object(Path, "is_dir", autospec=True, side_effect=lambda path: path in {parent, actual}), patch.object(
            Path, "iterdir", autospec=True, side_effect=lambda _path: iter([actual])
        ), patch.object(updater, "is_reparse_directory", return_value=False), redirect_stdout(StringIO()) as output:
            self.assertEqual(updater.suggest_quoted_directory(typed), actual)
            updater.report_unscannable_root(typed)
        self.assertIn(str(actual), output.getvalue())

    def test_ambiguous_quote_variants_are_not_guessed(self):
        parent = Path("sample")
        typed = parent / '千華繚乱"Next"_pure'
        candidates = [parent / "千華繚乱”Next”_pure", parent / "千華繚乱“Next”_pure"]
        with patch.object(Path, "is_dir", return_value=True), patch.object(
            Path, "iterdir", return_value=iter(candidates)
        ), patch.object(updater, "is_reparse_directory", return_value=False):
            self.assertIsNone(updater.suggest_quoted_directory(typed))

    def test_writer_search_reads_current_name_and_exact_old_names(self):
        browser = Mock()
        browser.navigate.return_value = (
            '<script data-page="app">'
            + json.dumps({"component": "Writers/Show", "props": {"writer": {
                "name": "Dの計画", "slug": "sangou",
                "writer_old_names": [{"old_name": "KING POWER D"}],
            }}})
            + "</script>"
        )
        metadata = fetch_metadata(browser, "123", " KING POWER D")
        self.assertEqual(metadata, FilmMetadata("123", "Dの計画", "", "sangou", ("KING POWER D",)))
        browser.navigate.assert_called_with(
            "https://fc2cmadb.com/search?keyword=KING+POWER+D&stype=writer", min_interval_seconds=0
        )
        browser.navigate.return_value = '<script data-page="app">{"component":"Search/Index","props":{}}</script>'
        with self.assertRaisesRegex(ValueError, "唯一的販売者"):
            fetch_metadata(browser, "123", " KING POWER D")
        browser.navigate.return_value = (
            '<script data-page="app">'
            + json.dumps({"component": "Writers/Show", "props": {"writer": {"name": "Other"}}})
            + "</script>"
        )
        with self.assertRaisesRegex(ValueError, "名称与查询词不一致"):
            fetch_metadata(browser, "123", " KING POWER D")

    def test_writer_search_removes_number_annotation_but_keeps_full_old_name(self):
        self.assertEqual(
            writer_search_url("_111 素人発掘隊！ 4610hakkutsu"),
            "https://fc2cmadb.com/search?keyword=%E7%B4%A0%E4%BA%BA%E7%99%BA%E6%8E%98%E9%9A%8A%EF%BC%81+4610hakkutsu&stype=writer",
        )
        self.assertEqual(
            writer_search_url(" KING POWER D"),
            "https://fc2cmadb.com/search?keyword=KING+POWER+D&stype=writer",
        )

    def test_writer_search_list_uses_only_unique_exact_name(self):
        browser = Mock()
        writers = [
            {"name": "ぱすも", "slug": "pasumomonnon", "writer_old_names": []},
            {"name": "ぱすもセカンド", "slug": "pasumomonnon2", "writer_old_names": []},
        ]
        def page(total, entries):
            return '<script data-page="app">' + json.dumps({
                "component": "Search/Writer", "props": {"writers": {"total": total, "data": entries}}
            }) + "</script>"

        browser.navigate.return_value = page(2, writers)
        self.assertEqual(fetch_metadata(browser, "123", " ぱすも").producer, "ぱすも")
        browser.navigate.return_value = page(3, writers)
        with self.assertRaisesRegex(ValueError, "未完整列出"):
            fetch_metadata(browser, "123", " ぱすも")
        browser.navigate.return_value = page(2, [writers[0], dict(writers[0])])
        with self.assertRaisesRegex(ValueError, "唯一的精确名称"):
            fetch_metadata(browser, "123", " ぱすも")

    def test_already_current_folder_is_a_successful_no_op(self):
        with patch("tools.update_fc2_folder_names.make_plan", return_value=([], ["已符合新名称"], 1, 0)):
            with redirect_stdout(StringIO()):
                self.assertEqual(run_root(Path(__file__).parent, Mock(), dry_run=True), 0)

    def test_full_preview_option_shows_all_pending_names_without_renaming(self):
        root = Path(__file__).parent
        plans = [
            RenamePlan(root / "a", root / "new-a", "1", frozenset({"truncation"}), None),
            RenamePlan(root / "b", root / "new-b", "2", frozenset({"other"}), None),
        ]
        with patch.object(updater, "make_plan", return_value=(plans, [], 2, 0)), patch(
            "builtins.input", side_effect=["2", "q"]
        ) as prompt, patch.object(updater, "apply_plan") as apply, redirect_stdout(StringIO()) as output:
            with self.assertRaises(updater.QuitTool):
                run_root(root, Mock())
        self.assertEqual(prompt.call_count, 2)
        apply.assert_not_called()
        self.assertIn("全部待重命名目录预览: 2 个目录", output.getvalue())
        self.assertIn("  a\n  -> new-a", output.getvalue())
        self.assertIn("  b\n  -> new-b", output.getvalue())
        self.assertEqual(output.getvalue().count("2. 预览所有将重命名"), 2)

    def test_full_preview_then_explicit_confirmation_applies_once(self):
        root = Path(__file__).parent
        plan = RenamePlan(root / "old", root / "new", "1", frozenset({"truncation"}), None)
        with patch.object(updater, "make_plan", return_value=([plan], [], 1, 0)), patch(
            "builtins.input", side_effect=["2", "1"]
        ), patch.object(updater, "apply_plan", return_value=(1, 0)) as apply, redirect_stdout(StringIO()):
            self.assertEqual(run_root(root, Mock()), 0)
        apply.assert_called_once_with([plan], root)

    def test_first_rate_limit_stops_fetching_and_shows_empty_partial_preview(self):
        browser = Mock()
        browser.navigate.return_value = '<script data-page="app">{"component":"Error","props":{"status":429}}</script>'
        source = Path("sample/fc2-ppv-123 Maker-Old")
        with patch.object(updater, "find_folders", return_value=([source], [])), patch.object(
            updater, "apply_plan"
        ) as apply, redirect_stdout(StringIO()) as output:
            self.assertEqual(run_root(Path(__file__).parent, browser), 1)
        apply.assert_not_called()
        self.assertEqual(browser.navigate.call_count, 1)
        self.assertEqual(browser._fc2_metadata_pacing.interval_seconds, 12)
        self.assertIn("[停止获取] 站点返回 429", output.getvalue())
        self.assertIn("待重命名: 0；跳过: 1", output.getvalue())

    def test_first_rate_limit_never_retries_same_writer_search(self):
        browser = Mock()
        browser.driver.current_url = "about:blank"
        url = "https://fc2cmadb.com/search?keyword=Maker&stype=writer"
        bad = '<script data-page="app">{"component":"Error","props":{"status":429}}</script>'
        browser.navigate.return_value = bad
        pacing = MetadataPacing()
        with self.assertRaises(SiteRateLimited):
            fetch_metadata_with_pacing(browser, "123", " Maker", pacing)
        browser.navigate.assert_called_once_with(url, min_interval_seconds=12)
        self.assertEqual(pacing.interval_seconds, 12)

    def test_metadata_navigation_receives_configured_interval(self):
        browser = Mock()
        browser.driver.current_url = "about:blank"
        with patch.object(updater, "fetch_metadata", return_value=FilmMetadata("123", "Maker", "Title")) as fetch:
            fetch_metadata_with_pacing(browser, "123", " Maker", MetadataPacing(interval_seconds=12))
        fetch.assert_called_once_with(browser, "123", " Maker", interval_seconds=12)

    def test_increased_interval_applies_to_next_normal_page(self):
        browser = Mock()
        browser.driver.current_url = "about:blank"
        pacing = MetadataPacing(interval_seconds=24)
        with patch.object(updater, "fetch_metadata", return_value=FilmMetadata("124", "Maker", "Title")) as fetch:
            fetch_metadata_with_pacing(browser, "124", " Maker", pacing)
        fetch.assert_called_once_with(browser, "124", " Maker", interval_seconds=24)

    def test_existing_destination_is_skipped_without_overwrite(self):
        source = Path("sample/fc2-ppv-123 Old-Title")
        metadata = FilmMetadata("123", "New", "Title", old_names=("Old",))
        with patch("tools.update_fc2_folder_names.find_folders", return_value=([source], [])), patch(
            "tools.update_fc2_folder_names.fetch_metadata", return_value=metadata
        ), patch.object(Path, "exists", return_value=True):
            plans, skipped, total, issues = make_plan(Path("sample"), Mock())
        self.assertEqual((plans, total, issues), ([], 1, 1))
        self.assertIn("目标目录已存在", skipped[0])

    def test_make_plan_retains_confirmed_old_and_new_producer(self):
        source = Path("sample/fc2-ppv-123 Old-旧标题")
        metadata = FilmMetadata("123", "New", "新标题", old_names=("Old",))
        with patch("tools.update_fc2_folder_names.find_folders", return_value=([source], [])), patch(
            "tools.update_fc2_folder_names.fetch_metadata", return_value=metadata
        ):
            plans, skipped, total, issues = make_plan(Path("sample"), Mock())
        self.assertEqual((len(plans), skipped, total, issues), (1, [], 1, 0))
        self.assertEqual(plans[0].producer_change, ("Old", "New"))
        self.assertIn("producer", plans[0].reasons)
        self.assertEqual(plans[0].target.name, "fc2-ppv-123 New-旧标题")

    def test_same_producer_queries_first_number_only_and_keeps_each_title(self):
        sources = [
            Path("sample/fc2-ppv-123 Old-短标题"),
            Path("sample/fc2-ppv-456 Old-" + "长" * 100),
        ]
        browser = Mock()
        with patch.object(updater, "find_folders", return_value=(sources, [])), patch.object(
            updater, "fetch_metadata", return_value=FilmMetadata("123", "New", "站点标题", old_names=("Old",))
        ) as fetch, redirect_stdout(StringIO()) as output:
            plans, skipped, total, issues = make_plan(Path("sample"), browser)
        fetch.assert_called_once_with(browser, "123", " Old", interval_seconds=12)
        self.assertEqual((len(plans), skipped, total, issues), (2, [], 2, 0))
        self.assertEqual(plans[0].target.name, "fc2-ppv-123 New-短标题")
        self.assertTrue(plans[1].target.name.startswith("fc2-ppv-456 New-长"))
        self.assertTrue(plans[1].target.name.endswith("+++"))
        self.assertIn("本批制作人查询: 1 次", output.getvalue())

    def test_different_producers_query_separately_and_new_batch_resets_cache(self):
        sources = [Path("sample/fc2-ppv-123 Old-A"), Path("sample/fc2-ppv-456 Other-B")]
        browser = Mock()
        def metadata(_browser, number, producer_area, **_kwargs):
            return FilmMetadata(number, "New", "Ignored", old_names=(producer_area.strip(),))

        with patch.object(updater, "find_folders", return_value=(sources, [])), patch.object(
            updater, "fetch_metadata", side_effect=metadata
        ) as fetch, redirect_stdout(StringIO()):
            make_plan(Path("sample"), browser)
            make_plan(Path("sample"), browser)
        self.assertEqual([call.args[1] for call in fetch.call_args_list], ["123", "456", "123", "456"])

    def test_failed_first_lookup_is_not_repeated_for_same_producer(self):
        sources = [Path("sample/fc2-ppv-123 Old-A"), Path("sample/fc2-ppv-456 Old-B")]
        with patch.object(updater, "find_folders", return_value=(sources, [])), patch.object(
            updater, "fetch_metadata", side_effect=ValueError("页面不可用")
        ) as fetch, redirect_stdout(StringIO()):
            plans, skipped, total, issues = make_plan(Path("sample"), Mock())
        self.assertEqual((plans, total, issues), ([], 2, 2))
        self.assertEqual(len(skipped), 2)
        fetch.assert_called_once()

    def test_frequency_prioritizes_seller_queries_before_low_frequency_groups(self):
        sources = [
            Path("sample/fc2-ppv-1 B-B1"),
            Path("sample/fc2-ppv-2 A-A1"),
            Path("sample/fc2-ppv-3 A-A2"),
            Path("sample/fc2-ppv-4 A-A3"),
        ]
        def metadata(_browser, number, area, **_kwargs):
            return FilmMetadata(number, area.strip(), "", old_names=(area.strip(),))

        with patch.object(updater, "find_folders", return_value=(sources, [])), patch.object(
            updater, "fetch_metadata", side_effect=metadata
        ) as fetch, redirect_stdout(StringIO()):
            plans, skipped, total, issues = make_plan(Path("sample"), Mock())
        self.assertEqual((len(plans), len(skipped), total, issues), (0, 4, 4, 0))
        self.assertEqual([call.args[2].strip() for call in fetch.call_args_list], ["A", "B"])

    def test_cached_old_name_skips_search_and_prepares_rename(self):
        self.load_cached_seller.return_value = CachedSeller("New", ("Old",), "new")
        source = Path("sample/fc2-ppv-123 Old-Title")
        with patch.object(updater, "find_folders", return_value=([source], [])), patch.object(
            updater, "fetch_metadata"
        ) as fetch, redirect_stdout(StringIO()) as output:
            plans, skipped, total, issues = make_plan(Path("sample"), Mock())
        fetch.assert_not_called()
        self.assertEqual((len(plans), skipped, total, issues), (1, [], 1, 0))
        self.assertEqual(plans[0].target.name, "fc2-ppv-123 New-Title")
        self.assertIn("本批制作人查询: 0 次", output.getvalue())

    def test_cached_group_is_prepared_before_higher_frequency_uncached_429(self):
        root = Path(__file__).parent
        sources = [
            root / "fc2-ppv-1 CachedOld-Title",
            root / "fc2-ppv-2 Uncached-Title",
            root / "fc2-ppv-3 Uncached-Title",
        ]
        self.load_cached_seller.side_effect = lambda name: (
            CachedSeller("CachedNew", ("CachedOld",), "") if name.casefold() == "cachedold" else None
        )
        with patch.object(updater, "find_folders", return_value=(sources, [])), patch.object(
            updater, "fetch_metadata", side_effect=SiteRateLimited("429")
        ) as fetch, redirect_stdout(StringIO()) as output:
            self.assertEqual(run_root(root, Mock(), dry_run=True), 1)
        fetch.assert_called_once()
        self.assertEqual(fetch.call_args.args[2].strip(), "Uncached")
        self.assertIn("待重命名: 1；跳过: 2", output.getvalue())

    def test_429_after_one_success_only_previews_prepared_rename(self):
        root = Path(__file__).parent
        sources = [root / "fc2-ppv-1 AOld-Title", root / "fc2-ppv-2 BOld-Title"]
        with patch.object(updater, "find_folders", return_value=(sources, [])), patch.object(
            updater, "fetch_metadata", side_effect=[
                FilmMetadata("1", "New", "", old_names=("AOld",)), SiteRateLimited("429")
            ]
        ) as fetch, patch("builtins.input", side_effect=["2", "q"]), patch.object(
            updater, "apply_plan"
        ) as apply, redirect_stdout(StringIO()) as output:
            with self.assertRaises(updater.QuitTool):
                run_root(root, Mock())
        self.assertEqual(fetch.call_count, 2)
        apply.assert_not_called()
        self.assertIn("未处理: 1 个目录", output.getvalue())
        self.assertIn("待重命名: 1；跳过: 1", output.getvalue())
        self.assertIn("全部待重命名目录预览: 1 个目录", output.getvalue())
        self.assertIn("确认重命名已准备的 1 个目录", output.getvalue())

    def test_429_allows_explicit_partial_confirmation(self):
        root = Path(__file__).parent
        sources = [root / "fc2-ppv-1 AOld-Title", root / "fc2-ppv-2 BOld-Title"]
        with patch.object(updater, "find_folders", return_value=(sources, [])), patch.object(
            updater, "fetch_metadata", side_effect=[
                FilmMetadata("1", "New", "", old_names=("AOld",)), SiteRateLimited("429")
            ]
        ), patch("builtins.input", return_value="1"), patch.object(
            updater, "apply_plan", return_value=(1, 0)
        ) as apply, redirect_stdout(StringIO()):
            self.assertEqual(run_root(root, Mock()), 1)
        self.assertEqual(len(apply.call_args.args[0]), 1)
        self.assertEqual(apply.call_args.args[0][0].source, sources[0])

    def test_same_producer_preserves_each_number_prefix_and_annotation(self):
        sources = [
            Path("sample/【A】fc2-ppv-123_1 Old-A"),
            Path("sample/【B】fc2-ppv-456_2 Old-B"),
            Path("sample/【C】fc2-ppv-789_3 Old-C"),
        ]
        def metadata(_browser, number, producer_area, **_kwargs):
            return FilmMetadata(number, "New", "Ignored", old_names=(producer_area.split()[-1],))

        with patch.object(updater, "find_folders", return_value=(sources, [])), patch.object(
            updater, "fetch_metadata", side_effect=metadata
        ) as fetch, redirect_stdout(StringIO()):
            plans, _, _, _ = make_plan(Path("sample"), Mock())
        fetch.assert_called_once()
        self.assertEqual(plans[0].target.name, "【A】fc2-ppv-123_1 New-A")
        self.assertEqual(plans[1].target.name, "【B】fc2-ppv-456_2 New-B")
        self.assertEqual(plans[2].target.name, "【C】fc2-ppv-789_3 New-C")

    def test_undo_does_not_start_chrome(self):
        with patch.object(updater, "PersistentBrowser") as browser, patch.object(
            updater, "undo_menu", return_value=0
        ), redirect_stdout(StringIO()):
            self.assertEqual(updater.main(["--undo"]), 0)
        browser.assert_not_called()
        self.auth.assert_not_called()

    def test_interactive_menu_requires_confirmed_login(self):
        self.auth.return_value = False
        with patch("builtins.input") as prompt, patch.object(updater, "PersistentBrowser") as browser, patch.object(
            updater, "run_root"
        ) as run, redirect_stdout(StringIO()) as output:
            self.assertEqual(updater.main([]), 1)
        prompt.assert_not_called()
        run.assert_not_called()
        self.auth.assert_called_once_with(browser.return_value.__enter__.return_value)
        self.assertIn("未确认站点登录状态", output.getvalue())

    def test_direct_root_requires_confirmed_login_before_scan(self):
        self.auth.return_value = False
        root = Path(__file__).parent
        with patch.object(updater, "PersistentBrowser") as browser, patch.object(
            updater, "run_root"
        ) as run, redirect_stdout(StringIO()) as output:
            self.assertEqual(updater.main([str(root), "--dry-run"]), 1)
        run.assert_not_called()
        self.auth.assert_called_once_with(browser.return_value.__enter__.return_value)
        self.assertIn("本批未扫描", output.getvalue())

    def test_interactive_menu_waits_for_browser_attachment(self):
        attached = False

        class BrowserContext:
            def __enter__(self):
                nonlocal attached
                attached = True
                return Mock()

            def __exit__(self, *args):
                return False

        def choose(*args):
            self.assertTrue(attached)
            return "q"

        with patch("builtins.input", side_effect=choose) as prompt, patch.object(
            updater, "PersistentBrowser", return_value=BrowserContext()
        ), redirect_stdout(StringIO()):
            self.assertEqual(updater.main([]), 0)
        prompt.assert_called_once()
        self.auth.assert_called_once()

    def test_browser_failure_does_not_show_interactive_menu(self):
        with patch("builtins.input") as prompt, patch.object(
            updater, "PersistentBrowser", side_effect=RuntimeError("browser unavailable")
        ), redirect_stdout(StringIO()) as output:
            self.assertEqual(updater.main([]), 1)
        prompt.assert_not_called()
        self.assertIn("browser unavailable", output.getvalue())

    def test_multiple_roots_reuse_one_browser(self):
        root = Path(__file__).parent
        fake_browser = Mock()
        with patch("builtins.input", side_effect=["1", str(root), str(root), "q"]), patch.object(
            updater, "PersistentBrowser"
        ) as browser, patch.object(updater, "run_root", return_value=0) as run, redirect_stdout(StringIO()):
            browser.return_value.__enter__.return_value = fake_browser
            self.assertEqual(updater.main([]), 0)
        browser.assert_called_once_with()
        self.auth.assert_called_once_with(fake_browser)
        self.assertEqual(run.call_count, 2)
        self.assertIs(run.call_args_list[0].args[1], fake_browser)
        self.assertIs(run.call_args_list[1].args[1], fake_browser)

    def test_interval_option_initializes_pacing_before_reading_pages(self):
        root = Path(__file__).parent
        fake_browser = Mock()

        def inspect_pacing(_root, browser, **_kwargs):
            self.assertEqual(browser._fc2_metadata_pacing.interval_seconds, 12)
            return 0

        with patch.object(updater, "PersistentBrowser") as browser, patch.object(
            updater, "run_root", side_effect=inspect_pacing
        ) as run, redirect_stdout(StringIO()):
            browser.return_value.__enter__.return_value = fake_browser
            self.assertEqual(updater.main([str(root), "--dry-run", "--interval", "12"]), 0)
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
