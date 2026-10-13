"""验证数字键 2 的 FC2 番号输入和详情页演员解析。"""

import unittest
from unittest.mock import patch

from bs4 import BeautifulSoup

from fc2cmadb_crawler import crawler


class Fc2NumberInputTests(unittest.TestCase):
    def test_digit_two_opens_fc2_number_mode(self):
        with patch("builtins.input", side_effect=["2", "1035965"]):
            target = crawler.choose_crawler_target(10436)

        self.assertEqual(target.kind, "fc2_number")
        self.assertEqual(target.value, "1035965")

    def test_direct_multi_digit_input_remains_actress_id(self):
        with patch("builtins.input", return_value="10436"):
            target = crawler.choose_crawler_target(999)

        self.assertEqual(target.kind, "actress_id")
        self.assertEqual(target.value, "10436")

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

            def get(self, _url):
                return None

            def execute_script(self, _script):
                return True

        self.assertEqual(
            crawler.resolve_actress_id_from_fc2_number(FakeDriver(), "1035965"),
            "10436",
        )

    def test_main_checks_login_before_showing_input_menu(self):
        events = []

        class FakeDriver:
            def get(self, url):
                events.append(("get", url))

            def quit(self):
                events.append(("quit", None))

        def logged_in(_driver):
            events.append(("login", None))
            return True

        def choose_target(_default):
            events.append(("input", None))
            return None

        with patch.object(crawler, "create_driver", return_value=FakeDriver()), patch.object(
            crawler, "is_logged_in", side_effect=logged_in
        ), patch.object(crawler, "choose_crawler_target", side_effect=choose_target), patch.object(
            crawler.time, "sleep", return_value=None
        ):
            self.assertEqual(crawler.main(), 0)

        self.assertLess(events.index(("login", None)), events.index(("input", None)))


if __name__ == "__main__":
    unittest.main()
