"""离线验证会话访问提醒和販売者名称有效期。"""

import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from uuid import uuid4

from fc2cmadb_crawler.site_state import (
    CachedSeller,
    VisitCounter,
    load_cached_seller,
    save_cached_seller,
)


class SiteStateTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(__file__).resolve().parent.parent / "~outputs" / "test-site-state" / f"{uuid4()}.sqlite3"

    def test_article_and_search_warn_once_at_fifty_but_continue_in_same_session(self):
        counter = VisitCounter()
        output = StringIO()
        with redirect_stdout(output):
            self.assertIsNone(counter.record("https://fc2cmadb.com/actresses/1"))
            for index in range(49):
                self.assertEqual(counter.record(f"https://fc2cmadb.com/articles/{index}"), index + 1)
            self.assertEqual(counter.record("https://fc2cmadb.com/search?stype=writer&keyword=Maker"), 50)
            self.assertEqual(counter.record("https://fc2cmadb.com/articles/999"), 51)
        self.assertEqual(output.getvalue().count("已达 50 次"), 1)
        self.assertEqual(VisitCounter().record("https://fc2cmadb.com/articles/1"), 1)

    def test_seller_current_and_old_names_expire_after_thirty_days(self):
        seller = CachedSeller("Dの計画", ("KING POWER D",), "sangou")
        save_cached_seller(seller, path=self.path, now=1000)
        self.assertEqual(load_cached_seller(" king power d ", path=self.path, now=1001), seller)
        self.assertEqual(load_cached_seller("Dの計画", path=self.path, now=1001), seller)
        self.assertIsNone(load_cached_seller("KING POWER D", path=self.path, now=1000 + 30 * 86400))
