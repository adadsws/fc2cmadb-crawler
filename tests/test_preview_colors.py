"""验证命令行预览只对原值和目标值的差异着色。"""

import unittest
import re
from io import StringIO

from tools._shared.preview_colors import format_changed_pair, supports_color


class PreviewColorsTests(unittest.TestCase):
    @staticmethod
    def highlighted_text(value: str) -> str:
        return "".join(re.findall(r"\x1b\[97;4[12]m(.*?)\x1b\[0m", value))

    @staticmethod
    def plain_text(value: str) -> str:
        return re.sub(r"\x1b\[[0-9;]+m", "", value)

    def test_replaced_domain_highlights_only_changed_text(self):
        source, target = format_changed_pair(
            "https://fc2example.com/watch/1",
            "https://fc2cmadb.com/watch/1",
            color=True,
        )
        self.assertEqual(self.plain_text(source), "https://fc2example.com/watch/1")
        self.assertEqual(self.plain_text(target), "https://fc2cmadb.com/watch/1")
        self.assertEqual(self.highlighted_text(source), "exaple")
        self.assertEqual(self.highlighted_text(target), "cadb")

    def test_separated_changes_keep_middle_text_uncolored(self):
        source, target = format_changed_pair(
            "A-old-middle-old-Z", "A-new-middle-new-Z", color=True
        )
        self.assertEqual(source, "A-\x1b[97;41mold\x1b[0m-middle-\x1b[97;41mold\x1b[0m-Z")
        self.assertEqual(target, "A-\x1b[97;42mnew\x1b[0m-middle-\x1b[97;42mnew\x1b[0m-Z")

    def test_unicode_rename_keeps_shared_middle(self):
        old = "制作人甲-中间文字-旧标题"
        new = "制作人乙-中间文字-新标题"
        source, target = format_changed_pair(old, new, color=True)
        self.assertEqual((self.plain_text(source), self.plain_text(target)), (old, new))
        self.assertEqual(self.highlighted_text(source), "甲旧")
        self.assertEqual(self.highlighted_text(target), "乙新")

    def test_emoji_remains_an_intact_highlighted_character(self):
        source, target = format_changed_pair("A😀Z", "A😃Z", color=True)
        self.assertEqual(source, "A\x1b[97;41m😀\x1b[0mZ")
        self.assertEqual(target, "A\x1b[97;42m😃\x1b[0mZ")

    def test_inserted_destination_text_has_no_source_highlight(self):
        source, target = format_changed_pair("movie.mp4", "movie [023Mbps_2048p].mp4", color=True)
        self.assertEqual(source, "movie.mp4")
        self.assertEqual(target, "movie\x1b[97;42m [023Mbps_2048p]\x1b[0m.mp4")

    def test_redirected_output_remains_plain_text(self):
        self.assertFalse(supports_color(StringIO()))
        self.assertEqual(format_changed_pair("old", "new", color=False), ("old", "new"))


if __name__ == "__main__":
    unittest.main()
