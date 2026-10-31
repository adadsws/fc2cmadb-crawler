"""验证辅助工具入口与默认输出位置。"""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ToolsLayoutTests(unittest.TestCase):
    def test_letter_commands_keep_distinct_meanings_in_copy_menus(self):
        from tools import copy_nonvids as copier

        source = PROJECT_ROOT / "tools"
        with patch("builtins.input", return_value="B"):
            with self.assertRaises(copier.BackToMainMenu):
                copier.prompt_copy_destination(source, copier.default_copy_destination(source))
        with patch("builtins.input", return_value="Q"):
            with self.assertRaises(copier.QuitTool):
                copier.confirm_existing_destination(source)

    def test_letter_commands_keep_distinct_meanings_in_shortcut_confirmation(self):
        from tools import update_shortcut_domains as shortcuts

        with patch("builtins.input", return_value="B"):
            with self.assertRaises(shortcuts.BackToMainMenu):
                shortcuts.confirm_update()
        with patch("builtins.input", return_value="Q"):
            with self.assertRaises(shortcuts.QuitTool):
                shortcuts.confirm_update()

    def test_zero_no_longer_duplicates_letter_commands(self):
        from tools import copy_nonvids as copier
        from tools import update_shortcut_domains as shortcuts

        source = PROJECT_ROOT / "tools"
        with patch("builtins.input", side_effect=["0", "b"]) as read_input:
            with self.assertRaises(copier.BackToMainMenu):
                copier.prompt_copy_destination(source, copier.default_copy_destination(source))
        self.assertEqual(read_input.call_count, 2)

        with patch("builtins.input", side_effect=["0", "q"]) as read_input:
            with self.assertRaises(shortcuts.QuitTool):
                shortcuts.confirm_update()
        self.assertEqual(read_input.call_count, 2)

        with patch("builtins.input", side_effect=["0", "q"]) as read_input:
            self.assertIsNone(shortcuts.choose_target_domain())
        self.assertEqual(read_input.call_count, 2)

    def test_shortcut_numeric_menus_use_first_option_on_enter(self):
        from tools import update_shortcut_domains as shortcuts

        with patch("builtins.input", return_value=""):
            self.assertEqual(shortcuts.choose_target_domain(), "fc2cmadb.com")
            self.assertTrue(shortcuts.confirm_update())

    def test_sibling_copy_option_uses_source_name_without_modifying_source(self):
        from tools import copy_nonvids as copier

        source = PROJECT_ROOT / "tests" / "sample"
        with patch("builtins.input", return_value="1"):
            destination, mode = copier.prompt_copy_destination(source, copier.default_copy_destination(source))
        self.assertEqual(destination, source.parent / "sample_nonvids")
        self.assertEqual(mode, "1")

    def test_copy_choice_enter_uses_first_option(self):
        from tools import copy_nonvids as copier

        source = PROJECT_ROOT / "tests" / "sample"
        default = copier.default_copy_destination(source)
        with patch("builtins.input", return_value=""):
            destination, mode = copier.prompt_copy_destination(source, default)
        self.assertEqual(destination, source.parent / "sample_nonvids")
        self.assertEqual(mode, "1")

    def test_copy_second_choice_uses_project_output(self):
        from tools import copy_nonvids as copier

        source = PROJECT_ROOT / "tests" / "sample"
        default = copier.default_copy_destination(source)
        with patch("builtins.input", return_value="2"):
            destination, mode = copier.prompt_copy_destination(source, default)
        self.assertEqual(destination, default.resolve())
        self.assertEqual(mode, "2")

    def test_copy_refuses_target_inside_source(self):
        from tools import copy_nonvids as copier

        source = PROJECT_ROOT / "tools"
        result = copier.ScanResult(files_to_copy=[(source / "config.py", 1)], bytes_to_copy=1)
        with redirect_stdout(StringIO()):
            copied_files, _, errors = copier.copy_files(source, source, result)
        self.assertEqual(copied_files, 0)
        self.assertEqual(len(errors), 1)

    def test_copy_scan_excludes_video_but_keeps_images_and_other_files(self):
        from tools import copy_nonvids as copier

        source = PROJECT_ROOT / "sample"
        with patch.object(copier.os, "walk", return_value=[
            (str(source), [], ["clip.MP4", "cover.JPG", "notes.txt"])
        ]), patch.object(Path, "stat") as stat:
            stat.return_value.st_size = 10
            result = copier.scan_source(source)

        self.assertEqual([path.name for path, _ in result.files_to_copy], ["cover.JPG", "notes.txt"])
        self.assertEqual(result.excluded_files, 1)
        self.assertEqual(result.bytes_to_copy, 20)

    def test_copy_destination_choices_keep_default_in_outputs_and_explicit_target(self):
        from tools import copy_nonvids as copier

        source = PROJECT_ROOT / "tools"
        explicit_target = PROJECT_ROOT / "~outputs" / "chosen"
        scan_result = copier.ScanResult(files_to_copy=[(source / "config.py", 1)])
        for args, selected_target in (
            ([str(source)], None),
            ([str(source), str(explicit_target)], explicit_target),
        ):
            with self.subTest(args=args):
                with patch.object(copier, "scan_source", return_value=scan_result), \
                    patch.object(copier, "print_scan_summary"), \
                    patch.object(copier, "prompt_copy_destination", return_value=(PROJECT_ROOT / "~outputs" / "result", "1")) as destination_prompt, \
                    patch.object(copier, "confirm_existing_destination", return_value=True), \
                    patch.object(copier, "copy_files", return_value=(1, 1, [])), \
                    redirect_stdout(StringIO()):
                    self.assertEqual(copier.main(args), 0)
                self.assertEqual(
                    destination_prompt.call_args.args,
                    (source, PROJECT_ROOT / "~outputs" / "tools_nonvids", str(selected_target) if selected_target else None, None),
                )

    def test_root_only_has_the_main_batch_entrypoint(self):
        self.assertEqual(
            sorted(path.name for path in PROJECT_ROOT.glob("*.bat")),
            ["run_fc2cmadb_crawler.bat"],
        )

    def test_auxiliary_tools_are_importable_from_tools_package(self):
        for module in ("tools.copy_nonvids", "tools.update_shortcut_domains"):
            result = subprocess.run(
                [sys.executable, "-m", module, "one", "two", "three"],
                cwd=PROJECT_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn(f"python -m {module}", result.stdout)

    def test_auxiliary_batch_files_call_tools_modules_from_project_root(self):
        expected_modules = {
            "run_copy_nonvids.bat": "tools.copy_nonvids",
            "run_update_shortcut_domains.bat": "tools.update_shortcut_domains",
        }
        for filename, module in expected_modules.items():
            content = (PROJECT_ROOT / "tools" / filename).read_text(encoding="utf-8")
            self.assertIn('cd /d "%~dp0.."', content)
            self.assertIn(f"python -m {module}", content)
