import tempfile
from pathlib import Path
from unittest import TestCase, mock

import src.daily_learning_sync as dls


class TestDailyLearningSync(TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.patch_diarios = mock.patch(
            "src.daily_learning_sync.DIARIOS", self.tmp
        )
        self.patch_contexto = mock.patch(
            "src.daily_learning_sync.CONTEXTO_FILE",
            self.tmp / "CONTEXTO_EVOLUCAO.md",
        )
        self.patch_indice = mock.patch(
            "src.daily_learning_sync.INDICE_FILE",
            self.tmp / "INDICE.md",
        )
        self.patch_diarios.start()
        self.patch_contexto.start()
        self.patch_indice.start()

    def tearDown(self):
        self.patch_diarios.stop()
        self.patch_contexto.stop()
        self.patch_indice.stop()
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _contexto_path(self):
        return self.tmp / "CONTEXTO_EVOLUCAO.md"

    def _indice_path(self):
        return self.tmp / "INDICE.md"

    def _criar_aprendizado(self, data: str, secoes: dict[str, list[str]]):
        path = self.tmp / f"{data}.md"
        linhas = [f"# Aprendizado Diário — {data}", ""]
        for secao, itens in secoes.items():
            linhas.append(f"## {secao}")
            for item in itens:
                linhas.append(f"- {item}")
            linhas.append("")
        path.write_text("\n".join(linhas), encoding="utf-8")
        return path

    def test_extrair_secao_encontra_itens(self):
        texto = (
            "## Erros Encontrados\n"
            "- Erro 1\n"
            "- Erro 2\n"
            "## Outra Seção\n"
        )
        resultado = dls._extrair_secao(texto, "Erros Encontrados")
        self.assertEqual(resultado, ["Erro 1", "Erro 2"])

    def test_extrair_secao_sem_itens(self):
        texto = "## Erros Encontrados\n## Outra Seção\n"
        resultado = dls._extrair_secao(texto, "Erros Encontrados")
        self.assertEqual(resultado, [])

    def test_extrair_secao_inexistente(self):
        texto = "## Outra Coisa\n"
        resultado = dls._extrair_secao(texto, "Erros Encontrados")
        self.assertEqual(resultado, [])

    def test_identificar_padroes_recorrentes(self):
        consolidado = {
            "Padrões Identificados": [
                "Padrão A",
                "Padrão B",
                "Padrão A",
                "Padrão C",
                "Padrão B",
            ]
        }
        padroes = dls._identificar_padroes_recorrentes(consolidado)
        self.assertIn("Padrão A", padroes)
        self.assertIn("Padrão B", padroes)
        self.assertNotIn("Padrão C", padroes)

    def test_identificar_padroes_sem_recorrentes(self):
        consolidado = {
            "Padrões Identificados": ["Padrão A", "Padrão B"]
        }
        padroes = dls._identificar_padroes_recorrentes(consolidado)
        self.assertEqual(padroes, [])

    def test_sincronizacao_sem_arquivos(self):
        resultado = dls.executar_sincronizacao()
        self.assertIn("Dias registrados: 0", resultado)
        self.assertTrue(self._contexto_path().exists())
        contexto = self._contexto_path().read_text(encoding="utf-8")
        self.assertIn("Nenhum padrão registrado ainda", contexto)
        self.assertIn("Contratos Protegidos", contexto)

    def test_sincronizacao_com_um_dia(self):
        self._criar_aprendizado("2026-07-22", {
            "Decisões Tomadas": ["Decisão X"],
            "Erros Encontrados": ["Erro Y"],
            "Correções Aplicadas": ["Corrigiu Z"],
            "Padrões Identificados": ["Padrão P"],
        })
        resultado = dls.executar_sincronizacao()
        self.assertIn("Dias registrados: 1", resultado)
        self.assertTrue(self._contexto_path().exists())
        self.assertTrue(self._indice_path().exists())
        contexto = self._contexto_path().read_text(encoding="utf-8")
        self.assertIn("Decisão X", contexto)
        self.assertIn("Erro Y", contexto)
        self.assertIn("Corrigiu Z", contexto)

    def test_sincronizacao_com_padrao_recorrente(self):
        self._criar_aprendizado("2026-07-21", {
            "Padrões Identificados": ["Erro recorrente de path"]
        })
        self._criar_aprendizado("2026-07-22", {
            "Padrões Identificados": ["Erro recorrente de path"]
        })
        resultado = dls.executar_sincronizacao()
        self.assertIn("Dias registrados: 2", resultado)
        contexto = self._contexto_path().read_text(encoding="utf-8")
        self.assertIn("Erro recorrente de path", contexto)

    def test_indice_atualizado(self):
        self._criar_aprendizado("2026-07-22", {
            "Decisões Tomadas": ["Algo"]
        })
        dls.executar_sincronizacao()
        indice = self._indice_path().read_text(encoding="utf-8")
        self.assertIn("2026-07-22", indice)

    def test_idempotencia_sem_mudancas(self):
        self._criar_aprendizado("2026-07-22", {
            "Decisões Tomadas": ["Decisão Única"]
        })
        r1 = dls.executar_sincronizacao()
        r2 = dls.executar_sincronizacao()
        self.assertIn("atualizado", r1)
        self.assertIn("já sincronizado", r2)

    def test_multiplos_dias_e_secoes(self):
        self._criar_aprendizado("2026-07-21", {
            "Operações / Missões Executadas": ["Auditoria"],
            "Decisões Tomadas": ["Mudar estrutura"],
            "Erros Encontrados": ["Path errado"],
            "Correções Aplicadas": ["Path corrigido"],
            "Padrões Identificados": ["Sempre verificar path"],
            "Recomendações para Agentes": ["Usar Path.resolve()"],
        })
        self._criar_aprendizado("2026-07-22", {
            "Operações / Missões Executadas": ["Correção de bug"],
            "Decisões Tomadas": ["Adotar novo padrão"],
            "Erros Encontrados": ["Timeout inesperado"],
            "Correções Aplicadas": ["Timeout aumentado"],
            "Padrões Identificados": ["Sempre verificar path"],
            "Recomendações para Agentes": ["Testar timeouts"],
        })
        resultado = dls.executar_sincronizacao()
        self.assertIn("Dias registrados: 2", resultado)
        contexto = self._contexto_path().read_text(encoding="utf-8")
        self.assertIn("Sempre verificar path", contexto)
        self.assertIn("Timeout aumentado", contexto)
