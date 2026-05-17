from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEPS_ROOT = WORKSPACE_ROOT / ".deps"
if str(DEPS_ROOT) not in sys.path:
    sys.path.insert(0, str(DEPS_ROOT))

from tw_valuation_models.config import WorkspacePaths
from tw_valuation_models.portfolio_builder import (
    _load_optional_external_modules,
    _unavailable_hybrid_result,
    _unavailable_imfs_result,
    _unavailable_quant_result,
)


class PortfolioBuilderFallbackTests(unittest.TestCase):
    def test_load_optional_external_modules_records_unavailable_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            paths = WorkspacePaths(
                workspace_root=workspace,
                shared_data_root=workspace / "shared",
                source_model_root=workspace / "_external" / "tw_hybrid_model",
            )
            with mock.patch("tw_valuation_models.portfolio_builder.import_imfs_modules", side_effect=FileNotFoundError("imfs missing")), mock.patch(
                "tw_valuation_models.portfolio_builder.import_tw_buffett_quant_modules",
                side_effect=FileNotFoundError("quant missing"),
            ), mock.patch(
                "tw_valuation_models.portfolio_builder.import_tw_hybrid_modules",
                side_effect=FileNotFoundError("hybrid missing"),
            ):
                imfs_modules, quant_modules, hybrid_modules, availability = _load_optional_external_modules(paths)
            self.assertIsNone(imfs_modules)
            self.assertIsNone(quant_modules)
            self.assertIsNone(hybrid_modules)
            self.assertIn("imfs missing", availability["imfs"])
            self.assertIn("quant missing", availability["tw_buffett_quant"])
            self.assertIn("hybrid missing", availability["tw_hybrid"])

    def test_unavailable_results_return_stable_shapes(self) -> None:
        imfs = _unavailable_imfs_result("imfs missing")
        quant = _unavailable_quant_result("quant missing")
        hybrid = _unavailable_hybrid_result("hybrid missing")
        self.assertEqual(imfs["signal"], "unavailable")
        self.assertEqual(quant["action_plan"], "unavailable")
        self.assertEqual(hybrid["signal"], "unavailable")
        self.assertIsNone(imfs["intrinsic_value"])
        self.assertIsNone(quant["composite_score"])
        self.assertIsNone(hybrid["ens_price"])


if __name__ == "__main__":
    unittest.main()
