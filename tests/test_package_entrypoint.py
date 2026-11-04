import importlib.util
import runpy
import unittest
from unittest.mock import patch


class PackageEntrypointTests(unittest.TestCase):
    def test_module_entrypoint_returns_crawler_exit_code(self):
        self.assertIsNotNone(
            importlib.util.find_spec("fc2cmadb_crawler.main"),
            "package entrypoint module is missing",
        )

        with patch("fc2cmadb_crawler.crawler.main", return_value=23):
            with self.assertRaises(SystemExit) as caught:
                runpy.run_module("fc2cmadb_crawler.main", run_name="__main__")

        self.assertEqual(caught.exception.code, 23)


if __name__ == "__main__":
    unittest.main()
