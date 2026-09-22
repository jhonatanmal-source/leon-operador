import json
from unittest.mock import patch

import pytest
from src import operational_evidence as evidence


@pytest.fixture
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(evidence, 'DATA', tmp_path)
    return tmp_path


def decision(**overrides):
    elliott = dict(valid=True, entry_eligible=True, direction='ALTA')
    elliott.update(overrides)
    return evidence.setup_decision('COMPRA', elliott, True, True, True)


def test_context_is_not_entry():
    assert not decision(entry_eligible=False)['approved']
    assert not decision(direction='BAIXA')['approved']
    assert not evidence.setup_decision('COMPRA', {'valid': True}, True, True, True)['approved']
    assert decision()['approved']
    for value in (1, 'true', None):
        assert not decision(entry_eligible=value)['approved']


def test_latest_other_structure_cannot_confirm(data):
    preop = dict(id='PREOP-1', status='ABERTO', ativo='XAUUSD', direcao='COMPRA')
    evidence.save_setup_evidence(preop, decision(pivots=[{'type': 'LOW', 'price': 10, 'time': 'a'}]))
    other = dict(preop, id='PREOP-2')
    evidence.save_setup_evidence(other, decision(pivots=[{'type': 'LOW', 'price': 11, 'time': 'b'}]))
    assert evidence.validate_setup_evidence(preop)['error'] == 'LATEST_SETUP_NOT_CONFIRMED'


def test_funnel_counts_decisions_once(data):
    preop = dict(id='PREOP-1', status='ABERTO', direcao='COMPRA')
    evidence.save_setup_evidence(preop, decision())
    result = evidence.save_setup_evidence(preop, decision())
    assert result['funnel']['candidates'] == 1
    assert result['funnel']['approved'] == 1
    preop.update(id='PREOP-2', status='OBSERVADO')
    result = evidence.save_setup_evidence(preop, decision())
    assert result['stage'] == 'WAITING_CONFIRMATION'
    assert result['funnel']['candidates'] == 2
    assert result['funnel']['blocked_by']['pre_operation_not_open'] == 1


def test_funnel_failure_does_not_change_execution_gate(data):
    with patch.object(evidence, 'record_setup_funnel', side_effect=OSError()):
        proof = evidence.save_setup_evidence(dict(id='PREOP-1', status='ABERTO'), decision())
    assert proof['approved']
    assert proof['telemetry_error']
    assert json.loads((data / 'latest_setup_decision.json').read_text())['telemetry_error']


def test_legacy_evidence_rejected(data):
    preop = dict(id='PREOP-1', status='ABERTO', direcao='COMPRA')
    proof = evidence.save_setup_evidence(preop, decision())
    proof['version'] = 'elliott-smc-evidence-v1'
    evidence.atomic_json(data / 'setup_evidence/PREOP-1.json', proof)
    assert not evidence.validate_setup_evidence(preop)['ok']


def test_uncertainty_and_invalid_returns(data):
    base = dict(ativo='X', direcao='COMPRA', smc='UP', elliott='ONDA 3',
                source='MT5_DEMO_REAL', setup_version=evidence.VERSION,
                account_key='TEST', entry_model='ORDER_BLOCK_RETEST', context_mode='TREND')
    rows = [dict(base, realized_r=r, position_id=str(i), region_id='region-' + str(i))
            for i, r in enumerate((1, 1, 1, 1, 'NaN', 'bad'), start=1)]
    rows.append(dict(base, realized_r=100, source='SHADOW'))
    with patch.object(evidence, 'confirmed_records', return_value=rows):
        result = evidence.learning_statistics(base)
    assert result['samples'] == 4
    assert result['mean_r'] == 1
    assert result['selection_score'] == pytest.approx(1/6)
    assert result['validated_edge'] is False
