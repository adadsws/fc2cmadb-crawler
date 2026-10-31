"""验证数字键 2 的 FC2 番号输入和详情页演员解析。"""

import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

from fc2cmadb_crawler import crawler


FIXTURES = Path(__file__).parent / "fixtures"


class Fc2NumberInputTests(unittest.TestCase):
    def test_blank_main_input_does_not_select_mode(self):
        with patch("builtins.input", side_effect=["", "q"]):
            self.assertIsNone(crawler.choose_crawler_target(10436))

    def test_blank_actress_input_does_not_select_example_id(self):
        with patch("builtins.input", side_effect=["1", "", "2"]):
            target = crawler.choose_crawler_target(10436)
        self.assertEqual(target.value, "2")

    def test_closed_input_exits_instead_of_repeating_default_crawl(self):
        with patch("builtins.input", side_effect=EOFError):
            self.assertIsNone(crawler.choose_crawler_target(10436))

    def test_digit_two_opens_fc2_number_mode(self):
        with patch("builtins.input", side_effect=["2", "1035965"]):
            target = crawler.choose_crawler_target(10436)

        self.assertEqual(target.kind, "fc2_number")
        self.assertEqual(target.value, "1035965")

    def test_direct_multi_digit_input_is_not_a_mode(self):
        with patch("builtins.input", side_effect=["10436", "q"]):
            self.assertIsNone(crawler.choose_crawler_target(999))

    def test_selected_mode_can_read_next_number_without_menu(self):
        with patch("builtins.input", side_effect=["4982165"]) as read_input:
            target = crawler.choose_crawler_target(10436, "fc2_number")
        self.assertEqual(target, crawler.CrawlerTarget("fc2_number", "4982165"))
        read_input.assert_called_once()

    def test_back_returns_to_mode_menu(self):
        with patch("builtins.input", side_effect=["b", "1", "10436"]):
            target = crawler.choose_crawler_target(10436, "fc2_number")
        self.assertEqual(target, crawler.CrawlerTarget("actress_id", "10436"))

    def test_digit_one_can_explicitly_enter_actress_id_two(self):
        with patch("builtins.input", side_effect=["1", "2"]):
            target = crawler.choose_crawler_target(10436)

        self.assertEqual(target.kind, "actress_id")
        self.assertEqual(target.value, "2")

    def test_extracts_unique_actress_from_inertia_article(self):
        soup = BeautifulSoup(
            """
            <script data-page="app">
              {"props":{"article":{"video_id":"1035965","actresses":[{"id":10436}]}}}
            </script>
            """,
            "html.parser",
        )
        self.assertEqual(crawler.extract_actress_ids_from_article(soup), ["10436"])

    def test_rejects_ambiguous_article_cast(self):
        soup = BeautifulSoup(
            """
            <main><article>
              <a href="/actresses/10">A</a>
              <a href="/actresses/20">B</a>
            </article></main>
            """,
            "html.parser",
        )
        self.assertEqual(crawler.extract_actress_ids_from_article(soup), ["10", "20"])

    def test_article_url_requires_digits(self):
        self.assertEqual(
            crawler.build_article_page_url("1035965"),
            "https://fc2cmadb.com/articles/1035965",
        )
        with self.assertRaises(ValueError):
            crawler.build_article_page_url("FC2-1035965")

    def test_resolves_unique_actress_id_from_fc2_article(self):
        class FakeDriver:
            current_url = "https://fc2cmadb.com/articles/1035965"
            title = "FC2 1035965"
            page_source = """
                <script data-page="app">
                  {"props":{"article":{"actress":{"id":10436}}}}
                </script>
            """

            def execute_script(self, _script):
                return True

        class FakeBrowser:
            def __init__(self):
                self.driver = FakeDriver()
                self.visited = []

            def navigate(self, url):
                self.visited.append(url)
                return self.driver.page_source

        browser = FakeBrowser()
        self.assertEqual(crawler.resolve_actress_id_from_fc2_number(browser, "1035965"), "10436")
        self.assertEqual(browser.visited, ["https://fc2cmadb.com/articles/1035965"])

    def test_waits_for_hydrated_actress_link_when_inertia_article_has_no_cast(self):
        class DynamicDriver:
            current_url = "https://fc2cmadb.com/articles/4982165"
            title = "FC2 4982165"

            def __init__(self):
                self.read_count = 0

            @property
            def page_source(self):
                self.read_count += 1
                if self.read_count == 1:
                    return (
                        '<script data-page="app">'
                        '{"component":"Articles/Show","props":{"article":{"video_id":"4982165"}}}'
                        "</script><main></main>"
                    )
                return (FIXTURES / "fc2_article_hydrated.html").read_text(encoding="utf-8")

        class FakeBrowser:
            def __init__(self):
                self.driver = DynamicDriver()

            def navigate(self, _url):
                return None

        browser = FakeBrowser()
        self.assertEqual(crawler.resolve_actress_id_from_fc2_number(browser, "4982165"), "10436")
        self.assertGreaterEqual(browser.driver.read_count, 2)

    def test_main_checks_login_before_showing_input_menu(self):
        events = []

        class FakeBrowser:
            def __init__(self):
                self.driver = object()

            def close(self):
                events.append(("close", None))

        def prepare(_browser):
            events.append(("login", None))
            return True

        def choose_target(_default, _mode):
            events.append(("input", None))
            return None

        with patch.object(crawler, "PersistentBrowser", return_value=FakeBrowser()), patch.object(
            crawler, "prepare_authenticated_session", side_effect=prepare
        ), patch.object(crawler, "choose_crawler_target", side_effect=choose_target):
            self.assertEqual(crawler.main(), 0)

        self.assertLess(events.index(("login", None)), events.index(("input", None)))
        self.assertEqual(events[-1], ("close", None))

    def test_main_keeps_fc2_mode_after_each_task(self):
        browser = unittest.mock.Mock()
        with patch("builtins.input", side_effect=["2", "1035965", "4982165", "b", "q"]), patch.object(
            crawler, "PersistentBrowser", return_value=browser
        ), patch.object(crawler, "prepare_authenticated_session", return_value=True), patch.object(
            crawler, "resolve_actress_id_from_fc2_number", return_value="10436"
        ) as resolve, patch.object(crawler, "crawl_actress", return_value=0) as crawl:
            self.assertEqual(crawler.main(), 0)

        self.assertEqual([call.args[1] for call in resolve.call_args_list], ["1035965", "4982165"])
        self.assertEqual(crawl.call_count, 2)


if __name__ == "__main__":
    unittest.main()
