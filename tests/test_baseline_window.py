"""Testes da base por janela de dias corridos.

Missão: MISSION-20260817-BASE-DIAS-CORRIDOS
Cobre: baseline_window, resumo_pre_operacao (janela + ultimo global),
_winrate_shadows_recentes (janela), shadow_evidence (janela) e o dedup
por operation_ids do operation_batch_review.
"""

import csv
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import src.baseline_window as baseline_window
import src.pre_operation_engine as pre_operation_engine
import src.learning_bootstrap as learning_bootstrap
import src.lab_entry_policy as lab_entry_policy
import src.operation_batch_review as operation_batch_review


class BaselineWindowHelperTests(unittest.TestCase):
    def test_obter_window_days_fallback_sem_secao(self):
        with TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.ini"
            config_file.write_text("[LEON]\nnome=LEON\n", encoding="utf-8")
            with patch.object(baseline_window, "CONFIG_FILE", config_file):
                self.assertEqual(baseline_window.obter_window_days(), 30)

    def test_obter_window_days_lido_da_secao(self):
        with TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.ini"
            config_file.write_text("[BASELINE]\nwindow_days=7\n", encoding="utf-8")
            with patch.object(baseline_window, "CONFIG_FILE", config_file):
                self.assertEqual(baseline_window.obter_window_days(), 7)

    def test_obter_window_days_valor_invalido_usa_fallback(self):
        with TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.ini"
            config_file.write_text("[BASELINE]\nwindow_days=abc\n", encoding="utf-8")
            with patch.object(baseline_window, "CONFIG_FILE", config_file):
                self.assertEqual(baseline_window.obter_window_days(), 30)

    def test_parse_datetime_com_T_e_espaco(self):
        self.assertIsNotNone(baseline_window.parse_datetime("2026-08-12T23:05:15"))
        self.assertIsNotNone(baseline_window.parse_datetime("2026-08-12 23:05:15.156821"))
        self.assertIsNone(baseline_window.parse_datetime(""))
        self.assertIsNone(baseline_window.parse_datetime("nao-e-data"))

    def test_dentro_da_janela_sem_filtro_sempre_true(self):
        self.assertTrue(baseline_window.dentro_da_janela("", None))
        self.assertTrue(baseline_window.dentro_da_janela("qualquer", 0))

    def test_dentro_da_janela_data_invalida_excluida(self):
        # Com filtro ativo, data invalida deve ser EXCLUIDA (False)
        self.assertFalse(baseline_window.dentro_da_janela("invalida", 30))
        self.assertFalse(baseline_window.dentro_da_janela("", 30))

    def test_parse_datetime_com_timezone_normaliza_para_naive(self):
        # Data com offset nao pode gerar TypeError na comparacao com now() naive
        resultado = baseline_window.parse_datetime("2026-08-17T10:00:00+00:00")
        self.assertIsNotNone(resultado)
        self.assertIsNone(resultado.tzinfo)
        resultado_z = baseline_window.parse_datetime("2026-08-17T10:00:00Z")
        if resultado_z is not None:
            self.assertIsNone(resultado_z.tzinfo)

    def test_dentro_da_janela_com_timezone_nao_levanta(self):
        agora = datetime(2026, 8, 17, 12, 0, 0)
        # Nao deve levantar TypeError (offset-aware vs offset-naive)
        self.assertTrue(
            baseline_window.dentro_da_janela("2026-08-17T10:00:00+00:00", 30, agora=agora)
        )
        self.assertFalse(
            baseline_window.dentro_da_janela("2026-06-01T10:00:00+00:00", 30, agora=agora)
        )

    def test_dentro_da_janela_limites(self):
        agora = datetime(2026, 8, 17, 12, 0, 0)
        dentro = (agora - timedelta(days=5)).isoformat()
        fora = (agora - timedelta(days=40)).isoformat()
        self.assertTrue(baseline_window.dentro_da_janela(dentro, 30, agora=agora))
        self.assertFalse(baseline_window.dentro_da_janela(fora, 30, agora=agora))


