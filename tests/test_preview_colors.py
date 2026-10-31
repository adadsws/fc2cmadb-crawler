"""验证命令行预览只对原值和目标值的差异着色。"""

import unittest
from io import StringIO

from tools.preview_colors import format_changed_pair, supports_color


class PreviewColorsTests(unittest.TestCase):
    def test_replaced_domain_highlights_only_changed_text(self):
        source, target = format_changed_pair(
            "https://fc2example.com/watch/1",
            "https://fc2cmadb.com/watch/1",
            color=True,
        )
        self.assertIn("https://fc2\x1b[97;41mexample\x1b[0m.com/watch/1", source)
        self.assertIn("https://fc2\x1b[97;42mcmadb\x1b[0m.com/watch/1", target)

    def test_inserted_destination_text_has_no_source_highlight(self):
        source, target = format_changed_pair("movie.mp4", "movie [023Mbps_2048p].mp4", color=True)
        self.assertEqual(source, "movie.mp4")
        self.assertEqual(target, "movie\x1b[97;42m [023Mbps_2048p]\x1b[0m.mp4")

    def test_redirected_output_remains_plain_text(self):
        self.assertFalse(supports_color(StringIO()))
        self.assertEqual(format_changed_pair("old", "new", color=False), ("old", "new"))


if __name__ == "__main__":
    unittest.main()
