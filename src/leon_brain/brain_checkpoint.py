from typing import Any

from .brain_models import BrainResult


def add_brain_to_checkpoint(checkpoint: dict, result: BrainResult) -> dict:
    active = [s.mcp_name for s in result.mcp_statuses if s.available]
    unavailable = [s.mcp_name for s in result.mcp_statuses if not s.available]

    brain_block = {
        "brain": {
            "enabled": not result.shadow_mode,
            "shadow_mode": result.shadow_mode,
            "state": result.conclusion.value,
            "mcps_active": len(active),
            "mcps_unavailable": len(unavailable),
            "mcps_list": active,
            "evidences_count": len(result.evidences),
            "conclusion": result.conclusion.value,
            "total_time_ms": result.total_time_ms,
            "partial": result.partial_result,
        }
    }

    if isinstance(checkpoint, dict):
        checkpoint.update(brain_block)
    return checkpoint


def format_panel_block(result: BrainResult) -> str:
    active = [s.mcp_name for s in result.mcp_statuses if s.available]
    unavailable = [s.mcp_name for s in result.mcp_statuses if not s.available]

    lines = []
    lines.append("")
    lines.append("LEON BRAIN")
    lines.append("")
    lines.append(f"Estado: {result.conclusion.value}")
    lines.append(f"MCPs ativos: {len(active)}")
    lines.append(f"MCPs indisponiveis: {len(unavailable)}")
    lines.append(f"Memorias consultadas: {len(result.evidences)}")
    lines.append(f"Padroes encontrados: {len(result.evidences)}")
    lines.append(f"Conclusao: {result.conclusion.value}")
    lines.append(f"Tempo: {result.total_time_ms:.0f}ms")
    lines.append(f"Modo: SHADOW" if result.shadow_mode else "Modo: ATIVO")
    lines.append("Regra: MEMORIA NAO LIBERA ORDEM")
    return "\n".join(lines)
