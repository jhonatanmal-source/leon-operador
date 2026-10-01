"""Single-writer daily report -> diary -> index pipeline; no MT5 actions."""
import argparse
import os
import tempfile
from datetime import date
from pathlib import Path

from src import daily_learning_report as report
from src import daily_learning_sync as sync

AUTO_START = "<!-- LEON_AUTO_MARKET_START -->"
AUTO_END = "<!-- LEON_AUTO_MARKET_END -->"


def _template(day):
    return f"# Aprendizados Diários — {day}\n\n" + "".join(
        f"## {section}\n\n" for section in sync.SECOES
    )


def upsert_bloco_auto(path, metricas):
    """Replace only the marked bytes; reject damaged/duplicate markers.

    Caller must serialize writers (as the operator already does). Atomic replace
    prevents a partial file on failure; the final check detects intervening edits.
    """
    path = Path(path)
    original = path.read_bytes() if path.exists() else None
    content = original if original is not None else _template(metricas['data']).encode('utf-8')
    start, end = AUTO_START.encode(), AUTO_END.encode()
    counts = content.count(start), content.count(end)
    if counts not in ((0, 0), (1, 1)):
        raise ValueError('Marcadores automaticos incompletos ou duplicados; diario preservado')
    if counts == (1, 1) and content.index(end) < content.index(start):
        raise ValueError('Marcadores automaticos invertidos; diario preservado')
    # Indented text keeps report content literal, including any Markdown markers.
    body = '\n'.join('    ' + line for line in metricas['relatorio'].splitlines())
    if AUTO_START in body or AUTO_END in body:
        raise ValueError('Relatorio contem marcador reservado')
    block = (f'{AUTO_START}\n## Dados de mercado (auto)\n\n{body}\n{AUTO_END}').encode('utf-8')
    if counts == (1, 1):
        begin = content.index(start)
        finish = content.index(end) + len(end)
        updated = content[:begin] + block + content[finish:]
    else:
        updated = content + b'\n\n' + block + b'\n'
    if updated == original:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.tmp', delete=False) as file:
            temp = Path(file.name)
            file.write(updated)
            file.flush()
            os.fsync(file.fileno())
        if original is not None:
            os.chmod(temp, path.stat().st_mode)
        current = path.read_bytes() if path.exists() else None
        if current != original:
            raise RuntimeError('Diario alterado por outro escritor; tente novamente')
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()
    return True


def executar_ciclo_aprendizado_diario(data_referencia=None):
    day = data_referencia or date.today()
    metricas = report.coletar_metricas_aprendizado(day)
    # Import an existing vault diary before creating today's file locally.
    sync.DIARIOS.mkdir(parents=True, exist_ok=True)
    sync._sincronizar_vault_para_tarefas()
    path = sync.DIARIOS / f'{day.isoformat()}.md'
    changed = upsert_bloco_auto(path, metricas)
    text = report.gerar_relatorio_aprendizado_diario(day, metricas=metricas)
    summary = sync.executar_sincronizacao()
    return {'report': text, 'diario_path': str(path),
            'diario_updated': changed, 'sync_summary': summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', type=date.fromisoformat, default=None)
    args = parser.parse_args()
    executar_ciclo_aprendizado_diario(args.date)


if __name__ == '__main__':
    main()