class ResumoPreOperacaoJanelaTests(unittest.TestCase):
    def _registros(self):
        hoje = datetime.now()
        recente = (hoje - timedelta(days=2)).isoformat(timespec="seconds")
        antigo = (hoje - timedelta(days=60)).isoformat(timespec="seconds")
        return [
            {"id": "P1", "data_fechamento": recente, "status": "FECHADO", "resultado": "WIN_TP1"},
            {"id": "P2", "data_fechamento": recente, "status": "FECHADO", "resultado": "LOSS"},
            {"id": "P3", "data_fechamento": antigo, "status": "FECHADO", "resultado": "WIN_TP2"},
            {"id": "P4", "data_fechamento": antigo, "status": "FECHADO", "resultado": "LOSS"},
            {"id": "P5", "data_fechamento": "", "status": "ABERTO", "resultado": "SEM_ENTRADA"},
        ]

    def test_sem_janela_conta_todos(self):
        with patch.object(pre_operation_engine, "_ler_registros", return_value=self._registros()):
            resumo = pre_operation_engine.resumo_pre_operacao()
        self.assertEqual(resumo["fechados"], 4)
        self.assertEqual(resumo["wins"], 2)
        self.assertEqual(resumo["losses"], 2)

    def test_com_janela_filtra_por_data_fechamento(self):
        with patch.object(pre_operation_engine, "_ler_registros", return_value=self._registros()):
            resumo = pre_operation_engine.resumo_pre_operacao(window_days=30)
        self.assertEqual(resumo["fechados"], 2)
        self.assertEqual(resumo["wins"], 1)
        self.assertEqual(resumo["losses"], 1)
        self.assertEqual(resumo["fechados_global"], 4)

    def test_ultimo_e_total_permanecem_globais(self):
        registros = self._registros()
        with patch.object(pre_operation_engine, "_ler_registros", return_value=registros):
            resumo = pre_operation_engine.resumo_pre_operacao(window_days=30)
        # total, abertos e ultimo NAO sao filtrados pela janela
        self.assertEqual(resumo["total"], 5)
        self.assertEqual(resumo["abertos"], 1)
        self.assertEqual(resumo["ultimo"]["id"], "P5")


class WinrateShadowsJanelaTests(unittest.TestCase):
    def _escrever_shadows(self, directory):
        hoje = datetime.now()
        recente = (hoje - timedelta(days=1)).isoformat(timespec="seconds")
        antigo = (hoje - timedelta(days=50)).isoformat(timespec="seconds")
        shadow_file = Path(directory) / "shadow_trades.csv"
        with shadow_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["id", "closed_at", "status", "result"])
            writer.writerow(["S1", recente, "FECHADO", "WIN_2R"])
            writer.writerow(["S2", recente, "FECHADO", "LOSS"])
            writer.writerow(["S3", antigo, "FECHADO", "LOSS"])
            writer.writerow(["S4", antigo, "FECHADO", "LOSS"])
        return shadow_file

    def test_janela_reduz_shadows_consideradas(self):
        with TemporaryDirectory() as directory:
            self._escrever_shadows(directory)
            with patch.object(learning_bootstrap, "DATA_DIR", Path(directory)):
                sem = learning_bootstrap._winrate_shadows_recentes()
                com = learning_bootstrap._winrate_shadows_recentes(window_days=30)
        self.assertEqual(sem["fechados"], 4)
        self.assertEqual(com["fechados"], 2)
        self.assertEqual(com["wins"], 1)
        self.assertEqual(com["losses"], 1)
        self.assertEqual(com["winrate"], 50.0)


