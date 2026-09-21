"""Regression coverage for canonical, local CSV persistence paths."""

from contextlib import chdir
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import importlib
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class CanonicalDataPathTests(TestCase):
    def test_loggers_write_semicolon_csvs_to_the_configured_canonical_data_dir(self):
        cases = (
            ("src.price_logger", "registrar_preco", ("XAUUSD", 1.0, 1.1), "price_history.csv", 4),
            ("src.candle_logger", "registrar_candle", ("XAUUSD", 1.0, 1.2, 0.9, 1.1), "candle_history.csv", 6),
            ("src.signal_logger", "registrar_sinal", ("alta", "forte", 9, "comprar"), "signals.csv", 5),
            ("src.trade_plan_memory", "salvar_trade_plan", ("XAUUSD", "compra", "ok", "ok", 9, 0.8), "trade_plan_memory.csv", 7),
        )

        with TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            legacy_data_dir = temporary_root / "C:" / "XAU_ELITE_AI" / "data"
            legacy_data_dir.mkdir(parents=True)
            canonical_data_dir = temporary_root / "canonical_data"

            with chdir(temporary_root):
                for module_name, function_name, arguments, filename, field_count in cases:
                    module = importlib.import_module(module_name)
                    with patch.object(module, "DATA_DIR", canonical_data_dir, create=True):
                        getattr(module, function_name)(*arguments)

                    output = canonical_data_dir / filename
                    self.assertTrue(output.is_file(), module_name)
                    lines = output.read_text(encoding="utf-8").splitlines()
                    row = lines[-1].split(";")
                    self.assertEqual(field_count, len(row), module_name)
                    self.assertFalse((legacy_data_dir / filename).exists(), module_name)
