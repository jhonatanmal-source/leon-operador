"""Testes de resiliencia do caminho web -> rpyc -> MT5 (MISSION-20260825-WEB-RPYC-TIMEOUT).

Cobre os criterios de aceitacao da missao:
1. Lock serializa chamadas concorrentes ao cliente RPyC compartilhado
   (mt5linux_compat.py) — evita que multiplas threads waitress fiquem
   presas simultaneamente no mesmo socket quando o gateway MT5 trava.
2. Falha/timeout em uma chamada reseta o cliente (proxima chamada
   reconecta do zero, nunca reusa um socket em estado inconsistente).
3. Cache stale-while-revalidate (system_health_service.py): com cache
   expirado mas valor anterior disponivel, o caminho critico do render
   nunca fica bloqueado esperando o gateway lento — devolve o valor
   antigo na hora e atualiza em background.
4. Sem nenhum valor cacheado ainda (1a chamada do processo), o calculo
   e sincrono mas limitado pelo timeout do rpyc (nunca bloqueio infinito).

Nenhuma chamada MT5 real e feita — tudo mockado. Nenhuma ordem, sem
alteracao de estrategia/risco/TP/SL/execucao.
"""
import importlib
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture
def mt5linux_compat_module():
    """Importa mt5linux_compat com estado limpo (sem cliente cacheado)."""
    if "mt5linux_compat" in sys.modules:
        del sys.modules["mt5linux_compat"]
    module = importlib.import_module("mt5linux_compat")
    module._reset_client()
    yield module
    module._reset_client()
    if "mt5linux_compat" in sys.modules:
        del sys.modules["mt5linux_compat"]


class TestClienteRpycThreadSafety:
    """Fase A: lock serializa acesso ao cliente RPyC compartilhado."""

    def test_call_locked_usa_lock_de_thread(self, mt5linux_compat_module):
        """Confirma que _CLIENT_LOCK existe e e um Lock real (nao RLock)."""
        assert isinstance(
            mt5linux_compat_module._CLIENT_LOCK, type(threading.Lock())
        )

    def test_chamadas_concorrentes_sao_serializadas(
        self, mt5linux_compat_module, monkeypatch
    ):
        """Duas threads chamando funcoes MT5 ao mesmo tempo nunca executam
        dentro do cliente RPyC simultaneamente — o lock garante exclusao
        mutua mesmo sob chamadas lentas (simulando gateway lento).
        """
        concurrent_calls = {"count": 0, "max_concurrent": 0}
        lock = threading.Lock()

        class SlowFakeClient:
            def symbol_info_tick(self, *args, **kwargs):
                with lock:
                    concurrent_calls["count"] += 1
                    concurrent_calls["max_concurrent"] = max(
                        concurrent_calls["max_concurrent"],
                        concurrent_calls["count"],
                    )
                time.sleep(0.05)
                with lock:
                    concurrent_calls["count"] -= 1
                return "tick"

            def initialize(self, *args, **kwargs):
                return True

            def shutdown(self, *args, **kwargs):
                return True

        monkeypatch.setattr(
            mt5linux_compat_module,
            "_get_client",
            lambda: SlowFakeClient(),
        )

        threads = [
            threading.Thread(
                target=mt5linux_compat_module.symbol_info_tick, args=("XAUUSD",)
            )
            for _ in range(4)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)

        # Com o lock, no maximo 1 chamada executa dentro do cliente por vez.
        assert concurrent_calls["max_concurrent"] == 1

    def test_falha_em_chamada_reseta_cliente(
        self, mt5linux_compat_module, monkeypatch
    ):
        """Uma exececao (ex: timeout de sync_request) durante a chamada
        deve resetar o cliente global, forcando reconexao limpa na
        proxima chamada — nunca reusar socket travado/inconsistente.
        """

        class FailingClient:
            def symbol_info_tick(self, *args, **kwargs):
                raise TimeoutError("sync_request_timeout simulado")

        monkeypatch.setattr(
            mt5linux_compat_module, "_get_client", lambda: FailingClient()
        )
        mt5linux_compat_module._CLIENT = "cliente-anterior-marcado"

        with pytest.raises(TimeoutError):
            mt5linux_compat_module.symbol_info_tick("XAUUSD")

        assert mt5linux_compat_module._CLIENT is None

    def test_initialize_falha_graciosamente_sem_travar(
        self, mt5linux_compat_module, monkeypatch
    ):
        """initialize() nunca propaga exececao — retorna False em falha,
        permitindo que o caminho web degrade sem quebrar o render.
        """

        class FailingClient:
            def initialize(self, *args, **kwargs):
                raise TimeoutError("gateway travado")

        monkeypatch.setattr(
            mt5linux_compat_module, "_get_client", lambda: FailingClient()
        )

        result = mt5linux_compat_module.initialize()
        assert result is False
        assert mt5linux_compat_module._CLIENT is None

    def test_shutdown_falha_graciosamente_sem_travar(
        self, mt5linux_compat_module, monkeypatch
    ):
        """shutdown() nunca propaga exececao — retorna None em falha."""

        class FailingClient:
            def shutdown(self, *args, **kwargs):
                raise ConnectionError("conexao perdida")

        monkeypatch.setattr(
            mt5linux_compat_module, "_get_client", lambda: FailingClient()
        )

        result = mt5linux_compat_module.shutdown()
        assert result is None
        assert mt5linux_compat_module._CLIENT is None

    def test_chamada_bem_sucedida_nao_reseta_cliente(
        self, mt5linux_compat_module, monkeypatch
    ):
        """Chamada com sucesso preserva o cliente para reuso (evita
        reconectar a cada chamada quando o gateway esta saudavel).
        """
        fake_client = MagicMock()
        fake_client.account_info.return_value = {"balance": 10000}
        monkeypatch.setattr(
            mt5linux_compat_module, "_get_client", lambda: fake_client
        )
        mt5linux_compat_module._CLIENT = fake_client

        mt5linux_compat_module.account_info()

        assert mt5linux_compat_module._CLIENT is fake_client


