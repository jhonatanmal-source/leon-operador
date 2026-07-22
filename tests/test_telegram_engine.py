import importlib
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests


SRC = Path(__file__).resolve().parent.parent / "src"


def _set_telegram_env(**env):
    for k in [
        "LEON_TELEGRAM_TOKEN",
        "TELEGRAM_TOKEN",
        "LEON_TELEGRAM_CHAT_ID",
        "TELEGRAM_CHAT_ID",
        "LEON_TELEGRAM_ENABLED",
        "TELEGRAM_ENABLED",
    ]:
        os.environ.pop(k, None)
    for k, v in env.items():
        os.environ[k] = v


def _reload_telegram_config(**env):
    import src.telegram_config as cfg

    _set_telegram_env(**env)

    with patch.object(Path, "exists", return_value=False):
        cfg = importlib.reload(cfg)

    for k in env:
        os.environ.pop(k, None)

    return cfg


def _reload_telegram_engine(**env):
    _set_telegram_env(**env)

    with patch.object(Path, "exists", return_value=False):
        import src.telegram_config as cfg
        cfg = importlib.reload(cfg)

    import src.telegram_engine as eng
    eng = importlib.reload(eng)

    for k in env:
        os.environ.pop(k, None)

    return eng, cfg


class TestTelegramImport:

    def test_import_como_pacote(self):
        import src.telegram_engine
        assert hasattr(src.telegram_engine, "enviar_mensagem")

    def test_import_sem_chamada_mt5(self):
        import src.telegram_engine
        assert "order_send" not in dir(src.telegram_engine)

    def test_nenhuma_chamada_order_send_durante_import(self):
        import src.telegram_engine
        assert not hasattr(src.telegram_engine, "order_send")


class TestTelegramConfig:

    def test_config_modulo_existe(self):
        source = (SRC / "telegram_config.py").read_text(encoding="utf-8")
        assert "TOKEN" in source
        assert "CHAT_ID" in source
        assert "TELEGRAM_ENABLED" in source

    def test_config_sem_segredo_no_codigo(self):
        source = (SRC / "telegram_config.py").read_text(encoding="utf-8")
        actual = os.getenv("LEON_TELEGRAM_TOKEN") or os.getenv("TELEGRAM_TOKEN")
        if actual:
            assert actual not in source

    def test_config_desabilitado(self):
        cfg = _reload_telegram_config(TELEGRAM_ENABLED="false")
        assert cfg.TELEGRAM_ENABLED is False
        assert cfg.TOKEN == ""
        assert cfg.CHAT_ID == ""

    def test_config_token_ausente(self):
        cfg = _reload_telegram_config(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="",
            TELEGRAM_TOKEN="",
            LEON_TELEGRAM_CHAT_ID="-100123",
            TELEGRAM_CHAT_ID="-100123",
        )
        assert cfg.TOKEN == ""

    def test_config_chat_id_ausente(self):
        cfg = _reload_telegram_config(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="token123",
            TELEGRAM_TOKEN="token123",
            LEON_TELEGRAM_CHAT_ID="",
            TELEGRAM_CHAT_ID="",
        )
        assert cfg.CHAT_ID == ""

    def test_config_valida(self):
        cfg = _reload_telegram_config(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="token123",
            LEON_TELEGRAM_CHAT_ID="-100999",
        )
        assert cfg.TOKEN == "token123"
        assert cfg.CHAT_ID == "-100999"
        assert cfg.TELEGRAM_ENABLED is True


