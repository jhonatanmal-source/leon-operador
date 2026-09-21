from typing import Any

from .brain_models import BrainResult, MCPStatus


def generate_short_summary(result: BrainResult) -> str:
    lines = []
    lines.append("LEON BRAIN CONTEXT")
    lines.append("")

    active = [s.mcp_name for s in result.mcp_statuses if s.available]
    unavailable = [s.mcp_name for s in result.mcp_statuses if not s.available]

    lines.append(f"Estado: {'PARCIAL' if result.partial_result else 'COMPLETO'}")
    lines.append(f"MCPs consultados: {', '.join(active) if active else 'NENHUM'}")
    if unavailable:
        lines.append(f"MCPs indisponiveis: {', '.join(unavailable)}")
    lines.append(f"Tempo total: {result.total_time_ms:.0f}ms")
    if result.partial_result:
        lines.append("Resultado: PARCIAL")
    lines.append("")

    ctx = result.context
    if ctx:
        lines.append(f"Mercado atual: {ctx.symbol} @ {ctx.price}")
        lines.append(f"Zona: {ctx.zone_type} ({ctx.zone_timeframe})")
        lines.append(f"Estrutura: {ctx.smc_state}")
        lines.append(f"Sessao: {ctx.session} / Killzone: {ctx.killzone}")
        lines.append(f"Elliott: {ctx.elliott_state}")
        lines.append(f"Fibonacci: {ctx.fibonacci_context}")
        lines.append(f"Liquidez: {ctx.liquidity_context}")
        lines.append("")

    validated = [e for e in result.evidences if e.status.value in ("VALIDATED", "UNDER_VALIDATION")]
    if validated:
        lines.append(f"Memorias validades: {len(validated)}")
        lines.append(f"Padroes encontrados: {len(result.evidences)}")

    lines.append(f"Conclusao: {result.conclusion.value}")
    lines.append(f"Modo: SHADOW" if result.shadow_mode else "Modo: ATIVO")
    lines.append("Regra: MEMORIA NAO LIBERA ORDEM")

    return "\n".join(lines)


def generate_panel_block(result: BrainResult) -> str:
    lines = []
    lines.append("")
    lines.append("LEON BRAIN")
    lines.append("")

    active = [s.mcp_name for s in result.mcp_statuses if s.available]
    unavailable = [s.mcp_name for s in result.mcp_statuses if not s.available]

    lines.append(f"Estado: {result.conclusion.value}")
    lines.append(f"MCPs ativos: {len(active)}")
    lines.append(f"MCPs indisponiveis: {len(unavailable)}")
    lines.append(f"Memorias consultadas: {len(result.evidences)}")
    lines.append(f"Padroes encontrados: {len(result.evidences)}")
    lines.append(f"Conclusao: {result.conclusion.value}")
    lines.append(f"Tempo: {result.total_time_ms:.0f}ms")
    lines.append(f"Modo: SHADOW")
    lines.append("Regra: MEMORIA NAO LIBERA ORDEM")

    return "\n".join(lines)
