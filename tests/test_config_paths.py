from pathlib import Path
import unittest

from fc2cmadb_crawler import config


class ConfigPathTests(unittest.TestCase):
    def test_generated_crawler_data_uses_outputs_directory(self):
        output_dir = Path(config.OUTPUT_DIR)

        self.assertEqual(output_dir.parent, config.PROJECT_ROOT)
        self.assertEqual(output_dir.name, "~outputs")

    def test_cookie_data_stays_under_secrets_directory(self):
        secrets_dir = Path(config.SECRETS_DIR)

        self.assertEqual(secrets_dir.parent, config.PROJECT_ROOT)
        self.assertEqual(secrets_dir.name, "secrets")


if __name__ == "__main__":
    unittest.main()
