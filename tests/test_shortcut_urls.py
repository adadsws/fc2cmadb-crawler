import unittest

from fc2cmadb_crawler import crawler


class ShortcutUrlTests(unittest.TestCase):
    def test_latest_shortcut_uses_explicit_first_page_url(self):
        build_url = getattr(crawler, "build_actress_page_url", lambda *_: "")

        self.assertEqual(
            build_url(10436),
            "https://fc2cmadb.com/actresses/10436?page=1",
        )


if __name__ == "__main__":
    unittest.main()