class ShadowEvidenceJanelaTests(unittest.TestCase):
    def test_janela_filtra_por_closed_at(self):
        hoje = datetime.now()
        recente = (hoje - timedelta(days=1)).isoformat(timespec="seconds")
        antigo = (hoje - timedelta(days=45)).isoformat(timespec="seconds")
        rows = [
            {"status": "FECHADO", "result": "WIN_2R", "closed_at": recente,
             "missing_confirmations": "FIBONACCI_ONDA_2_OU_4,CAPTURA_LIQUIDEZ"},
            {"status": "FECHADO", "result": "LOSS", "closed_at": antigo,
             "missing_confirmations": "FIBONACCI_ONDA_2_OU_4,CAPTURA_LIQUIDEZ"},
        ]
        sem = lab_entry_policy.shadow_evidence(rows=rows)
        com = lab_entry_policy.shadow_evidence(rows=rows, window_days=30)
        self.assertEqual(sem["closed"], 2)
        self.assertEqual(com["closed"], 1)
        self.assertEqual(com["wins"], 1)


class BatchReviewSeedMigrationTests(unittest.TestCase):
    def test_seed_le_operation_ids_e_ultimo_bloco_dos_relatorios(self):
        import json

        with TemporaryDirectory() as directory:
            reports_dir = Path(directory) / "operation_batches"
            reports_dir.mkdir(parents=True, exist_ok=True)
            (reports_dir / "bloco_001.json").write_text(
                json.dumps({"batch": 1, "operation_ids": ["A1", "A2"]}),
                encoding="utf-8",
            )
            (reports_dir / "bloco_002.json").write_text(
                # A2 duplicado entre blocos (duplicidade historica do formato antigo)
                json.dumps({"batch": 2, "operation_ids": ["A2", "A3"]}),
                encoding="utf-8",
            )
            with patch.object(operation_batch_review, "REPORTS_DIR", reports_dir):
                ids, last_batch = operation_batch_review._seed_from_existing_reports()

        self.assertEqual(ids, {"A1", "A2", "A3"})
        self.assertEqual(last_batch, 2)

    def test_state_antigo_migra_sem_reprocessar_historico(self):
        import json

        with TemporaryDirectory() as directory:
            reports_dir = Path(directory) / "operation_batches"
            reports_dir.mkdir(parents=True, exist_ok=True)
            (reports_dir / "bloco_001.json").write_text(
                json.dumps({"batch": 1, "operation_ids": ["H1", "H2"]}),
                encoding="utf-8",
            )
            state_file = Path(directory) / "state.json"
            # Formato ANTIGO: indexado por numero de bloco
            state_file.write_text(
                json.dumps({"processed_batches": [1], "closed_operations": 2}),
                encoding="utf-8",
            )
            with patch.object(operation_batch_review, "REPORTS_DIR", reports_dir), \
                 patch.object(operation_batch_review, "STATE_FILE", state_file):
                _, processed_ids, last_batch = operation_batch_review._load_review_state()

        self.assertEqual(processed_ids, {"H1", "H2"})
        self.assertEqual(last_batch, 1)


class BatchReviewDedupTests(unittest.TestCase):
    def test_dedup_por_operation_ids_nao_reprocessa(self):
        hoje = datetime.now()
        with TemporaryDirectory() as directory:
            reports_dir = Path(directory) / "reports"
            state_file = Path(directory) / "state.json"
            rec_file = Path(directory) / "rec.json"
            operations = [
                {
                    "id": f"OP{i:03d}",
                    "resultado": "WIN_TP1" if i % 2 else "LOSS",
                    "data_fechamento": (hoje - timedelta(days=1)).isoformat(timespec="seconds"),
                    "entrada": "100", "stop": "95", "tp1": "110", "tp2": "115",
                    "rr": "2", "context": {},
                }
                for i in range(20)
            ]
            with patch.object(operation_batch_review, "REPORTS_DIR", reports_dir), \
                 patch.object(operation_batch_review, "STATE_FILE", state_file), \
                 patch.object(operation_batch_review, "RECOMMENDATIONS_FILE", rec_file), \
                 patch.object(operation_batch_review, "_closed_operations", return_value=operations):
                primeira = operation_batch_review.process_operation_batches(window_days=30)
                segunda = operation_batch_review.process_operation_batches(window_days=30)

        self.assertEqual(len(primeira["generated"]), 1)
        self.assertEqual(len(segunda["generated"]), 0)
        self.assertEqual(len(primeira["state"]["processed_operation_ids"]), 20)


if __name__ == "__main__":
    unittest.main()
