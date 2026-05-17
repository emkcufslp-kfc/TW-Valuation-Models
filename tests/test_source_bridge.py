from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tw_valuation_models.config import WorkspacePaths
from tw_valuation_models.source_bridge import import_imfs_modules


class SourceBridgeTests(unittest.TestCase):
    def test_import_imfs_modules_raises_clear_error_when_root_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = WorkspacePaths(
                workspace_root=workspace,
                shared_data_root=workspace / "shared",
                source_model_root=workspace / "_external" / "tw_hybrid_model",
            )
            with self.assertRaises(FileNotFoundError) as ctx:
                import_imfs_modules(paths)
            self.assertIn("IMFS source root not found", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
