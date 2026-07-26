from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", SyntaxWarning)
    from fc2cmadb_crawler import crawler


class FindCookieFileTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.secrets_dir = self.base / "secrets"
        self.cwd = self.base / "cwd"
        self.project_root = self.base / "project"
        for path in (self.secrets_dir, self.cwd, self.project_root):
            path.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def find_cookie(self):
        with (
            patch.object(crawler, "SECRETS_DIR", str(self.secrets_dir)),
            patch.object(crawler, "SCRIPT_DIR", str(self.project_root)),
            patch.object(crawler.os, "getcwd", return_value=str(self.cwd)),
        ):
            return crawler.find_cookie_file("cookies.txt")

    def test_prefers_secrets_directory(self):
        secret = self.secrets_dir / "cookies.txt"
        secret.write_text("secret", encoding="utf-8")
        (self.cwd / "cookies.txt").write_text("cwd", encoding="utf-8")
        (self.project_root / "cookies.txt").write_text("root", encoding="utf-8")
        self.assertTrue(Path(self.find_cookie()).samefile(secret))

    def test_falls_back_to_legacy_project_root(self):
        legacy = self.project_root / "cookies.txt"
        legacy.write_text("root", encoding="utf-8")
        self.assertTrue(Path(self.find_cookie()).samefile(legacy))

    def test_returns_none_when_no_cookie_exists(self):
        self.assertIsNone(self.find_cookie())


if __name__ == "__main__":
    unittest.main()
