import unittest
from unittest.mock import Mock, patch

import requests

import src.telegram_engine as telegram_engine


class TelegramRetryTests(unittest.TestCase):

    def test_retries_transient_connection_failure(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}

        with patch.object(
            telegram_engine.requests,
            "post",
            side_effect=[
                requests.exceptions.Timeout("timeout"),
                response,
            ],
        ) as post, patch.object(
            telegram_engine,
            "_mensagem_duplicada",
            return_value=False,
        ), patch.object(
            telegram_engine,
            "_registrar_log",
        ), patch.object(
            telegram_engine.time,
            "sleep",
        ):
            result = telegram_engine.enviar_mensagem("teste")

        self.assertTrue(result["ok"])
        self.assertEqual(post.call_count, 2)


if __name__ == "__main__":
    unittest.main()
