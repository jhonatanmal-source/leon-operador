from typing import Optional

from .brain_models import BrainEvidence, MemoryStatus


class BrainMemory:

    def __init__(self, memory_mcp):
        self._memory_mcp = memory_mcp

    def consultar(self, contexto: dict, max_results: int = 10) -> list[BrainEvidence]:
        try:
            memories, status = self._memory_mcp.consultar_memorias(contexto)
        except Exception:
            return []

        if not status.available:
            return []

        evidences = []
        for mem in (memories or [])[:max_results]:
            status_str = mem.get("status", "OBSERVATION")
            try:
                mem_status = MemoryStatus(status_str)
            except ValueError:
                mem_status = MemoryStatus.OBSERVATION

            evidences.append(BrainEvidence(
                evidence_id=mem.get("id", ""),
                evidence_type=mem.get("type", "memory"),
                source_mcp="leon-memory",
                source_reference=mem.get("reference", ""),
                status=mem_status,
                relevance=float(mem.get("relevance", 0)),
                created_at=mem.get("created_at", ""),
                summary=mem.get("summary", ""),
            ))

        return evidences

    def filtrar_validados(self, evidences: list[BrainEvidence]) -> list[BrainEvidence]:
        return [e for e in evidences if e.status in (MemoryStatus.VALIDATED, MemoryStatus.UNDER_VALIDATION)]

    def registrar(self, observacao: dict) -> Optional[str]:
        return self._memory_mcp.registrar_observacao(observacao)
