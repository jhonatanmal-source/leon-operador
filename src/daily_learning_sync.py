import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIARIOS = ROOT / "tarefas" / "aprendizados_diarios"
CONTEXTO_FILE = DIARIOS / "CONTEXTO_EVOLUCAO.md"
INDICE_FILE = DIARIOS / "INDICE.md"

SECOES = [
    "Operações / Missões Executadas",
    "Decisões Tomadas",
    "Erros Encontrados",
    "Correções Aplicadas",
    "Padrões Identificados",
    "Recomendações para Agentes",
]


def _arquivos_dia() -> list[Path]:
    if not DIARIOS.exists():
        return []
    return sorted(
        p
        for p in DIARIOS.iterdir()
        if re.match(r"^\d{4}-\d{2}-\d{2}\.md$", p.name)
    )


def _extrair_secao(texto: str, secao: str) -> list[str]:
    linhas = texto.splitlines()
    dentro = False
    itens = []
    for linha in linhas:
        if linha.strip().startswith("## ") and secao.lower() in linha.lower():
            dentro = True
            continue
        if dentro:
            if linha.strip().startswith("## "):
                break
            item = linha.strip()
            item = re.sub(r"^[-*]\s+", "", item)
            item = re.sub(r"^\d+[\.\)]\s*", "", item).strip()
            if item:
                itens.append(item)
    return itens


def _extrair_aprendizados(arquivo: Path) -> dict[str, list[str]]:
    texto = arquivo.read_text(encoding="utf-8")
    return {s: _extrair_secao(texto, s) for s in SECOES}


def _consolidar_todos_aprendizados() -> dict[str, list[str]]:
    consolidado: dict[str, list[str]] = {s: [] for s in SECOES}
    for arq in _arquivos_dia():
        aprendizado = _extrair_aprendizados(arq)
        for secao in SECOES:
            consolidado[secao].extend(aprendizado[secao])
    return consolidado


def _identificar_padroes_recorrentes(
    consolidado: dict[str, list[str]],
) -> list[str]:
    todos_itens = consolidado.get("Padrões Identificados", [])
    contagem = Counter(todos_itens)
    return [item for item, qtd in contagem.most_common() if qtd >= 2]


def _gerar_tabela_correcoes(
    consolidado: dict[str, list[str]],
) -> str:
    linhas = ["| Data | Arquivo | Correção |", "|------|---------|----------|"]
    for arq in _arquivos_dia():
        correcoes = _extrair_secao(
            arq.read_text(encoding="utf-8"), "Correções Aplicadas"
        )
        for corr in correcoes:
            linhas.append(f"| {arq.stem} | — | {corr} |")
    return "\n".join(linhas)


def _atualizar_contexto_evolucao(consolidado: dict[str, list[str]]) -> bool:
    padroes = _identificar_padroes_recorrentes(consolidado)
    correcoes = _gerar_tabela_correcoes(consolidado)
    erros = consolidado.get("Erros Encontrados", [])
    decisoes = consolidado.get("Decisões Tomadas", [])

    padroes_texto = "\n".join(
        f"- {p}" for p in padroes
    ) or "*(Nenhum padrão registrado ainda)*"
    erros_texto = "\n".join(f"- {e}" for e in erros) or "*(Nenhum erro registrado ainda)*"
    decisoes_texto = "\n".join(
        f"- {d}" for d in decisoes
    ) or "*(Nenhuma decisão registrada ainda)*"

    novo = f"""# Contexto de Evolução — Aprendizados Acumulados

Este arquivo é carregado por todos os agentes ao iniciar uma missão.
Contém padrões, decisões, erros e correções acumulados que evoluem o conhecimento da equipe.

## Como usar
- Leia este arquivo no início de cada missão
- Adicione novos aprendizados ao final do dia em `tarefas/aprendizados_diarios/YYYY-MM-DD.md`
- Apenas padrões recorrentes e decisões estruturais devem ser promovidos para cá

---

## Padrões Identificados

{padroes_texto}

## Decisões Estruturais

{decisoes_texto}

## Erros Recorrentes

{erros_texto}

## Correções Aplicadas

{correcoes}

## Contratos Protegidos (relembre)
- Conta real sempre bloqueada
- Nenhum agente pode enviar ordens MT5
- Nenhum agente pode remover guards
- Toda alteração exige diagnóstico, plano, testes, revisão e relatório
"""
    if CONTEXTO_FILE.exists():
        existente = CONTEXTO_FILE.read_text(encoding="utf-8")
        if existente.strip() == novo.strip():
            return False

    CONTEXTO_FILE.write_text(novo, encoding="utf-8")
    return True


def _atualizar_indice() -> bool:
    arquivos = _arquivos_dia()
    linhas = [
        "# Índice de Aprendizados Diários",
        "",
        "## Estrutura",
        "Cada arquivo `YYYY-MM-DD.md` contém os aprendizados do dia.",
        "",
        "## Contexto Acumulado",
        "`CONTEXTO_EVOLUCAO.md` — compilado dos aprendizados mais relevantes para consulta rápida dos agentes.",
        "",
        "## Entradas",
        "",
        "| Data | Resumo |",
        "|------|--------|",
    ]
    for arq in arquivos:
        primeira_linha = arq.read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
        linhas.append(f"| {arq.stem} | {primeira_linha} |")

    novo = "\n".join(linhas) + "\n"
    if INDICE_FILE.exists():
        existente = INDICE_FILE.read_text(encoding="utf-8")
        if existente.strip() == novo.strip():
            return False

    INDICE_FILE.write_text(novo, encoding="utf-8")
    return True


def _gerar_resumo(consolidado: dict[str, list[str]]) -> str:
    total_erros = len(consolidado.get("Erros Encontrados", []))
    total_padroes = len(consolidado.get("Padrões Identificados", []))
    total_decisoes = len(consolidado.get("Decisões Tomadas", []))
    total_correcoes = len(consolidado.get("Correções Aplicadas", []))
    total_dias = len(_arquivos_dia())
    padroes_recorrentes = _identificar_padroes_recorrentes(consolidado)

    return (
        f"[DAILY LEARNING SYNC] {date.today()}\n"
        f"  Dias registrados: {total_dias}\n"
        f"  Decisões: {total_decisoes}\n"
        f"  Erros: {total_erros}\n"
        f"  Correções: {total_correcoes}\n"
        f"  Padrões: {total_padroes}\n"
        f"  Padrões recorrentes: {len(padroes_recorrentes)}\n"
        f"  Contexto: {'atualizado' if _atualizar_contexto_evolucao(consolidado) else 'já sincronizado'}\n"
        f"  Índice: {'atualizado' if _atualizar_indice() else 'já sincronizado'}"
    )


def executar_sincronizacao(force: bool = False) -> str:
    DIARIOS.mkdir(parents=True, exist_ok=True)
    consolidado = _consolidar_todos_aprendizados()
    resumo = _gerar_resumo(consolidado)
    print(resumo)
    return resumo


def main():
    force = "--force" in sys.argv
    executar_sincronizacao(force=force)


if __name__ == "__main__":
    main()
