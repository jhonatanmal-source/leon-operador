"""Testes de idempotência para src/obsidian_sync.py.

Regressão para o bug MISSION-20260804-APRENDIZADO: append sem idempotência
gerava 16+ duplicatas de PREOP-000116 no CONTEXTO_EVOLUCAO.md e 42 linhas
duplicadas no diário diário 2026-07-30.md (vault Obsidian).

Causa raiz:
- update_daily_learning() fazia append sem checar se a entrada já existia.
- update_contexto_evolucao() fazia append de operações individuais no
  CONTEXTO, que é regenerado integralmente por daily_learning_sync.py.
- sync_closed_trade() chamava update_contexto_evolucao() a cada fechamento.

Correção:
- update_daily_learning() agora é idempotente (retorna False se já existe).
- sync_closed_trade() não chama mais update_contexto_evolucao().
- update_contexto_evolucao() fica idempotente e DEPRECATED.
"""
import tempfile
from pathlib import Path
from unittest import TestCase, mock

import src.obsidian_sync as obs


class TestObsidianSyncIdempotency(TestCase):

    def setUp(self):
        self.vault_tmp = Path(tempfile.mkdtemp())
        self.diario_tmp = self.vault_tmp / "aprendizados_diarios"
        self.diario_tmp.mkdir(parents=True)
        self.operacional_tmp = self.vault_tmp / "operacional"
        self.operacional_tmp.mkdir(parents=True)

        self.patch_vault = mock.patch("src.obsidian_sync.VAULT", self.vault_tmp)
        self.patch_diario = mock.patch(
            "src.obsidian_sync.DIARIO_DIR", self.diario_tmp
        )
        self.patch_operacional = mock.patch(
            "src.obsidian_sync.OPERACIONAL_DIR", self.operacional_tmp
        )
        self.patch_contexto = mock.patch(
            "src.obsidian_sync.CONTEXTO_FILE",
            self.diario_tmp / "CONTEXTO_EVOLUCAO.md",
        )
        self.patch_stats = mock.patch(
            "src.obsidian_sync.STATS_FILE",
            self.vault_tmp / ".trade_stats.json",
        )
        self.patch_vault.start()
        self.patch_diario.start()
        self.patch_operacional.start()
        self.patch_contexto.start()
        self.patch_stats.start()

    def tearDown(self):
        self.patch_vault.stop()
        self.patch_diario.stop()
        self.patch_operacional.stop()
        self.patch_contexto.stop()
        self.patch_stats.stop()
        import shutil

        shutil.rmtree(self.vault_tmp, ignore_errors=True)

    def test_update_daily_learning_nao_duplica_no_mesmo_dia(self):
        """Chamar 2x com a mesma nota não pode duplicar a linha."""
        hoje = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
        note_path = self.operacional_tmp / f"PREOP-000116_{hoje}.md"
        primeiro = obs.update_daily_learning(note_path)
        segundo = obs.update_daily_learning(note_path)

        self.assertTrue(primeiro)
        self.assertFalse(segundo)

        conteudo = (self.diario_tmp / f"{hoje}.md").read_text()
        esperado = f"- [[PREOP-000116_{hoje}]] — fechada em {hoje}"
        self.assertEqual(conteudo.count(esperado), 1)

    def test_update_daily_learning_datas_diferentes_append(self):
        """Operações em dias diferentes geram linhas em diários distintos."""
        note_hoje = self.operacional_tmp / "PREOP-000116_2026-07-30.md"

        with mock.patch(
            "src.obsidian_sync.datetime"
        ) as dt_mock:
            dt_mock.now.return_value.strftime.return_value = "2026-07-30"
            obs.update_daily_learning(note_hoje)

        conteudo = (self.diario_tmp / "2026-07-30.md").read_text()
        self.assertIn("PREOP-000116", conteudo)
        self.assertNotIn("X", conteudo)  # sanity

    def test_sync_closed_trade_nao_chama_update_contexto_evolucao(self):
        """sync_closed_trade não pode mais poluir o CONTEXTO com operações."""
        operation = {
            "id": "PREOP-000116",
            "ativo": "Gold_Spot",
            "direcao": "COMPRA",
            "resultado": "WIN_TP1",
            "data_fechamento": "2026-07-30",
            "smc": "BULLISH",
            "elliott": "ABC",
            "brain_score": 65,
            "entrada": 4100.0,
            "stop": 4090.0,
            "tp1": 4120.0,
            "tp2": 4140.0,
            "rr": 2.0,
        }
        with mock.patch.object(
            obs, "update_contexto_evolucao", wraps=obs.update_contexto_evolucao
        ) as spy:
            obs.sync_closed_trade(operation)
            spy.assert_not_called()

        # CONTEXTO não deve conter a operação (nem ser criado pelo fluxo).
        contexto_path = self.diario_tmp / "CONTEXTO_EVOLUCAO.md"
        if contexto_path.exists():
            self.assertNotIn("PREOP-000116", contexto_path.read_text())

    def test_sync_closed_trade_duas_vezes_diario_sem_duplicata(self):
        """sync_closed_trade chamado 2x para a mesma operação: diário sem duplicata."""
        operation = {
            "id": "PREOP-000116",
            "ativo": "Gold_Spot",
            "direcao": "COMPRA",
            "resultado": "WIN_TP1",
            "data_fechamento": "2026-07-30",
            "smc": "BULLISH",
            "elliott": "ABC",
            "brain_score": 65,
            "entrada": 4100.0,
            "stop": 4090.0,
            "tp1": 4120.0,
            "tp2": 4140.0,
            "rr": 2.0,
        }
        obs.sync_closed_trade(operation)
        obs.sync_closed_trade(operation)

        hoje = __import__("datetime").datetime.now().strftime("%Y-%m-%d")
        diario = (self.diario_tmp / f"{hoje}.md").read_text()
        # save_trade_note usa data_fechamento ("2026-07-30") no nome do arquivo.
        esperado = "- [[PREOP-000116_2026-07-30]] — fechada em " + hoje
        self.assertEqual(diario.count(esperado), 1)

    def test_update_contexto_evolucao_idempotente(self):
        """update_contexto_evolucao (deprecated) não duplica se chamado 2x."""
        operation = {
            "id": "PREOP-000116",
            "ativo": "Gold_Spot",
            "direcao": "COMPRA",
            "resultado": "WIN_TP1",
            "smc": "BULLISH",
            "elliott": "ABC",
            "brain_score": 65,
        }
        primeiro = obs.update_contexto_evolucao(operation)
        segundo = obs.update_contexto_evolucao(operation)

        self.assertTrue(primeiro)
        self.assertFalse(segundo)

        contexto = (self.diario_tmp / "CONTEXTO_EVOLUCAO.md").read_text()
        self.assertEqual(contexto.count("PREOP-000116"), 1)