class TestCacheStaleWhileRevalidate:
    """Fase B: cache MT5 no caminho web nunca bloqueia alem do 1o miss."""

    @pytest.fixture(autouse=True)
    def _isolar_modulo(self):
        for name in list(sys.modules):
            if name.startswith("web_app.services.system_health_service"):
                del sys.modules[name]
        yield
        for name in list(sys.modules):
            if name.startswith("web_app.services.system_health_service"):
                del sys.modules[name]

    def _importar_servico(self):
        return importlib.import_module(
            "web_app.services.system_health_service"
        )

    def test_cache_fresco_retorna_sem_computar(self):
        service = self._importar_servico()
        cache = {"result": "valor_cacheado", "timestamp": time.monotonic(), "refreshing": False}
        lock = threading.Lock()
        compute_calls = {"count": 0}

        def compute():
            compute_calls["count"] += 1
            return "valor_novo"

        result = service._stale_while_revalidate(cache, lock, ttl=30, compute_fn=compute)

        assert result == "valor_cacheado"
        assert compute_calls["count"] == 0

    def test_sem_cache_calcula_sincrono(self):
        service = self._importar_servico()
        cache = {"result": None, "timestamp": 0.0, "refreshing": False}
        lock = threading.Lock()

        def compute():
            return "primeiro_valor"

        result = service._stale_while_revalidate(cache, lock, ttl=30, compute_fn=compute)

        assert result == "primeiro_valor"
        assert cache["result"] == "primeiro_valor"

    def test_cache_expirado_devolve_valor_antigo_sem_bloquear(self):
        """Critério de aceitação #1/#2: com gateway lento, o render não
        pode esperar o timeout — deve devolver o valor stale na hora.
        """
        service = self._importar_servico()
        cache = {
            "result": "valor_antigo",
            "timestamp": time.monotonic() - 60,  # expirado (TTL=30)
            "refreshing": False,
        }
        lock = threading.Lock()
        compute_started = threading.Event()
        compute_finished = threading.Event()

        def compute_lento():
            compute_started.set()
            time.sleep(0.3)  # simula chamada MT5 lenta
            compute_finished.set()
            return "valor_atualizado"

        start = time.monotonic()
        result = service._stale_while_revalidate(
            cache, lock, ttl=30, compute_fn=compute_lento
        )
        elapsed = time.monotonic() - start

        # Devolve o valor antigo IMEDIATAMENTE, nao espera o compute lento.
        assert result == "valor_antigo"
        assert elapsed < 0.2

        # O refresh em background deve ter sido disparado e completar depois.
        assert compute_started.wait(timeout=1)
        assert compute_finished.wait(timeout=1)
        time.sleep(0.05)  # dar tempo do lock ser liberado pela thread
        assert cache["result"] == "valor_atualizado"

    def test_cache_expirado_nao_duplica_refresh_concorrente(self):
        """Multiplas threads batendo no cache expirado simultaneamente
        disparam apenas UM refresh em background, nao um por thread.
        """
        service = self._importar_servico()
        cache = {
            "result": "valor_antigo",
            "timestamp": time.monotonic() - 60,
            "refreshing": False,
        }
        lock = threading.Lock()
        compute_calls = {"count": 0}
        compute_lock = threading.Lock()

        def compute_lento():
            with compute_lock:
                compute_calls["count"] += 1
            time.sleep(0.2)
            return "valor_novo"

        threads = [
            threading.Thread(
                target=service._stale_while_revalidate,
                args=(cache, lock, 30, compute_lento),
            )
            for _ in range(5)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)
        time.sleep(0.3)

        assert compute_calls["count"] == 1

    def test_mt5_status_usa_cache_stale_while_revalidate(self, monkeypatch):
        """_mt5_status() real usa o helper — validacao de integracao."""
        service = self._importar_servico()

        service._mt5_cache["result"] = {"status": "OK", "connected": True}
        service._mt5_cache["timestamp"] = time.monotonic()
        service._mt5_cache["refreshing"] = False

        compute_called = {"value": False}

        def fake_compute():
            compute_called["value"] = True
            return {"status": "NOVO"}

        monkeypatch.setattr(service, "_compute_mt5_status", fake_compute)

        result = service._mt5_status()

        assert result == {"status": "OK", "connected": True}
        assert compute_called["value"] is False

    def test_get_mt5_account_summary_usa_cache_stale_while_revalidate(
        self, monkeypatch
    ):
        """get_mt5_account_summary() real usa o helper — validacao de
        integracao do context_processor do sidebar (caminho critico).
        """
        service = self._importar_servico()

        service._mt5_account_cache["result"] = {"account": "1234", "connected": True}
        service._mt5_account_cache["timestamp"] = time.monotonic()
        service._mt5_account_cache["refreshing"] = False

        compute_called = {"value": False}

        def fake_compute():
            compute_called["value"] = True
            return {"account": "NOVO"}

        monkeypatch.setattr(service, "_compute_mt5_account_summary", fake_compute)

        result = service.get_mt5_account_summary()

        assert result == {"account": "1234", "connected": True}
        assert compute_called["value"] is False

    def test_context_processor_nao_bloqueia_com_gateway_travado(self, monkeypatch):
        """Criterio de aceitacao #1: simula gateway travado (compute que
        demora mais que qualquer timeout razoavel) com cache stale
        presente — o context_processor (get_mt5_account_summary) deve
        responder quase instantaneamente.
        """
        service = self._importar_servico()

        service._mt5_account_cache["result"] = {"account": "SEM CONTA", "connected": False}
        service._mt5_account_cache["timestamp"] = time.monotonic() - 999
        service._mt5_account_cache["refreshing"] = False

        def compute_gateway_travado():
            time.sleep(5)  # gateway "travado" — muito mais que o timeout aceitavel
            return {"account": "NAO_DEVERIA_CHEGAR_AQUI"}

        monkeypatch.setattr(
            service, "_compute_mt5_account_summary", compute_gateway_travado
        )

        start = time.monotonic()
        result = service.get_mt5_account_summary()
        elapsed = time.monotonic() - start

        assert elapsed < 1.0, (
            f"context_processor bloqueou por {elapsed:.2f}s com gateway travado"
        )
        assert result == {"account": "SEM CONTA", "connected": False}


