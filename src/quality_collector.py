"""Bounded, separate MT5 read-only job. Never modifies the confirmed outcome ledger."""
import hashlib
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from src.operational_evidence import atomic_json, read_json, VERSION
from src.trade_quality import execution_quality, quote_excursions

DATA = Path(__file__).resolve().parent.parent / 'data'
BATCH = 10000
MAX_BATCHES = 6


def cache_key(row):
    return hashlib.sha256(f"{row['account_key']}:{row['position_id']}".encode()).hexdigest()


def tick_history(mt5, symbol, start, end):
    cursor = int(start)//1000
    found = {}
    reason = 'BATCH_LIMIT'
    for _ in range(MAX_BATCHES):
        data = mt5.copy_ticks_from(symbol, datetime.fromtimestamp(cursor, timezone.utc), BATCH, mt5.COPY_TICKS_ALL)
        if data is None:
            reason = 'BROKER_HISTORY_UNAVAILABLE'
            break
        if not len(data):
            reason = 'NO_MORE_TICKS'
            break
        latest = cursor*1000
        for tick in data:
            t, bid, ask = int(tick['time_msc']), float(tick['bid']), float(tick['ask'])
            latest = max(latest, t)
            if start <= t <= end:
                found[(t, bid, ask)] = {'time_msc': t, 'bid': bid, 'ask': ask}
        if latest >= end:
            reason = 'REQUESTED_END_REACHED'
            break
        if len(data) < BATCH:
            reason = 'AVAILABLE_HISTORY_EXHAUSTED'
            break
        # Overlap the last second; extrema do not need duplicate identical quotes.
        next_cursor = latest//1000
        if next_cursor <= cursor:
            reason = 'PAGINATION_STALLED'
            break
        cursor = next_cursor
    return list(found.values()), reason


def measure(mt5, row):
    position = int(row['position_id'])
    deals = mt5.history_deals_get(position=position)
    if not deals or any(d.symbol != row['ativo'] for d in deals):
        raise ValueError('Broker identity not confirmed')
    entries = [d for d in deals if d.entry == mt5.DEAL_ENTRY_IN]
    exits = [d for d in deals if d.entry in (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_OUT_BY)]
    if not entries or not exits or not any(int(d.order) == int(row['order_ticket']) for d in entries):
        raise ValueError('Entry or exit unavailable')
    # A single entry order can have several fills. Scale-ins need time-weighted exposure.
    if len({int(d.order) for d in entries}) != 1:
        return {'status': 'UNSUPPORTED_SCALE_IN', 'mfe_r': None, 'mae_r': None}
    start = min(int(getattr(d, 'time_msc', d.time*1000)) for d in entries)
    end = max(int(getattr(d, 'time_msc', d.time*1000)) for d in exits)
    quality = execution_quality(row['direcao'], row.get('entrada'), entries, deals)
    ticks, coverage = tick_history(mt5, row['ativo'], start, end+3600000)
    metrics = quote_excursions(row['direcao'], quality['actual_entry'], row.get('stop'),
                              row.get('tp2') or row.get('tp'), start, end, ticks)
    latest = mt5.symbol_info_tick(row['ativo'])
    broker_now = int(getattr(latest, 'time_msc', 0)) if latest else 0
    return dict(metrics, execution=quality, collection_reason=coverage,
                entry_msc=start, exit_msc=end, post_exit_window_elapsed=broker_now >= end+3600000,
                time_basis='broker_deal_and_tick_epoch_utc', source='BROKER_TICKS_AND_DEALS')


def run(mt5, limit=2, now=None):
    now = now or datetime.now(timezone.utc)
    ledger = read_json(DATA / 'confirmed_mt5_outcomes.json', {})
    orders_path = DATA / 'mt5_order_memory.csv'
    with orders_path.open() if orders_path.exists() else io.StringIO('') as stream:
        orders = {r.get('ticket'): r for r in csv.DictReader(stream, delimiter=';') if r.get('status') == 'ENVIADA'}
    processed = []
    if not mt5.initialize():
        return {'ok': False, 'error': 'MT5_UNAVAILABLE'}
    try:
        account = mt5.account_info()
        positions = mt5.positions_get()
        if account is None or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO or positions is None:
            return {'ok': False, 'error': 'DEMO_AND_POSITION_HISTORY_REQUIRED'}
        account_key = f'{account.server}:{account.login}'
        open_ids = {int(getattr(p, 'identifier', p.ticket)) for p in positions}
        rows = [r for r in ledger.values() if r.get('source') == 'MT5_DEMO_REAL'
                and r.get('setup_version') == VERSION and r.get('account_key') == account_key
                and r.get('position_id') and int(r['position_id']) not in open_ids]
        rows.sort(key=lambda r: r.get('data_fechamento', ''), reverse=True)
        for row in rows:
            path = DATA / 'trade_quality' / (cache_key(row)+'.json')
            previous = read_json(path, {})
            if previous.get('completed'):
                continue
            if previous.get('retry_after_epoch', 0) > now.timestamp():
                continue
            attempts = int(previous.get('attempts', 0))+1
            try:
                order = orders.get(str(row.get('order_ticket')), {})
                measured_row = dict(row, entrada=order.get('entrada'),
                                    stop=order.get('stop') or row.get('stop'),
                                    tp2=order.get('tp') or row.get('tp2'))
                value = measure(mt5, measured_row)
            except Exception as error:
                value = {'status': 'MEASUREMENT_UNAVAILABLE', 'error_type': type(error).__name__, 'mfe_r': None, 'mae_r': None}
                if previous.get('status') == 'OBSERVED_TICKS':
                    value = dict(previous, last_attempt_error=type(error).__name__)
            completed = (value.get('status') == 'OBSERVED_TICKS' and value.get('post_exit_window_elapsed')
                         and value.get('collection_reason') == 'REQUESTED_END_REACHED') or attempts >= 3
            value.update(policy='observed_tick_quality_v1', order_ticket=row.get('order_ticket'),
                         updated_at=now.isoformat(), attempts=attempts, completed=bool(completed),
                         retry_after_epoch=now.timestamp()+900,
                         completion_reason='ATTEMPT_LIMIT' if attempts >= 3 else 'COLLECTED' if completed else 'RETRY_PENDING')
            atomic_json(path, value)
            processed.append({'ticket': row.get('order_ticket'), 'status': value['status'],
                              'mfe_r': value.get('mfe_r'), 'mae_r': value.get('mae_r')})
            if len(processed) >= limit:
                break
        atomic_json(DATA / 'quality_collector_status.json', {'updated_at': now.isoformat(), 'processed': processed, 'ok': True})
        return {'ok': True, 'processed': processed}
    finally:
        mt5.shutdown()


if __name__ == '__main__':
    import mt5_safe as mt5
    result = run(mt5)
    print(json.dumps(result, allow_nan=False))
    raise SystemExit(0 if result.get('ok') else 1)
