from typing import Any

from .brain_models import BrainConclusion, BrainEvidence, MemoryStatus


class BrainProfessor:

    def gerar_explicacao(
        self,
        context_summary: str,
        evidences: list[BrainEvidence],
        patterns: dict[str, Any],
    ) -> str:
        lines = []

        validated = [e for e in evidences if e.status == MemoryStatus.VALIDATED]
        hypotheses = [e for e in evidences if e.status in (MemoryStatus.UNDER_VALIDATION, MemoryStatus.HYPOTHESIS, MemoryStatus.OBSERVATION)]

        lines.append(f"Contexto: {context_summary}")

        if validated:
            lines.append(f"Evidencias validadas: {len(validated)}")
            for ev in validated[:3]:
                lines.append(f"  - [{ev.evidence_id}] {ev.summary} (fonte: {ev.source_mcp})")

        if hypotheses:
            lines.append(f"Hipoteses em analise: {len(hypotheses)}")
            for ev in hypotheses[:3]:
                lines.append(f"  - [{ev.evidence_id}] {ev.summary}")

        similar = patterns.get("similar_contexts", [])
        if similar:
            best = max(similar, key=lambda x: x["similarity"])
            lines.append(f"Contexto semelhante encontrado (similaridade: {best['similarity']:.0%})")
            lines.append(f"  Resultado anterior: {best.get('result', 'N/A')}")
            if best.get("lesson"):
                lines.append(f"  Licao: {best['lesson']}")
        else:
            lines.append("Sem memoria suficiente para comparacao.")

        errors = patterns.get("recurring_errors", [])
        if errors:
            lines.append(f"Erros recorrentes: {len(errors)} ocorrencia(s)")

        blockers = patterns.get("blockers", [])
        if blockers:
            lines.append(f"Bloqueios atuais: {', '.join(blockers)}")

        lines.append("")
        lines.append("Regra: A memoria nao libera operacao.")
        lines.append("Conclusao baseada em evidencia real, nao em hipotese.")

        return "\n".join(lines)

    def gerar_conclusao(self, evidences: list[BrainEvidence], patterns: dict[str, Any]) -> BrainConclusion:
        validated = [e for e in evidences if e.status == MemoryStatus.VALIDATED]

        if not evidences:
            return BrainConclusion.NO_EVIDENCE

        favorable = 0
        unfavorable = 0

        for ev in validated:
            if "favoravel" in ev.summary.lower() or "positivo" in ev.summary.lower():
                favorable += 1
            elif "desfavoravel" in ev.summary.lower() or "negativo" in ev.summary.lower():
                unfavorable += 1

        if favorable > unfavorable:
            return BrainConclusion.FAVORABLE
        elif unfavorable > favorable:
            return BrainConclusion.UNFAVORABLE
        else:
            return BrainConclusion.INCONCLUSIVE