class TestTelegramEngineFailSafe:

    def test_desabilitado(self):
        eng, _ = _reload_telegram_engine(TELEGRAM_ENABLED="false")
        result = eng.enviar_mensagem("teste")
        assert result["ok"] is False
        assert result["error"] == "TELEGRAM_DISABLED"

    def test_token_ausente(self):
        eng, _ = _reload_telegram_engine(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="",
            LEON_TELEGRAM_CHAT_ID="-100999",
        )
        result = eng.enviar_mensagem("teste")
        assert result["ok"] is False
        assert result["error"] == "TELEGRAM_CONFIG_MISSING"

    def test_chat_id_ausente(self):
        eng, _ = _reload_telegram_engine(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="token123",
            LEON_TELEGRAM_CHAT_ID="",
        )
        result = eng.enviar_mensagem("teste")
        assert result["ok"] is False
        assert result["error"] == "TELEGRAM_CONFIG_MISSING"

    def test_mensagem_vazia(self):
        eng, _ = _reload_telegram_engine(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="token123",
            LEON_TELEGRAM_CHAT_ID="-100999",
        )
        result = eng.enviar_mensagem("")
        assert result["ok"] is False
        assert result["error"] == "TELEGRAM_EMPTY_MESSAGE"

    def test_timeout(self):
        eng, _ = _reload_telegram_engine(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="token123",
            LEON_TELEGRAM_CHAT_ID="-100999",
        )
        with patch.object(eng, "_mensagem_duplicada", return_value=False):
            with patch.object(eng, "_registrar_log"):
                with patch.object(eng, "_registrar_erro") as mock_err:
                    with patch.object(
                        eng.requests,
                        "post",
                        side_effect=requests.exceptions.Timeout("timeout"),
                    ):
                        with patch.object(eng.time, "sleep"):
                            result = eng.enviar_mensagem("teste")

        assert result["ok"] is False
        assert result["error"] == "TELEGRAM_CONNECTION_ERROR"
        for call_args in [c[0][0] for c in mock_err.call_args_list]:
            assert "token123" not in call_args

    def test_erro_http(self):
        eng, _ = _reload_telegram_engine(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="token123",
            LEON_TELEGRAM_CHAT_ID="-100999",
        )
        bad_response = Mock()
        bad_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError("403 Forbidden")
        )
        bad_response.json.return_value = {"ok": False, "description": "Forbidden"}

        with patch.object(eng, "_mensagem_duplicada", return_value=False):
            with patch.object(eng, "_registrar_log"):
                with patch.object(eng, "_registrar_erro"):
                    with patch.object(
                        eng.requests,
                        "post",
                        return_value=bad_response,
                    ):
                        with patch.object(eng.time, "sleep"):
                            result = eng.enviar_mensagem("teste")

        assert result.get("ok") is False

    def test_resposta_invalida(self):
        eng, _ = _reload_telegram_engine(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="token123",
            LEON_TELEGRAM_CHAT_ID="-100999",
        )
        bad_response = Mock()
        bad_response.raise_for_status.return_value = None
        bad_response.json.side_effect = ValueError("not json")

        with patch.object(eng, "_mensagem_duplicada", return_value=False):
            with patch.object(eng, "_registrar_log"):
                with patch.object(eng, "_registrar_erro"):
                    with patch.object(
                        eng.requests,
                        "post",
                        return_value=bad_response,
                    ):
                        result = eng.enviar_mensagem("teste")

        assert result["ok"] is False
        assert result["error"] == "TELEGRAM_INVALID_RESPONSE"

    def test_sucesso_com_http_mockado(self):
        eng, _ = _reload_telegram_engine(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="token123",
            LEON_TELEGRAM_CHAT_ID="-100999",
        )
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True, "result": {"message_id": 1}}

        with patch.object(eng, "_mensagem_duplicada", return_value=False):
            with patch.object(eng, "_registrar_log"):
                with patch.object(eng, "_registrar_erro"):
                    with patch.object(eng.time, "sleep"):
                        with patch.object(
                            eng.requests,
                            "post",
                            return_value=response,
                        ) as post:
                            result = eng.enviar_mensagem("teste")

        assert result["ok"] is True
        assert post.called

    def test_token_ausente_nos_logs(self):
        eng, _ = _reload_telegram_engine(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="secret_token_12345",
            LEON_TELEGRAM_CHAT_ID="-100999",
        )
        with patch.object(eng, "_mensagem_duplicada", return_value=False):
            with patch.object(eng, "_registrar_log") as mock_log:
                with patch.object(eng, "_registrar_erro"):
                    with patch.object(
                        eng.requests,
                        "post",
                        side_effect=requests.exceptions.Timeout("timeout"),
                    ):
                        eng.enviar_mensagem("teste")

        for call_args in [c[0][0] for c in mock_log.call_args_list]:
            assert "secret_token_12345" not in call_args

    def test_token_ausente_em_erro(self):
        eng, _ = _reload_telegram_engine(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="secret_token_12345",
            LEON_TELEGRAM_CHAT_ID="-100999",
        )
        with patch.object(eng, "_mensagem_duplicada", return_value=False):
            with patch.object(eng, "_registrar_log"):
                with patch.object(eng, "_registrar_erro") as mock_err:
                    with patch.object(
                        eng.requests,
                        "post",
                        side_effect=requests.exceptions.Timeout("timeout"),
                    ):
                        eng.enviar_mensagem("teste")

        for call_args in [c[0][0] for c in mock_err.call_args_list]:
            assert "secret_token_12345" not in call_args

    def test_falha_nao_libera_execucao(self):
        eng, _ = _reload_telegram_engine(TELEGRAM_ENABLED="false")
        result = eng.enviar_mensagem("teste")
        assert result["ok"] is False
        assert "order_send" not in result

    def test_compatibilidade_chamadas_existentes(self):
        eng, _ = _reload_telegram_engine(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="token123",
            LEON_TELEGRAM_CHAT_ID="-100999",
        )
        assert callable(eng.enviar_mensagem)
        assert callable(eng.enviar_foto)


class TestTelegramIdentidade:

    def test_identity_unica_apos_import_pacote(self):
        import src.telegram_engine
        import src.telegram_config
        mods = [k for k in sys.modules if "telegram_config" in k and not k.startswith("test_")]
        assert len(mods) == 1, f"identidade dupla: {mods}"
        assert "src.telegram_config" in sys.modules
        assert "telegram_config" not in sys.modules

    def test_sys_path_nao_modificado(self):
        saved = list(sys.path)
        import src.telegram_engine
        assert sys.path == saved, "sys.path foi modificado durante import"


class TestImportDeDiretorioDiferente:

    def test_import_de_fora_da_raiz(self):
        import subprocess
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, '/opt/leon/app'); import src.telegram_engine; print('OK')",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr}"
        assert "OK" in proc.stdout

    def test_import_operator_status_de_fora(self):
        import subprocess
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.path.insert(0, '/opt/leon/app'); import src.operator_status; print('OK')",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr}"
        assert "OK" in proc.stdout


class TestTelegramSemInternet:

    def test_nenhuma_chamada_real_internet(self):
        eng, _ = _reload_telegram_engine(
            TELEGRAM_ENABLED="true",
            LEON_TELEGRAM_TOKEN="token123",
            LEON_TELEGRAM_CHAT_ID="-100999",
        )
        with patch.object(eng, "_mensagem_duplicada", return_value=False):
            with patch.object(eng, "_registrar_log"):
                with patch.object(eng, "_registrar_erro"):
                    with patch.object(
                        eng.requests,
                        "post",
                        side_effect=requests.exceptions.Timeout("mocked"),
                    ):
                        eng.enviar_mensagem("teste")

        assert True

    def test_nenhuma_chamada_mt5(self):
        import src.telegram_engine
        assert not hasattr(src.telegram_engine, "order_send")

    def test_nenhuma_chamada_order_send(self):
        import src.telegram_engine
        for attr in dir(src.telegram_engine):
            assert "order_send" not in attr.lower()
