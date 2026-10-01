from datetime import date
from unittest import mock

import pytest

from src import daily_learning_diary as diary
from src import daily_learning_report as report
from src import daily_learning_sync as sync


def metrics(text='Precos coletados: 3'):
    return {'data': date(2026, 9, 30), 'relatorio': text}


def test_create_and_repeat_is_byte_identical(tmp_path):
    path = tmp_path / '2026-09-30.md'
    assert diary.upsert_bloco_auto(path, metrics())
    original = path.read_bytes()
    assert not diary.upsert_bloco_auto(path, metrics())
    assert path.read_bytes() == original
    assert all(section in path.read_text(encoding='utf-8') for section in sync.SECOES)


def test_preserve_manual_bytes_before_and_after_block(tmp_path):
    path = tmp_path / '2026-09-30.md'
    prefix = b'\xef\xbb\xbf# Manual\r\n\r\n'
    suffix = '\r\n## Decisões Tomadas\r\n- Manter revisão humana.\r\n'.encode()
    path.write_bytes(prefix + diary.AUTO_START.encode() + b'OLD' + diary.AUTO_END.encode() + suffix)
    diary.upsert_bloco_auto(path, metrics())
    assert path.read_bytes().startswith(prefix)
    assert path.read_bytes().endswith(suffix)
    assert b'OLD' not in path.read_bytes()
    assert path.read_bytes().count(diary.AUTO_START.encode()) == 1


@pytest.mark.parametrize('text', [diary.AUTO_START, diary.AUTO_END,
    diary.AUTO_END + diary.AUTO_START, diary.AUTO_START * 2 + diary.AUTO_END])
def test_damaged_markers_refuse_to_overwrite(tmp_path, text):
    path = tmp_path / 'diary.md'
    path.write_text(text, encoding='utf-8')
    original = path.read_bytes()
    with pytest.raises(ValueError):
        diary.upsert_bloco_auto(path, metrics())
    assert path.read_bytes() == original


def test_append_preserves_manual_text_and_excludes_auto_from_sync(tmp_path):
    path = tmp_path / '2026-09-30.md'
    manual = '## Recomendações para Agentes\n- Conferir dados.\n'
    path.write_text(manual, encoding='utf-8')
    original = path.read_bytes()
    diary.upsert_bloco_auto(path, metrics('## Padrões Identificados\n- Metrica automatica'))
    assert path.read_bytes().startswith(original)
    extracted = sync._extrair_aprendizados(path)
    assert extracted['Recomendações para Agentes'] == ['Conferir dados.']
    assert extracted['Padrões Identificados'] == []


def test_failed_atomic_replace_preserves_original(tmp_path):
    path = tmp_path / 'diary.md'
    path.write_bytes(b'Manual')
    with mock.patch.object(diary.os, 'replace', side_effect=OSError('disk failure')):
        with pytest.raises(OSError):
            diary.upsert_bloco_auto(path, metrics())
    assert path.read_bytes() == b'Manual'
    assert list(tmp_path.glob('*.tmp')) == []


def test_real_cycle_isolated_csv_and_curated_context(tmp_path, monkeypatch):
    diaries = tmp_path / 'diaries'
    vault = tmp_path / 'vault'
    diaries.mkdir()
    vault.mkdir()
    context = diaries / 'CONTEXTO_EVOLUCAO.md'
    context.write_bytes(b'<!-- CURADO_MANUALMENTE -->\nCuradoria humana\n')
    original = context.read_bytes()
    for name, value in {
        'DIARIOS': diaries, 'CONTEXTO_FILE': context,
        'INDICE_FILE': diaries / 'INDICE.md', 'VAULT_DIARIOS': vault,
        'VAULT_CONTEXTO': vault / 'CONTEXTO_EVOLUCAO.md',
        'VAULT_INDICE': vault / 'INDICE.md',
    }.items():
        monkeypatch.setattr(sync, name, value)
    # Every CSV/JSON input and report output lives in the fixture directory.
    for name, value in vars(report).copy().items():
        if name.endswith('_FILE'):
            monkeypatch.setattr(report, name, tmp_path / value.name)
    monkeypatch.setattr(report, 'REPORTS_DIR', tmp_path)
    (vault / '2026-09-30.md').write_text('## Decisões Tomadas\n- Nota do vault.\n', encoding='utf-8')
    report.PRICE_HISTORY_FILE.write_text(
        'data;ativo;bid;ask\n2026-09-30T10:00:00;XAUUSD;10;11\n'
        '2026-09-29T10:00:00;XAUUSD;9;10\n', encoding='utf-8')
    day = date(2026, 9, 30)
    collected = report.coletar_metricas_aprendizado(day)
    assert collected['total_precos'] == 1
    assert not report.DAILY_LEARNING_FILE.exists()
    result = diary.executar_ciclo_aprendizado_diario(day)
    path = diaries / '2026-09-30.md'
    first = path.read_bytes()
    repeated = diary.executar_ciclo_aprendizado_diario(day)
    assert result['diario_updated']
    assert not repeated['diario_updated']
    assert path.read_bytes() == first
    assert 'Nota do vault.' in path.read_text(encoding='utf-8')
    assert context.read_bytes() == original
    assert '2026-09-30' in sync.INDICE_FILE.read_text(encoding='utf-8')
    assert 'Precos coletados: 1' in result['report']


@pytest.mark.parametrize('failed', [False, True])
def test_operator_only_marks_day_complete_after_success(monkeypatch, failed):
    from src import leon_operator as operator

    mocks = {}
    for name in ('_ler_ultima_execucao', '_salvar_execucao', 'registrar_log',
                 'registrar_erro', 'enviar_erro_sistema',
                 'gerar_relatorio_operador_diario', 'generate_setup_audit',
                 'enviar_relatorio_aprendizado_texto',
                 'executar_ciclo_aprendizado_diario'):
        mocks[name] = mock.Mock()
        monkeypatch.setattr(operator, name, mocks[name])
    mocks['_ler_ultima_execucao'].return_value = None
    mocks['gerar_relatorio_operador_diario'].return_value = 'operador'
    mocks['generate_setup_audit'].return_value = {'text': 'audit', 'audit': {'status': 'OK'}}
    pipeline = mocks['executar_ciclo_aprendizado_diario']
    pipeline.return_value = {'report': 'daily report'}
    if failed:
        pipeline.side_effect = OSError('diary failed')
    result = operator.executar_aprendizado_diario()
    assert result['ok'] is not failed
    pipeline.assert_called_once_with(date.today())
    if failed:
        mocks['_salvar_execucao'].assert_not_called()
        mocks['enviar_relatorio_aprendizado_texto'].assert_not_called()
    else:
        mocks['_salvar_execucao'].assert_called_once_with(date.today())
        assert mocks['enviar_relatorio_aprendizado_texto'].call_args_list[0].args == ('daily report',)
