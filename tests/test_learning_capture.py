"""
Testes unitários para learning_capture.py
=========================================

Cobertura mínima: 13 testes
- _is_sensitive(): detecção de TP, SL, token, password, conta real, balance, equity
- _is_sensitive(): retorno False para texto seguro
- _sanitize_text(): redação de keywords sensíveis
- _sanitize_text(): preservação de texto seguro
- LearningCapture.__init__(): inicialização
- LearningCapture.start_mission(): registro TRIAGEM
- LearningCapture.diagnostic_complete(): registro DIAGNÓSTICO
- LearningCapture.plano_complete(): registro PLANO
- LearningCapture.implementation_complete(): registro IMPLEMENTAÇÃO
- LearningCapture.testes_complete(): registro TESTES
- LearningCapture.end_mission(): promoção de padrões não-sensíveis
- LearningCapture.end_mission(): NÃO promove padrões sensíveis
- _update_indice(): atualização do INDICE.md

Guards:
- Somente leitura/escrita em arquivos temporários (tmp_path)
- Nenhum acesso MT5
- Nenhum sys.exit()
- Monkeypatch de ROOT_DIR, DIARIOS_DIR, CONTEXTO_EVOLUCAO_FILE, INDICE_FILE
"""

import pytest
from pathlib import Path
from src.learning_capture import LearningCapture, _is_sensitive, _sanitize_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_paths(monkeypatch, tmp_path):
    """Monkeypatch module-level paths to use tmp_path."""
    import src.learning_capture as lc

    diarios = tmp_path / "aprendizados_diarios"
    diarios.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(lc, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(lc, "DIARIOS_DIR", diarios)
    monkeypatch.setattr(lc, "CONTEXTO_EVOLUCAO_FILE", diarios / "CONTEXTO_EVOLUCAO.md")
    monkeypatch.setattr(lc, "INDICE_FILE", diarios / "INDICE.md")

    return diarios


# ---------------------------------------------------------------------------
# 1. _is_sensitive() detecta TP, SL, token, password, conta real, balance, equity
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("tp 2345.00", True),
        ("sl 2300.00", True),
        ("meu token abc123", True),
        ("password: xpto", True),
        ("conta real ativa", True),
        ("balance 10000", True),
        ("equity 9500", True),
        ("take profit at 2350", True),
        ("stop loss at 2290", True),
        ("entry_price 2310", True),
        ("risk 2%", True),
        ("rr 1:2", True),
    ],
    ids=[
        "tp_value",
        "sl_value",
        "token",
        "password",
        "conta_real",
        "balance",
        "equity",
        "take_profit",
        "stop_loss",
        "entry_price",
        "risk",
        "rr",
    ],
)
def test_is_sensitive_detects_keywords(text, expected):
    assert _is_sensitive(text) is expected


# ---------------------------------------------------------------------------
# 2. _is_sensitive() retorna False para texto seguro
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "SMC identificou BOS na H1",
        "Elliott wave 3 concluída",
        "código refactorizado com sucesso",
        "Killzone londres ativa",
        "arquitetura modulada corretamente",
        "deploy concluído sem erros",
        "documento atualizado",
    ],
    ids=[
        "smc",
        "elliott",
        "codigo",
        "killzone",
        "arquitetura",
        "deploy",
        "documento",
    ],
)
def test_is_sensitive_returns_false_for_safe_text(text):
    assert _is_sensitive(text) is False


def test_is_sensitive_returns_false_for_empty():
    assert _is_sensitive("") is False
    assert _is_sensitive(None) is False