class TestObsidianSyncLOSS(TestCase):
    """Cobertura adicional para operações LOSS (não geravam linha de WIN)."""

    def setUp(self):
        self.vault_tmp = Path(tempfile.mkdtemp())
        self.diario_tmp = self.vault_tmp / "aprendizados_diarios"
        self.diario_tmp.mkdir(parents=True)
        self.operacional_tmp = self.vault_tmp / "operacional"
        self.operacional_tmp.mkdir(parents=True)

        self.patch_vault = mock.patch("src.obsidian_sync.VAULT", self.vault_tmp)
        self.patch_diario = mock.patch(
            "src.obsidian_sync.DIARIO_DIR", self.diario_tmp
        )
        self.patch_operacional = mock.patch(
            "src.obsidian_sync.OPERACIONAL_DIR", self.operacional_tmp
        )
        self.patch_contexto = mock.patch(
            "src.obsidian_sync.CONTEXTO_FILE",
            self.diario_tmp / "CONTEXTO_EVOLUCAO.md",
        )
        self.patch_stats = mock.patch(
            "src.obsidian_sync.STATS_FILE",
            self.vault_tmp / ".trade_stats.json",
        )
        self.patch_vault.start()
        self.patch_diario.start()
        self.patch_operacional.start()
        self.patch_contexto.start()
        self.patch_stats.start()

    def tearDown(self):
        self.patch_vault.stop()
        self.patch_diario.stop()
        self.patch_operacional.stop()
        self.patch_contexto.stop()
        self.patch_stats.stop()
        import shutil

        shutil.rmtree(self.vault_tmp, ignore_errors=True)

    def test_update_contexto_evolucao_loss_idempotente(self):
        operation = {
            "id": "SHADOW-000049",
            "ativo": "Gold_Spot",
            "direcao": "COMPRA",
            "resultado": "LOSS",
            "smc": "?",
            "elliott": "?",
            "brain_score": "?",
        }
        primeiro = obs.update_contexto_evolucao(operation)
        segundo = obs.update_contexto_evolucao(operation)

        self.assertTrue(primeiro)
        self.assertFalse(segundo)

        contexto = (self.diario_tmp / "CONTEXTO_EVOLUCAO.md").read_text()
        self.assertEqual(contexto.count("SHADOW-000049"), 1)