class TestHealthMt5StatusEndpoint:
    """Fase C: endpoint JSON /health/mt5-status para polling do widget.

    Fora do critical path de render — o sidebar exibe o valor do
    context_processor no 1o load e depois atualiza via fetch() neste
    endpoint (ver web_app/static/js/mt5_status_widget.js).
    """

    @pytest.fixture(autouse=True)
    def _isolar_modulos(self):
        for name in list(sys.modules):
            if name.startswith("web_app."):
                del sys.modules[name]
        yield
        for name in list(sys.modules):
            if name.startswith("web_app."):
                del sys.modules[name]

    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        from cryptography.fernet import Fernet

        db_path = tmp_path / "leon_web_test.db"
        master_key = tmp_path / "master_key"
        master_key.write_bytes(Fernet.generate_key())

        from web_app import config

        monkeypatch.setattr(config, "DATABASE_PATH", db_path)

        from web_app.database import db as db_module

        monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)
        monkeypatch.setattr(db_module, "DEFAULT_ADMIN_USERNAME", "admin_test")
        monkeypatch.setattr(
            db_module, "DEFAULT_ADMIN_PASSWORD", "senha-admin-teste-123"
        )

        from web_app.services import access_log_service

        monkeypatch.setattr(
            access_log_service, "LOG_FILE", tmp_path / "web_access.log"
        )

        from web_app.app import create_app

        app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
        test_client = app.test_client()

        from web_app.database.db import get_connection

        with app.app_context():
            with get_connection() as connection:
                row = connection.execute(
                    "SELECT id FROM users WHERE username = ?", ("admin_test",)
                ).fetchone()
            admin_id = row["id"]

        with test_client.session_transaction() as session:
            session["user_id"] = admin_id

        return test_client

    def test_endpoint_requer_login(self, tmp_path, monkeypatch):
        from cryptography.fernet import Fernet

        db_path = tmp_path / "leon_web_test.db"
        master_key = tmp_path / "master_key"
        master_key.write_bytes(Fernet.generate_key())

        from web_app import config

        monkeypatch.setattr(config, "DATABASE_PATH", db_path)

        from web_app.database import db as db_module

        monkeypatch.setattr(db_module, "DATABASE_PATH", db_path)

        from web_app.services import access_log_service

        monkeypatch.setattr(
            access_log_service, "LOG_FILE", tmp_path / "web_access.log"
        )

        from web_app.app import create_app

        app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
        response = app.test_client().get("/health/mt5-status", follow_redirects=False)

        assert response.status_code == 302
        assert "/login" in response.headers["Location"]

    def test_endpoint_retorna_json_com_login(self, client, monkeypatch):
        # A rota importa o nome diretamente (`from ... import
        # get_mt5_account_summary`), entao o patch precisa ser no modulo
        # da rota (onde o nome esta vinculado), nao no modulo de origem.
        from web_app.routes import health_routes

        monkeypatch.setattr(
            health_routes,
            "get_mt5_account_summary",
            lambda: {
                "account": "****5678",
                "server": "Broker-Demo",
                "type": "DEMO",
                "status": "OK",
                "connected": True,
            },
        )

        response = client.get("/health/mt5-status")

        assert response.status_code == 200
        assert response.content_type.startswith("application/json")
        payload = response.get_json()
        assert payload["connected"] is True
        assert payload["account"] == "****5678"

    def test_endpoint_nunca_expoe_senha_ou_dados_sensiveis(self, client, monkeypatch):
        """Somente leitura — login mascarado, sem senha/credencial no payload."""
        from web_app.routes import health_routes

        monkeypatch.setattr(
            health_routes,
            "get_mt5_account_summary",
            lambda: {
                "account": "****5678",
                "server": "Broker-Demo",
                "type": "DEMO",
                "status": "OK",
                "connected": True,
            },
        )

        response = client.get("/health/mt5-status")
        payload = response.get_json()

        assert "password" not in payload
        assert "senha" not in payload
        for value in payload.values():
            assert "senha123" not in str(value)

    def test_endpoint_degrada_com_gateway_indisponivel(self, client, monkeypatch):
        """Com MT5 indisponivel, o fallback de config ainda responde 200
        (nunca 500) — o widget deve mostrar estado neutro, nao quebrar.
        """
        from web_app.routes import health_routes

        monkeypatch.setattr(
            health_routes,
            "get_mt5_account_summary",
            lambda: {
                "account": "SEM CONTA",
                "server": "SEM DADOS",
                "type": "SEM DADOS",
                "connected": False,
            },
        )

        response = client.get("/health/mt5-status")

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["connected"] is False
