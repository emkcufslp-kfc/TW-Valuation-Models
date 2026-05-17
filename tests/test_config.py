from __future__ import annotations

import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


class ConfigTests(unittest.TestCase):
    def test_env_overrides_default_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            shared = Path(tmp) / "shared"
            source = Path(tmp) / "source"
            env = {
                "TVM_WORKSPACE_ROOT": str(workspace),
                "TVM_SHARED_DATA_ROOT": str(shared),
                "TVM_SOURCE_MODEL_ROOT": str(source),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                import tw_valuation_models.config as config

                importlib.reload(config)
                self.assertEqual(config.DEFAULT_WORKSPACE_ROOT, workspace)
                self.assertEqual(config.DEFAULT_SHARED_DATA_ROOT, shared)
                self.assertEqual(config.DEFAULT_SOURCE_MODEL_ROOT, source)

    def test_external_model_roots_default_under_workspace(self) -> None:
        import tw_valuation_models.config as config

        workspace = Path(tempfile.gettempdir()) / "tvm-workspace"
        paths = config.WorkspacePaths(
            workspace_root=workspace,
            shared_data_root=workspace / "shared",
            source_model_root=workspace / "_external" / "tw_hybrid_model",
        )
        self.assertEqual(paths.imfs_source_root, workspace / "_external" / "imfs_tw_stock")
        self.assertEqual(paths.quant_source_root, workspace / "_external" / "tw_buffett_quant")
        self.assertEqual(paths.hybrid_source_root, workspace / "_external" / "tw_hybrid_model")


if __name__ == "__main__":
    unittest.main()
