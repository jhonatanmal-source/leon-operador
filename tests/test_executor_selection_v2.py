"""Isolated selection tests plus static send guards, not MT5 integration tests.

Only the selected function AST is compiled. No executor imports or top-level
statements run; CSV input, clock, evidence and learning dependencies are mocks.
"""
import ast
import io
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest


SOURCE = Path(__file__).resolve().parents[1] / 'src' / 'mt5_order_executor.py'


def tree():
    return ast.parse(SOURCE.read_text(encoding='utf-8-sig'))


def selection(rows, scores, *, invalid=(), executed=(), exists=True):
    function = next(n for n in tree().body if isinstance(n, ast.FunctionDef)
                    and n.name == '_ultima_pre_operacao_aberta')
    program = ast.Module(body=[function], type_ignores=[])
    file = Mock()
    file.exists.return_value = exists
    file.open.side_effect = lambda *args, **kwargs: io.StringIO('mock CSV')
    reader = Mock(return_value=[dict(row) for row in rows])
    validate = Mock(side_effect=lambda row: {'ok': row['id'] not in invalid})
    sent = Mock(side_effect=lambda identifier: identifier in executed)
    statistics = Mock(side_effect=lambda row: scores[row['id']])
    clock = Mock()
    clock.now.return_value = datetime(2026, 9, 11, 12, 34, 56)
    old_score = Mock(side_effect=AssertionError('Score must come from frozen statistics'))
    namespace = dict(PRE_OPERATION_FILE=file, csv=SimpleNamespace(DictReader=reader),
                     validate_setup_evidence=validate, _pre_operacao_ja_executada=sent,
                     learning_statistics=statistics, learning_score=old_score,
                     datetime=clock, VERSION='test-v2')
    exec(compile(program, str(SOURCE), 'exec'), namespace)
    return namespace['_ultima_pre_operacao_aberta'], statistics, validate, reader


def row(identifier, time='2026-09-11T12:00:00', status='ABERTO'):
    return dict(id=identifier, data_abertura=time, status=status)


def test_choice_freezes_statistics_used_for_ranking():
    scores = {'older': {'selection_score': 0.8, 'samples': 12, 'mean_r': 1.2},
              'newer': {'selection_score': 0.2, 'samples': 4, 'mean_r': 0.4}}
    choose, stats, _, _ = selection([row('older'), row('newer', '2026-09-11T12:01:00')], scores)
    chosen = choose()
    assert chosen['id'] == 'older'
    assert chosen['_selection'] == dict(scores['older'], selected_at='2026-09-11T12:34:56', version='test-v2')
    assert [call.args[0]['id'] for call in stats.call_args_list] == ['older', 'newer']
    assert stats.call_count == 2
    scores['older']['selection_score'] = -100
    scores['older']['samples'] = 999
    assert chosen['_selection']['selection_score'] == 0.8
    assert chosen['_selection']['samples'] == 12


@pytest.mark.parametrize('reverse', [False, True])
def test_tie_uses_most_recent_time_not_csv_order(reverse):
    rows = [row('old'), row('new', '2026-09-11T12:01:00')]
    choose, _, _, _ = selection(rows[::-1] if reverse else rows,
                               {key: {'selection_score': 0} for key in ('old', 'new')})
    assert choose()['id'] == 'new'


def test_ineligible_candidates_never_reach_ranking():
    rows = [row('closed', status='FECHADO'), row('expired'), row('already_sent'), row('eligible')]
    choose, stats, validate, _ = selection(rows, {'eligible': {'selection_score': -0.2}},
                                         invalid={'expired'}, executed={'already_sent'})
    assert choose()['id'] == 'eligible'
    stats.assert_called_once()
    assert stats.call_args.args[0]['id'] == 'eligible'
    assert 'closed' not in [call.args[0]['id'] for call in validate.call_args_list]


def test_no_eligible_candidates_does_not_rank():
    choose, stats, _, _ = selection([row('expired')], {}, invalid={'expired'})
    assert choose() is None
    stats.assert_not_called()


def test_missing_file_does_not_read_or_rank():
    choose, stats, validate, reader = selection([], {}, exists=False)
    assert choose() is None
    for dependency in (stats, validate, reader):
        dependency.assert_not_called()


def sends(statement):
    return [n for n in ast.walk(statement) if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute) and n.func.attr == 'order_send']


def test_both_send_sites_have_immediate_fail_closed_revalidation():
    """Require validation + returning rejection guard directly before each send."""
    module = tree()
    checked = 0
    for parent in ast.walk(module):
        for _, block in ast.iter_fields(parent):
            if not isinstance(block, list):
                continue
            for index, statement in enumerate(block):
                if not isinstance(statement, ast.Assign) or not sends(statement):
                    continue
                checked += 1
                assert index >= 2
                validation, guard = block[index - 2:index]
                assert isinstance(validation, ast.Assign)
                call = validation.value
                assert isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                assert call.func.id == 'validate_setup_evidence'
                assert len(call.args) == 1 and isinstance(call.args[0], ast.Name)
                assert call.args[0].id == 'pre_operacao'
                gate = validation.targets[0].id
                assert isinstance(guard, ast.If)
                assert ast.dump(guard.test) == ast.dump(ast.parse(f"not {gate}.get('ok')", mode='eval').body)
                assert len(guard.body) == 1 and isinstance(guard.body[0], ast.Return)
                rejection = guard.body[0].value
                assert isinstance(rejection, ast.Call) and isinstance(rejection.func, ast.Name)
                assert rejection.func.id == '_bloqueio'
                assert not guard.orelse
    assert checked == len(sends(module)) == 2, 'Check every initial/retry send site'