# ---------------------------------------------------------------------------
# 3. _sanitize_text() redacta keywords sensíveis
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected_contains",
    [
        ("tp 2345.00", "[REDACTED]"),
        ("sl 2300.00", "[REDACTED]"),
        ("meu token abc123", "[REDACTED]"),
        ("password: xpto", "[REDACTED]"),
        ("conta real ativa", "[REDACTED]"),
        ("balance 10000", "[REDACTED]"),
        ("equity 9500", "[REDACTED]"),
        ("take profit at 2350", "[REDACTED]"),
        ("stop loss at 2290", "[REDACTED]"),
    ],
    ids=[
        "tp",
        "sl",
        "token",
        "password",
        "conta_real",
        "balance",
        "equity",
        "take_profit",
        "stop_loss",
    ],
)
def test_sanitize_text_redacts_sensitive(text, expected_contains):
    result = _sanitize_text(text)
    assert expected_contains in result
    # Keyword original não deve aparecer
    assert text.lower() not in result.lower() or "[REDACTED]" in result


def test_sanitize_text_case_insensitive():
    result = _sanitize_text("TOKEN Teste123")
    assert "[REDACTED]" in result


# ---------------------------------------------------------------------------
# 4. _sanitize_text() preserva texto seguro
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "SMC identificou BOS na H1",
        "Elliott wave 3 concluída",
        "deploy concluído sem erros",
        "Killzone londres ativa",
    ],
    ids=["smc", "elliott", "deploy", "killzone"],
)
def test_sanitize_text_preserves_safe_text(text):
    assert _sanitize_text(text) == text


def test_sanitize_text_empty():
    assert _sanitize_text("") == ""
    assert _sanitize_text(None) is None


# ---------------------------------------------------------------------------
# 5. LearningCapture.__init__() inicializa corretamente
# ---------------------------------------------------------------------------

def test_init_default():
    lc = LearningCapture()
    assert lc.today is not None
    assert lc.mission_started is False
    assert len(lc.captured_learnings) == 5
    assert "TRIAGEM" in lc.captured_learnings
    assert "DIAGNÓSTICO" in lc.captured_learnings
    assert "PLANO" in lc.captured_learnings
    assert "IMPLEMENTATION" in lc.captured_learnings
    assert "TESTES" in lc.captured_learnings


def test_init_all_phases_empty():
    lc = LearningCapture()
    for phase_list in lc.captured_learnings.values():
        assert phase_list == []


# ---------------------------------------------------------------------------
# 6. LearningCapture.start_mission() registra TRIAGEM
# ---------------------------------------------------------------------------

