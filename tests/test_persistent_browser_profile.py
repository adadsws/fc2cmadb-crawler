from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fc2cmadb_crawler import crawler


class FakeChromeOptions:
    def __init__(self):
        self.arguments = []

    def add_argument(self, argument):
        self.arguments.append(argument)


class FakeDriver:
    def __init__(self):
        self.maximized = False

    def maximize_window(self):
        self.maximized = True


class PersistentBrowserProfileTests(unittest.TestCase):
    def test_create_driver_uses_the_dedicated_persistent_profile(self):
        with TemporaryDirectory() as temporary_directory:
            profile_directory = Path(temporary_directory) / "crawler-profile"
            options = FakeChromeOptions()
            driver = FakeDriver()

            with (
                patch.object(crawler, "CHROME_PROFILE_DIR", profile_directory, create=True),
                patch.object(crawler.uc, "ChromeOptions", return_value=options),
                patch.object(crawler.uc, "Chrome", return_value=driver),
            ):
                crawler.create_driver()

            self.assertTrue(profile_directory.is_dir())
            self.assertIn(f"--user-data-dir={profile_directory}", options.arguments)
            self.assertTrue(driver.maximized)

    def test_is_logged_in_reads_the_inertia_auth_user(self):
        class Driver:
            page_source = (
                '<script data-page="app">'
                '{"props":{"auth":{"user":{"id":1}}}}'
                "</script>"
            )

        self.assertTrue(crawler.is_logged_in(Driver()))

    def test_create_driver_does_not_detect_or_override_chrome_version(self):
        with TemporaryDirectory() as temporary_directory:
            options = FakeChromeOptions()
            driver = FakeDriver()

            with (
                patch.object(
                    crawler,
                    "CHROME_PROFILE_DIR",
                    Path(temporary_directory) / "crawler-profile",
                ),
                patch.object(crawler.uc, "ChromeOptions", return_value=options),
                patch.object(crawler.uc, "Chrome", return_value=driver) as create_chrome,
            ):
                crawler.create_driver()

        self.assertFalse(hasattr(crawler, "detect_chrome_major_version"))
        self.assertNotIn("version_main", create_chrome.call_args.kwargs)

    def test_unauthenticated_error_does_not_reference_removed_cookie_config(self):
        page_data = {"component": "Error", "props": {"status": 403, "auth": {}}}

        with patch.object(crawler, "print_section"), patch.object(crawler, "print_step"), patch.object(crawler, "print_detail"):
            self.assertTrue(crawler.describe_inertia_error(page_data))


if __name__ == "__main__":
    unittest.main()
