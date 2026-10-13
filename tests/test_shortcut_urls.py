from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fc2cmadb_crawler import crawler


class ShortcutUrlTests(unittest.TestCase):
    def test_latest_shortcut_uses_explicit_first_page_url(self):
        build_url = getattr(crawler, "build_actress_page_url", lambda *_: "")

        self.assertEqual(
            build_url(10436),
            "https://fc2cmadb.com/actresses/10436?page=1",
        )

    def test_actress_shortcut_name_keeps_original_id_and_latest_number_format(self):
        self.assertEqual(
            crawler.build_actress_shortcut_name(10436, "1035965"),
            "id_10436 - latest_1035965",
        )

    def test_film_folders_do_not_contain_url_shortcuts(self):
        with TemporaryDirectory() as temporary_directory:
            actress_folder = Path(temporary_directory)
            crawler.create_film_folders(
                actress_folder,
                [
                    {
                        "film_number": "1035965",
                        "producer": "producer",
                        "film_title": "title",
                    }
                ],
            )

            film_folders = [path for path in actress_folder.iterdir() if path.is_dir()]
            self.assertEqual(len(film_folders), 1)
            self.assertEqual(list(film_folders[0].glob("*.url")), [])


if __name__ == "__main__":
    unittest.main()
