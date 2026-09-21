"""Describe timeframe relationships without authorizing orders or inferring a reversal."""
from src.timeframe_policy import evaluate_timeframe_policy

DIRECTIONS = {'ALTA', 'BAIXA'}


def describe_multidegree(top_down):
    h4 = top_down.get('h4_bias')
    h1 = top_down.get('h1_contexto')
    m15 = top_down.get('m15_gatilho')
    macro, macro_tf = (h4, 'H4') if h4 in DIRECTIONS else (h1, 'H1')
    if macro not in DIRECTIONS:
        macro, macro_tf = None, None
    if macro is None:
        phase = 'MACRO_INDEFINIDO'
    elif m15 not in DIRECTIONS:
        phase = 'POSSIVEL_CORRECAO_NO_H1' if h1 in DIRECTIONS and h1 != macro else 'MENOR_SEM_DIRECAO'
    elif m15 != macro:
        phase = 'POSSIVEL_CORRECAO_NO_MENOR'
    elif h1 in DIRECTIONS and h1 != macro:
        phase = 'MICRO_A_FAVOR_MACRO_H1_AINDA_CONTRARIO'
    else:
        phase = 'MOVIMENTO_ALINHADO'
    corrections = [dict(timeframe=tf, direction=value) for tf,value in (('H1',h1),('M15',m15))
                   if macro and value in DIRECTIONS and value != macro]
    return dict(macro_direction=macro, macro_timeframe=macro_tf, corrections=corrections,
                h4_direction=h4, h1_direction=h1, m15_direction=m15,
                phase=phase, reversal_confirmed=False,
                entry_authorized=False, entry_owner='SMC')


def diagnose_candidate(top_down, direction):
    """Read-only comparison against the currently installed tactical policy."""
    result = describe_multidegree(top_down)
    candidate = {'COMPRA': 'ALTA', 'VENDA': 'BAIXA'}.get(direction)
    macro, lower = result['macro_direction'], result['m15_direction']
    if candidate is None or macro is None:
        intent = 'SEM_CANDIDATO_DIRECIONAL'
    elif candidate == macro:
        intent = 'RETOMADA_A_CONFIRMAR_SMC' if lower in DIRECTIONS and lower != macro else 'A_FAVOR_DA_TENDENCIA_MAIOR'
    elif candidate in [c['direction'] for c in result['corrections']]:
        intent = 'CORRECAO_CONTRA_TENDENCIA_MAIOR'
    else:
        intent = 'SEM_ALINHAMENTO_COM_MOVIMENTO_MENOR'
    result.update(candidate_direction=candidate, intent=intent,
                  current_policy=evaluate_timeframe_policy(top_down, direction))
    return result


def evaluate_daytrade_context(top_down, direction):
    """Allow the macro leg or observed M15 correction; SMC must trigger either."""
    context = diagnose_candidate(top_down, direction)
    intent = context['intent']
    approved = intent in {'A_FAVOR_DA_TENDENCIA_MAIOR', 'RETOMADA_A_CONFIRMAR_SMC',
                          'CORRECAO_CONTRA_TENDENCIA_MAIOR'}
    correction = intent == 'CORRECAO_CONTRA_TENDENCIA_MAIOR'
    return dict(approved=approved, mode='CORRECAO' if approved and correction else 'TENDENCIA' if approved else 'BLOQUEADO',
                risk_factor=0.5 if approved and correction else 1.0 if approved else 0,
                reason=intent, context=context, smc_trigger_required=True)
