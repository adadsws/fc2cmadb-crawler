"""撤销前若源状态变化，不覆盖目录或快捷方式。"""

import base64
import hashlib
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tools import update_fc2_folder_names as folders
from tools import update_shortcut_domains as shortcuts
from tools.undo_history import batch_folder_paths


class MultistepUndoTests(unittest.TestCase):
    def test_folder_undo_stops_when_original_name_is_occupied(self):
        record = {"entries": [{"source": "root/old", "target": "root/new"}]}
        with patch.object(folders, "read_batch", return_value=record), patch("builtins.input", return_value="1"), patch.object(
            Path, "is_dir", return_value=True
        ), patch.object(Path, "exists", return_value=True), patch.object(
            Path, "rename"
        ) as rename, patch.object(folders, "mark_undone") as mark:
            self.assertFalse(folders.undo_batch(Path("batch.json")))
        rename.assert_not_called()
        mark.assert_not_called()

    def test_shortcut_undo_stops_when_file_changed_again(self):
        record = {"entries": [{
            "path": "sample.url",
            "original_b64": base64.b64encode(b"original").decode("ascii"),
            "updated_sha256": hashlib.sha256(b"updated").hexdigest(),
            "old_domain": "fc2example.com",
            "new_domain": "fc2cmadb.com",
        }]}
        with patch.object(shortcuts, "read_batch", return_value=record), patch("builtins.input", return_value="1"), patch.object(
            Path, "read_bytes", return_value=b"external edit"
        ), patch.object(Path, "write_bytes") as write, patch.object(shortcuts, "mark_undone") as mark:
            self.assertFalse(shortcuts.undo_batch(Path("batch.json")))
        write.assert_not_called()
        mark.assert_not_called()

    def test_history_folder_label_supports_new_and_old_records(self):
        self.assertEqual(
            batch_folder_paths({"root_path": "chosen", "entries": [{"source": "older/a"}]}, "source"),
            ["chosen"],
        )
        self.assertEqual(
            batch_folder_paths({"entries": [{"source": "older/a"}, {"source": "older/b"}]}, "source"),
            ["older"],
        )

    def test_folder_menu_selects_batch_by_displayed_path(self):
        paths = [Path("newer.json"), Path("older.json")]
        records = {
            paths[0]: {"root_path": "newer folder", "entries": [{"source": "newer/a"}]},
            paths[1]: {"entries": [{"source": "older/a"}]},
        }
        with patch.object(folders, "pending_batches", return_value=paths), patch.object(
            folders, "read_batch", side_effect=lambda path: records[path]
        ), patch.object(folders, "undo_batch", return_value=True) as undo, patch(
            "builtins.input", side_effect=["2", "b"]
        ), redirect_stdout(StringIO()) as output:
            with self.assertRaises(folders.BackToMainMenu):
                folders.undo_menu()
        undo.assert_called_once_with(paths[1])
        self.assertIn("1. newer folder", output.getvalue())
        self.assertIn("2. older", output.getvalue())


if __name__ == "__main__":
    unittest.main()