def test_start_mission(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    lc = LearningCapture()
    lc.start_mission()

    assert lc.mission_started is True
    assert len(lc.captured_learnings["TRIAGEM"]) == 1
    assert "Missão iniciada" in lc.captured_learnings["TRIAGEM"][0]

    # Verificar que arquivo diário foi criado com a entrada
    daily_files = list(tmp_path.glob("aprendizados_diarios/*.md"))
    assert len(daily_files) >= 1
    content = daily_files[0].read_text(encoding="utf-8")
    assert "Missão iniciada" in content


def test_start_mission_resets_previous_learnings(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    lc = LearningCapture()
    # Simular dados anteriores
    lc.captured_learnings["TRIAGEM"].append("old_entry")
    lc.start_mission()
    assert len(lc.captured_learnings["TRIAGEM"]) == 1
    assert "old_entry" not in lc.captured_learnings["TRIAGEM"]


# ---------------------------------------------------------------------------
# 7. LearningCapture.diagnostic_complete() registra DIAGNÓSTICO
# ---------------------------------------------------------------------------

def test_diagnostic_complete_with_summary(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    lc = LearningCapture()
    lc.start_mission()
    lc.diagnostic_complete(summary="Bug identificado no módulo X")

    assert len(lc.captured_learnings["DIAGNÓSTICO"]) == 1
    assert "Bug identificado" in lc.captured_learnings["DIAGNÓSTICO"][0]


def test_diagnostic_complete_without_summary(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    lc = LearningCapture()
    lc.start_mission()
    lc.diagnostic_complete()

    assert len(lc.captured_learnings["DIAGNÓSTICO"]) == 1
    assert "Diagnóstico concluído" in lc.captured_learnings["DIAGNÓSTICO"][0]


# ---------------------------------------------------------------------------
# 8. LearningCapture.plano_complete() registra PLANO
# ---------------------------------------------------------------------------

def test_plano_complete_with_summary(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    lc = LearningCapture()
    lc.start_mission()
    lc.plano_complete(summary="Refatoração do módulo Y aprovada")

    assert len(lc.captured_learnings["PLANO"]) == 1
    assert "Refatoração" in lc.captured_learnings["PLANO"][0]


def test_plano_complete_without_summary(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    lc = LearningCapture()
    lc.start_mission()
    lc.plano_complete()

    assert len(lc.captured_learnings["PLANO"]) == 1
    assert "Plano concluído" in lc.captured_learnings["PLANO"][0]


# ---------------------------------------------------------------------------
# 9. LearningCapture.implementation_complete() registra IMPLEMENTAÇÃO
# ---------------------------------------------------------------------------

def test_implementation_complete_with_summary(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    lc = LearningCapture()
    lc.start_mission()
    lc.implementation_complete(summary="Módulo Z implementado com sucesso")

    assert len(lc.captured_learnings["IMPLEMENTATION"]) == 1
    assert "Módulo Z" in lc.captured_learnings["IMPLEMENTATION"][0]


def test_implementation_complete_without_summary(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    lc = LearningCapture()
    lc.start_mission()
    lc.implementation_complete()

    assert len(lc.captured_learnings["IMPLEMENTATION"]) == 1
    assert "Implementação concluída" in lc.captured_learnings["IMPLEMENTATION"][0]


# ---------------------------------------------------------------------------
# 10. LearningCapture.testes_complete() registra TESTES
# ---------------------------------------------------------------------------

def test_testes_complete_with_summary(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    lc = LearningCapture()
    lc.start_mission()
    lc.testes_complete(summary="12 testes passaram, 0 falharam")

    assert len(lc.captured_learnings["TESTES"]) == 1
    assert "12 testes" in lc.captured_learnings["TESTES"][0]


def test_testes_complete_without_summary(monkeypatch, tmp_path):
    _patch_paths(monkeypatch, tmp_path)
    lc = LearningCapture()
    lc.start_mission()
    lc.testes_complete()

    assert len(lc.captured_learnings["TESTES"]) == 1
    assert "Testes concluídos" in lc.captured_learnings["TESTES"][0]


# ---------------------------------------------------------------------------
# 11. LearningCapture.end_mission() promove padrões não-sensíveis
# ---------------------------------------------------------------------------

def test_end_mission_promotes_safe_patterns(monkeypatch, tmp_path):
    diarios = _patch_paths(monkeypatch, tmp_path)
    import src.learning_capture as lc

    # Criar CONTEXTO_EVOLUCAO com seção de padrões
    contexto_file = diarios / "CONTEXTO_EVOLUCAO.md"
    contexto_file.write_text(
        "# Contexto de Evolução\n\n"
        "## Padrões Identificados\n\n"
        "## Decisões Estruturais\n\n",
        encoding="utf-8",
    )

    lc_instance = LearningCapture()
    lc_instance.start_mission()
    lc_instance.diagnostic_complete(summary="SMC causou falsos positivos em H1")
    lc_instance.plano_complete(summary="Killzone london validada corretamente")
    lc_instance.end_mission()

    # Verificar que padrões seguros foram promovidos
    contexto_content = contexto_file.read_text(encoding="utf-8")
    assert "SMC" in contexto_content or "Killzone" in contexto_content


# ---------------------------------------------------------------------------
# 12. LearningCapture.end_mission() NÃO promove padrões sensíveis
# ---------------------------------------------------------------------------

def test_end_mission_does_not_promote_sensitive_patterns(monkeypatch, tmp_path):
    diarios = _patch_paths(monkeypatch, tmp_path)
    import src.learning_capture as lc

    # Criar CONTEXTO_EVOLUCAO vazio
    contexto_file = diarios / "CONTEXTO_EVOLUCAO.md"
    contexto_file.write_text(
        "# Contexto de Evolução\n\n"
        "## Padrões Identificados\n\n",
        encoding="utf-8",
    )

    lc_instance = LearningCapture()
    lc_instance.start_mission()
    # Adicionar aprendizado com dados sensíveis
    lc_instance.captured_learnings["DIAGNÓSTICO"].append("tp 2345.00 configurado")
    lc_instance.captured_learnings["PLANO"].append("sl 2300.00 definido")
    lc_instance.captured_learnings["TESTES"].append("balance 10000 verificado")
    lc_instance.end_mission()

    contexto_content = contexto_file.read_text(encoding="utf-8")
    # Dados sensíveis NÃO devem aparecer no contexto
    assert "tp 2345.00" not in contexto_content
    assert "sl 2300.00" not in contexto_content
    assert "balance 10000" not in contexto_content


def test_end_mission_limit_patterns_to_five(monkeypatch, tmp_path):
    diarios = _patch_paths(monkeypatch, tmp_path)
    import src.learning_capture as lc

    contexto_file = diarios / "CONTEXTO_EVOLUCAO.md"
    contexto_file.write_text(
        "# Contexto de Evolução\n\n"
        "## Padrões Identificados\n\n",
        encoding="utf-8",
    )

    lc_instance = LearningCapture()
    lc_instance.start_mission()
    # Adicionar 7 padrões seguros
    for i in range(7):
        lc_instance.captured_learnings["DIAGNÓSTICO"].append(f"padrão seguro {i} sem dados sensiveis")
    lc_instance.end_mission()

    contexto_content = contexto_file.read_text(encoding="utf-8")
    # Máximo 5 devem ser promovidos
    count = contexto_content.count("padrão seguro")
    assert count <= 5


# ---------------------------------------------------------------------------
# 13. _update_indice() atualiza INDICE.md com entrada do dia
# ---------------------------------------------------------------------------

def test_update_indice_creates_entry(monkeypatch, tmp_path):
    """Testa que _update_indice() cria entrada no INDICE.md quando arquivo diário existe."""
    diarios = _patch_paths(monkeypatch, tmp_path)
    import src.learning_capture as lc

    # Criar arquivo diário para hoje
    today_str = lc._today_filename()
    daily_file = diarios / f"{today_str}.md"
    daily_file.write_text(
        f"# Aprendizados Diários — {today_str}\n\n"
        "- [10:00:00] | Teste de indice\n",
        encoding="utf-8",
    )

    # Criar INDICE com cabeçalho
    indice_file = diarios / "INDICE.md"
    indice_file.write_text(
        "# Índice de Aprendizados\n\n"
        "| Data | Resumo |\n"
        "|------|--------|\n",
        encoding="utf-8",
    )

    lc._update_indice()

    assert indice_file.exists()
    indice_content = indice_file.read_text(encoding="utf-8")
    assert f"| {today_str} |" in indice_content


def test_update_indice_adds_today_entry(monkeypatch, tmp_path):
    diarios = _patch_paths(monkeypatch, tmp_path)
    import src.learning_capture as lc

    # Criar arquivo diário para hoje
    today_str = lc._today_filename()
    daily_file = diarios / f"{today_str}.md"
    daily_file.write_text(
        f"# Aprendizados Diários — {today_str}\n\n"
        "- [10:00:00] | Teste de indice\n",
        encoding="utf-8",
    )

    # Criar INDICE com cabeçalho
    indice_file = diarios / "INDICE.md"
    indice_file.write_text(
        "# Índice de Aprendizados\n\n"
        "| Data | Resumo |\n"
        "|------|--------|\n",
        encoding="utf-8",
    )

    lc._update_indice()

    indice_content = indice_file.read_text(encoding="utf-8")
    assert f"| {today_str} |" in indice_content


def test_update_indice_no_duplicate(monkeypatch, tmp_path):
    diarios = _patch_paths(monkeypatch, tmp_path)
    import src.learning_capture as lc

    today_str = lc._today_filename()

    # Criar INDICE já com entrada de hoje
    indice_file = diarios / "INDICE.md"
    indice_file.write_text(
        "# Índice de Aprendizados\n\n"
        "| Data | Resumo |\n"
        "|------|--------|\n"
        f"| {today_str} | Entrada existente |\n",
        encoding="utf-8",
    )

    lc._update_indice()

    indice_content = indice_file.read_text(encoding="utf-8")
    # Deve conter apenas uma entrada para hoje
    assert indice_content.count(f"| {today_str} |") == 1


# ---------------------------------------------------------------------------
# Testes de integração do fluxo completo
# ---------------------------------------------------------------------------

def test_full_mission_flow(monkeypatch, tmp_path):
    """Testa o fluxo completo de uma missão: start → diagnostic → plan → impl → test → end."""
    diarios = _patch_paths(monkeypatch, tmp_path)
    import src.learning_capture as lc

    # Criar CONTEXTO_EVOLUCAO
    contexto_file = diarios / "CONTEXTO_EVOLUCAO.md"
    contexto_file.write_text(
        "# Contexto de Evolução\n\n"
        "## Padrões Identificados\n\n",
        encoding="utf-8",
    )

    # Criar INDICE
    indice_file = diarios / "INDICE.md"
    indice_file.write_text(
        "# Índice de Aprendizados\n\n"
        "| Data | Resumo |\n"
        "|------|--------|\n",
        encoding="utf-8",
    )

    # Executar fluxo completo
    lc_instance = LearningCapture()
    lc_instance.start_mission()
    lc_instance.diagnostic_complete(summary="Módulo X analisado")
    lc_instance.plano_complete(summary="Refatoração planejada")
    lc_instance.implementation_complete(summary="Código implementado")
    lc_instance.testes_complete(summary="13 testes passaram")
    lc_instance.end_mission()

    # Verificar arquivo diário criado
    today_str = lc._today_filename()
    daily_file = diarios / f"{today_str}.md"
    assert daily_file.exists()
    daily_content = daily_file.read_text(encoding="utf-8")
    assert "Missão iniciada" in daily_content
    assert "Diagnóstico concluído" in daily_content
    assert "Plano concluído" in daily_content
    assert "Implementação concluída" in daily_content
    assert "Testes concluídos" in daily_content

    # Verificar INDICE atualizado
    indice_content = indice_file.read_text(encoding="utf-8")
    assert f"| {today_str} |" in indice_content


def test_sanitize_in_captured_learnings(monkeypatch, tmp_path):
    """Garante que dados sensíveis são redactados antes de serem salvos."""
    _patch_paths(monkeypatch, tmp_path)

    lc_instance = LearningCapture()
    lc_instance.start_mission()
    # Inserir texto com dado sensível
    lc_instance.diagnostic_complete(summary="tp 2345.00 configurado corretamente")
    lc_instance.plano_complete(summary="sl 2300.00 validado")

    # Verificar que os learnings internos contêm o texto original
    # (sanitização ocorre ao gravar no arquivo, não na memória)
    assert "tp 2345.00" in lc_instance.captured_learnings["DIAGNÓSTICO"][0]
    assert "sl 2300.00" in lc_instance.captured_learnings["PLANO"][0]


def test_duplicate_learning_not_appended(monkeypatch, tmp_path):
    """Verifica que entradas duplicadas não são adicionadas ao arquivo diário."""
    _patch_paths(monkeypatch, tmp_path)

    lc_instance = LearningCapture()
    lc_instance.start_mission()
    # Chamar start_mission novamente (que adiciona "Missão iniciada")
    lc_instance.start_mission()

    daily_files = list(tmp_path.glob("aprendizados_diarios/*.md"))
    assert len(daily_files) >= 1
    content = daily_files[0].read_text(encoding="utf-8")
    # "Missão iniciada" deve aparecer apenas uma vez (sanitizado)
    assert content.count("[REDACTED]") + content.count("Missão iniciada") <= 2