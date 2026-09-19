from pathlib import Path
import subprocess
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ToolsLayoutTests(unittest.TestCase):
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
