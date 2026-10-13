from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from fc2cmadb_crawler import browser as browser_module
from fc2cmadb_crawler import crawler


class FakeDriver:
    def __init__(self):
        self.current_url = "about:blank"
        self.title = "FC2CmaDB"
        self.page_source = "<html>ready</html>"
        self.body_text = "ready"
        self.commands = []
        self.service = Mock()

    def execute_cdp_cmd(self, command, params):
        self.commands.append((command, params))
        if command == "Page.navigate":
            self.current_url = params["url"]
            return {"frameId": "test"}
        return {}

    def execute_script(self, script):
        if "document.body" in script:
            return self.body_text
        return "complete"

    def set_page_load_timeout(self, _timeout):
        return None


class PersistentBrowserProfileTests(unittest.TestCase):
    def test_normal_chrome_is_started_then_webdriver_attaches(self):
        fake_process = Mock()
        fake_driver = FakeDriver()
        with TemporaryDirectory() as temporary_directory, patch.object(
            browser_module, "find_existing_debug_port", return_value=None
        ), patch.object(
            browser_module, "find_chrome_executable", return_value=Path("chrome.exe")
        ), patch.object(
            browser_module, "reserve_debug_port", return_value=9229
        ), patch.object(
            browser_module.subprocess, "Popen", return_value=fake_process
        ) as popen, patch.object(browser_module, "wait_for_debugger"), patch.object(
            browser_module.webdriver, "Chrome", return_value=fake_driver
        ) as chrome:
            instance = browser_module.PersistentBrowser(Path(temporary_directory))

        command = popen.call_args.args[0]
        self.assertIn("--remote-debugging-port=9229", command)
        self.assertIn(f"--user-data-dir={Path(temporary_directory).resolve()}", command)
        self.assertNotIn("--enable-automation", command)
        self.assertEqual(chrome.call_args.kwargs["options"].debugger_address, "127.0.0.1:9229")
        self.assertEqual(chrome.call_args.kwargs["options"].page_load_strategy, "eager")
        self.assertIs(instance.driver, fake_driver)

    def test_existing_project_chrome_is_reused(self):
        fake_driver = FakeDriver()
        with TemporaryDirectory() as temporary_directory, patch.object(
            browser_module, "find_existing_debug_port", return_value=9330
        ), patch.object(browser_module.subprocess, "Popen") as popen, patch.object(
            browser_module, "wait_for_debugger"
        ), patch.object(browser_module.webdriver, "Chrome", return_value=fake_driver):
            instance = browser_module.PersistentBrowser(Path(temporary_directory))

        popen.assert_not_called()
        self.assertIsNone(instance.chrome_process)

    def test_navigation_uses_single_cdp_entrypoint_and_skips_same_url(self):
        instance = browser_module.PersistentBrowser.__new__(browser_module.PersistentBrowser)
        instance.driver = FakeDriver()
        instance._last_navigation_at = 0.0

        first = instance.navigate("https://fc2cmadb.com/actresses/10436?page=1")
        second = instance.navigate("https://fc2cmadb.com/actresses/10436?page=1")

        navigations = [item for item in instance.driver.commands if item[0] == "Page.navigate"]
        self.assertEqual(len(navigations), 1)
        self.assertEqual(first, "<html>ready</html>")
        self.assertEqual(second, "<html>ready</html>")

    def test_challenge_is_detected_from_body_when_title_looks_normal(self):
        driver = FakeDriver()
        driver.title = "FC2CmaDB"
        driver.page_source = "<main>正在验证您是否是真人。这可能需要几秒钟时间。</main>"
        driver.body_text = "正在验证您是否是真人。这可能需要几秒钟时间。"

        self.assertTrue(browser_module.is_challenge_page(driver))

    def test_embedded_turnstile_on_404_is_not_a_full_page_challenge(self):
        driver = FakeDriver()
        driver.title = "404: ページが見つかりません - FC2CMADB"
        driver.page_source = '<main>404</main><div class="cf-chl-widget"></div>'
        driver.body_text = "404: ページが見つかりません"

        self.assertFalse(browser_module.is_challenge_page(driver))

    def test_close_detaches_without_closing_project_chrome(self):
        instance = browser_module.PersistentBrowser.__new__(browser_module.PersistentBrowser)
        instance.driver = FakeDriver()

        instance.close()

        instance.driver.service.stop.assert_called_once_with()
        self.assertNotIn(("Browser.close", {}), instance.driver.commands)

    def test_is_logged_in_reads_inertia_auth_from_any_site_page(self):
        driver = FakeDriver()
        driver.page_source = (
            '<script data-page="app">'
            '{"props":{"auth":{"user":{"id":1}}}}'
            "</script>"
        )
        self.assertTrue(crawler.is_logged_in(driver))

    def test_prepare_session_reuses_current_logged_in_page_without_navigation(self):
        browser = Mock()
        browser.driver.current_url = "https://fc2cmadb.com/actresses/10436?page=2"
        with patch.object(crawler, "is_logged_in", return_value=True):
            self.assertTrue(crawler.prepare_authenticated_session(browser))

        browser.navigate.assert_not_called()

    def test_prepare_session_navigates_to_home_at_most_once(self):
        browser = Mock()
        browser.driver.current_url = "about:blank"
        with patch.object(crawler, "is_logged_in", return_value=True):
            self.assertTrue(crawler.prepare_authenticated_session(browser))

        browser.navigate.assert_called_once_with(crawler.SITE_BASE_URL)

    def test_unauthenticated_error_does_not_reference_removed_cookie_config(self):
        page_data = {"component": "Error", "props": {"status": 403, "auth": {}}}

        with patch.object(crawler, "print_section"), patch.object(
            crawler, "print_step"
        ), patch.object(crawler, "print_detail"):
            self.assertTrue(crawler.describe_inertia_error(page_data))


if __name__ == "__main__":
    unittest.main()
