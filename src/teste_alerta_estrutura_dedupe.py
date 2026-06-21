import tempfile
from pathlib import Path
from unittest.mock import patch

import telegram_alert


def executar_teste():

    evento = {
        "time": "2026-06-18T11:15:00",
        "level": 4250.0,
        "close": 4240.0,
    }

    with tempfile.TemporaryDirectory() as diretorio:
        estado = Path(diretorio) / "structure_alert_state.json"

        with (
            patch.object(telegram_alert, "STRUCTURE_ALERT_STATE_FILE", estado),
            patch.object(telegram_alert, "_enviar", return_value={"ok": True}),
        ):
            primeiro = telegram_alert.enviar_alerta_bos(
                "XAUUSD",
                "OPERACIONAL",
                "BOS_BEARISH",
                evento,
            )
            repetido = telegram_alert.enviar_alerta_bos(
                "XAUUSD",
                "OPERACIONAL",
                "BOS_BEARISH",
                evento,
            )
            novo = telegram_alert.enviar_alerta_bos(
                "XAUUSD",
                "OPERACIONAL",
                "BOS_BEARISH",
                {
                    **evento,
                    "time": "2026-06-18T11:30:00",
                    "close": 4235.0,
                },
            )

    assert primeiro["ok"] is True
    assert repetido["error"] == "TELEGRAM_STRUCTURE_EVENT_ALREADY_SENT"
    assert novo["ok"] is True
    print("OK: alertas estruturais repetidos foram bloqueados")


if __name__ == "__main__":
    executar_teste()
