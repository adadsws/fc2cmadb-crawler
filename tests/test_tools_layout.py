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
    def test_copy_destination_choices_keep_default_in_outputs_and_explicit_target(self):
        from tools import copy_non_media_files as copier

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
                    patch.object(copier, "prompt_copy_destination", return_value=PROJECT_ROOT / "~outputs" / "result") as destination_prompt, \
                    patch.object(copier, "confirm_existing_destination", return_value=True), \
                    patch.object(copier, "copy_files", return_value=(1, 1, [])), \
                    redirect_stdout(StringIO()):
                    self.assertEqual(copier.main(args), 0)
                self.assertEqual(
                    destination_prompt.call_args.args,
                    (source, PROJECT_ROOT / "~outputs" / "tools_non_media_files", str(selected_target) if selected_target else None),
                )

    def test_root_only_has_the_main_batch_entrypoint(self):
        self.assertEqual(
            sorted(path.name for path in PROJECT_ROOT.glob("*.bat")),
            ["run_fc2cmadb_crawler.bat"],
        )

    def test_auxiliary_tools_are_importable_from_tools_package(self):
        for module in ("tools.copy_non_media_files", "tools.update_shortcut_domains"):
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
            "run_copy_non_media_files.bat": "tools.copy_non_media_files",
            "run_update_shortcut_domains.bat": "tools.update_shortcut_domains",
        }
        for filename, module in expected_modules.items():
            content = (PROJECT_ROOT / "tools" / filename).read_text(encoding="utf-8")
            self.assertIn('cd /d "%~dp0.."', content)
            self.assertIn(f"python -m {module}", content)
