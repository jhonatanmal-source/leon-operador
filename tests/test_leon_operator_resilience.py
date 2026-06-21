import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

import leon_operator


class LeonOperatorResilienceTests(unittest.TestCase):

    def test_invalid_operator_config_uses_safe_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config.ini"
            config_file.write_text(
                "\n".join(
                    [
                        "[OPERATOR]",
                        "collector_interval_minutes=invalid",
                        "analysis_interval_minutes=0",
                        "daily_learning_time=99:99",
                        "poll_seconds=-1",
                        "telegram_status_interval_minutes=invalid",
                        "demo_execution_interval_minutes=0",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.object(
                leon_operator,
                "CONFIG_FILE",
                config_file,
            ), patch.object(leon_operator, "registrar_erro"):
                config = leon_operator._carregar_operador_config()

        self.assertEqual(config["collector_interval_minutes"], 15)
        self.assertEqual(config["analysis_interval_minutes"], 15)
        self.assertEqual(config["daily_learning_time"], "23:55")
        self.assertEqual(config["poll_seconds"], 60)
        self.assertEqual(config["telegram_status_interval_minutes"], 720)
        self.assertEqual(config["demo_execution_interval_minutes"], 15)

    def test_failed_telegram_send_does_not_delay_retry(self):
        with patch.object(
            leon_operator,
            "enviar_status_operadores",
            return_value={"ok": False, "error": "NETWORK"},
        ), patch.object(
            leon_operator,
            "_salvar_status_telegram",
        ) as save_status, patch.object(
            leon_operator,
            "registrar_erro",
        ), patch.object(leon_operator, "registrar_log"):
            result = leon_operator.executar_status_telegram(forcar=True)

        self.assertFalse(result["ok"])
        save_status.assert_not_called()

    def test_successful_telegram_send_saves_timestamp(self):
        with patch.object(
            leon_operator,
            "enviar_status_operadores",
            return_value={"ok": True},
        ), patch.object(
            leon_operator,
            "_salvar_status_telegram",
        ) as save_status, patch.object(leon_operator, "registrar_log"):
            result = leon_operator.executar_status_telegram(forcar=True)

        self.assertTrue(result["ok"])
        save_status.assert_called_once()
        self.assertIsInstance(save_status.call_args.args[0], datetime)

    def test_task_exception_is_isolated(self):
        def failing_task():
            raise RuntimeError("falha simulada")

        with patch.object(leon_operator, "registrar_erro"), patch.object(
            leon_operator,
            "_enviar_erro_seguro",
        ):
            result = leon_operator._executar_tarefa_segura(
                "teste",
                failing_task,
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "OPERATOR_TASK_EXCEPTION")
        self.assertEqual(result["task"], "teste")

    def test_high_spread_respects_demo_retry_interval(self):
        with patch.object(
            leon_operator,
            "_carregar_operador_config",
            return_value={"demo_execution_interval_minutes": 5},
        ), patch.object(
            leon_operator,
            "executar_ordem_mt5_pre_operacao",
            return_value={"ok": False, "error": "SPREAD_ABOVE_LIMIT"},
        ), patch.object(
            leon_operator,
            "_salvar_execucao_demo",
        ) as save_execution, patch.object(
            leon_operator,
            "register_emotional_event",
        ), patch.object(leon_operator, "registrar_log"):
            result = leon_operator.executar_ordem_demo_programada(forcar=True)

        self.assertEqual(result["error"], "SPREAD_ABOVE_LIMIT")
        save_execution.assert_called_once()

    def test_atomic_state_write_replaces_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = Path(temp_dir) / "state.txt"
            leon_operator._escrever_texto_atomico(state_file, "novo")

            self.assertEqual(state_file.read_text(encoding="utf-8"), "novo")
            self.assertEqual(list(Path(temp_dir).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