def test_no_learning_recalculation_after_send_and_metadata_uses_snapshot():
    module = tree()
    first_send = min(call.lineno for call in sends(module))
    late = [n for n in ast.walk(module) if isinstance(n, ast.Call) and n.lineno > first_send
            and ((isinstance(n.func, ast.Name) and n.func.id in {'learning_score', 'learning_statistics'})
                 or (isinstance(n.func, ast.Attribute) and n.func.attr in {'learning_score', 'learning_statistics'}))]
    assert not late, 'Post-send score must not be recalculated'
    metadata = [n for n in ast.walk(module) if isinstance(n, ast.Dict) and n.lineno > first_send
                and any(isinstance(k, ast.Constant) and k.value == 'selection_statistics' for k in n.keys)]
    assert metadata, 'Order evidence must persist frozen selection statistics'
    for item in metadata:
        values = {k.value: v for k, v in zip(item.keys, item.values) if isinstance(k, ast.Constant)}
        expected = ast.parse("pre_operacao.get('_selection', {})", mode='eval').body
        assert ast.dump(values['selection_statistics']) == ast.dump(expected)
        expected_score = ast.parse("pre_operacao.get('_selection', {}).get('selection_score')", mode='eval').body
        assert ast.dump(values['selection_score']) == ast.dump(expected_score)


def compiled_send_segment(monkeypatch, gates):
    """Execute only source import/send/retry statements with explicit mocks.

    Stop before the outer final mt5.shutdown; retain shutdown inside the retry
    branch. This does not exercise the enclosing executor's try/finally.
    """
    segments = []
    for parent in ast.walk(tree()):
        for _, block in ast.iter_fields(parent):
            if not isinstance(block, list):
                continue
            for start, node in enumerate(block):
                if not isinstance(node, ast.Import) or not any(
                        alias.name == 'mt5linux_compat' for alias in node.names):
                    continue
                for end in range(start + 1, len(block)):
                    candidate = block[end]
                    if (isinstance(candidate, ast.Expr) and isinstance(candidate.value, ast.Call)
                            and isinstance(candidate.value.func, ast.Attribute)
                            and isinstance(candidate.value.func.value, ast.Name)
                            and candidate.value.func.value.id == 'mt5'
                            and candidate.value.func.attr == 'shutdown'):
                        segments.append(block[start:end])
                        break
    assert len(segments) == 1, 'Expected one isolated initial-send/retry block'
    assert len(sends(ast.Module(body=segments[0], type_ignores=[]))) == 2
    wrapper = ast.parse('def send_segment():\n    pass\n')
    wrapper.body[0].body = segments[0]
    ast.fix_missing_locations(wrapper)

    execution = ModuleType('mt5linux_compat')
    execution.order_send = Mock(return_value=None)
    execution.last_error = Mock(return_value=(-10001, 'mock IPC failure'))
    execution.shutdown = Mock()
    execution.initialize = Mock(return_value=True)
    monkeypatch.setitem(sys.modules, 'mt5linux_compat', execution)
    gate = Mock(side_effect=gates)
    blocked = Mock(side_effect=lambda error, details: {'ok': False, 'error': error, 'details': details})
    preop, request = {'id': 'PREOP-test'}, {'symbol': 'MOCK_ONLY'}
    safe_mt5 = SimpleNamespace(shutdown=Mock())
    namespace = dict(validate_setup_evidence=gate, _bloqueio=blocked,
                     pre_operacao=preop, request=request, registrar_log=Mock(), mt5=safe_mt5)
    exec(compile(wrapper, str(SOURCE), 'exec'), namespace)
    return namespace['send_segment'], execution, gate, blocked, safe_mt5, preop, request


def test_executable_final_gate_failure_sends_no_order(monkeypatch):
    failure = {'ok': False, 'error': 'SETUP_EVIDENCE_STALE'}
    run, mt5, gate, blocked, safe_mt5, preop, _ = compiled_send_segment(monkeypatch, [failure])
    result = run()
    assert result['error'] == 'SETUP_EVIDENCE_STALE'
    gate.assert_called_once_with(preop)
    blocked.assert_called_once_with('SETUP_EVIDENCE_STALE', failure)
    mt5.order_send.assert_not_called()
    mt5.initialize.assert_not_called()
    mt5.shutdown.assert_not_called()
    safe_mt5.shutdown.assert_not_called()


def test_executable_retry_gate_failure_prevents_second_order(monkeypatch):
    failure = {'ok': False, 'error': 'SETUP_EVIDENCE_STALE'}
    run, mt5, gate, blocked, safe_mt5, preop, request = compiled_send_segment(
        monkeypatch, [{'ok': True}, failure])
    sequence = Mock()
    for name, dependency in [('gate', gate), ('send', mt5.order_send),
                             ('shutdown', mt5.shutdown), ('initialize', mt5.initialize)]:
        sequence.attach_mock(dependency, name)
    result = run()
    assert result['error'] == 'SETUP_EVIDENCE_STALE'
    mt5.order_send.assert_called_once_with(request)
    mt5.shutdown.assert_called_once_with()
    mt5.initialize.assert_called_once_with()
    assert gate.call_count == 2
    assert all(call.args == (preop,) for call in gate.call_args_list)
    assert [call[0] for call in sequence.mock_calls] == ['gate', 'send', 'shutdown', 'initialize', 'gate']
    blocked.assert_called_once_with('SETUP_EVIDENCE_STALE', failure)
    safe_mt5.shutdown.assert_not_called()
