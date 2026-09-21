"""Prospective M15 order-block detection and closed-M5 lifecycle; no orders."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib

from src.interest_zone_engine import InterestZoneStore, build_zone_from_context, monitor_zone, validate_zone_for_execution

SOURCE = 'REAL_M15_OB_V1'


def _clock(value):
    return datetime.fromisoformat(str(value).replace('Z','+00:00'))


def detect_zone(symbol, m15, m5, smc, *, now=None):
    """Last opposing candle before a recent displaced BOS; no historical retest."""
    now = now or datetime.now(timezone.utc)
    closed = m15[:-1]
    event = smc.get('bos_event') or smc.get('choch_event') or {}
    shift = not smc.get('bos_event') and bool(smc.get('choch_event'))
    direction = event.get('direction') if shift else smc.get('direction')
    i = event.get('index')
    if (direction not in ('BULLISH','BEARISH') or not isinstance(i,int)
            or i < 1 or i >= len(closed) or len(closed)-1-i > 4 or len(m5)<2):
        return None, 'NO_RECENT_BOS'
    buy = direction=='BULLISH'
    if (event.get('type') != ('CHOCH_' if shift else 'BOS_')+direction or event.get('direction') != direction
            or event.get('displacement') is not True or event.get('time') != closed[i].get('time')):
        return None, 'BOS_WITHOUT_VERIFIABLE_DISPLACEMENT'
    level = event.get('level')
    if level is None or not (closed[i]['close']>level if buy else closed[i]['close']<level):
        return None, 'BOS_PRICE_NOT_BROKEN'
    j = next((j for j in range(i-1,max(-1,i-9),-1)
              if (closed[j]['close']<closed[j]['open'] if buy else closed[j]['close']>closed[j]['open'])),None)
    if j is None:
        return None, 'NO_OPPOSING_ORIGIN_CANDLE'
    origin = closed[j]
    low,high = float(origin['low']),float(origin['high'])
    if high<=low or not (closed[i]['close']>high if buy else closed[i]['close']<low):
        return None, 'BOS_HAS_NOT_LEFT_ORIGIN'
    # Exclude the BOS candle itself; only subsequent observations can be retests.
    bos_end = _clock(closed[i]['time']) + timedelta(minutes=15)
    after = [c for c in m5 if _clock(c['time'])>=bos_end]
    if any(c['low']<=high and c['high']>=low for c in after):
        return None, 'RETEST_ALREADY_OCCURRED_BEFORE_REGISTRATION'
    price = float(m5[-1]['close'])
    if not (price>high if buy else price<low):
        return None, 'PRICE_NOT_OUTSIDE_PLANNED_ZONE'
    event_id = hashlib.sha256(f'{symbol}|{event["time"]}|{direction}|{level}'.encode()).hexdigest()[:24]
    targets = [float(p['price']) for p in smc.get('pivots',[])
               if (p.get('type')=='HIGH' if buy else p.get('type')=='LOW')]
    context = {'region':dict(region_low=low,region_high=high,region_direction=direction,
                            region_type=direction+'_ORDER_BLOCK',source_timeframe='M15',
                            source_module='real_zone_cycle',zone_source=SOURCE,source_event_id=event_id,
                            source_structure_id=event_id,source_reason='Opposing origin candle followed by displaced '+('CHOCH' if shift else 'BOS'),
                            invalidation_price=low if buy else high,target_prices=targets),
               'smc':dict(direction=direction,order_block_valid=True,displacement_present=True)}
    zone = build_zone_from_context({'symbol':symbol,'candle_timestamp':origin['time']},context,
                                   current_price=price,reject_retroactive=True)
    if zone is None:
        return None, 'CANONICAL_BUILD_REJECTED'
    zone.update(created_at=now.isoformat(),updated_at=now.isoformat(),
                expires_at=(now+timedelta(hours=4)).isoformat(),
                observed_after_m5=str(m5[-1]['time']),last_processed_m5=str(m5[-1]['time']),
                source_bos=deepcopy(event),origin_candle=deepcopy(origin),
                structure_model='CHOCH_RETEST' if shift else 'BOS_RETEST',
                structural_confirmations=[],valid_confirmations=[],
                monitor_timeline=[dict(event='ZONE_REGISTERED_BEFORE_RETEST',observed_at=now.isoformat(),
                                       broker_bar=str(m5[-1]['time']))])
    return zone,'REAL_ZONE_REGISTERED'


def advance_zone(zone, m5, smc, *, now=None):
    """Process only bars beginning after registration; terminal states never revive."""
    now = now or datetime.now(timezone.utc)
    z = deepcopy(zone)
    if z.get('zone_source')!=SOURCE or z.get('region_status') in ('INVALIDADA','EXPIRADA','CANCELADA','CONSUMIDA'):
        return z
    buy = z['region_direction']=='BULLISH'
    low,high,stop = z['region_low'],z['region_high'],z['invalidation_price']
    events = smc.get('events') or []
    opposite = any(e.get('direction') != z['region_direction'] and
                   str(e.get('time',''))>str(z['source_bos']['time']) for e in events)
    z = monitor_zone(z,current_price=m5[-1]['close'],now=now,
                     evidence={'region_invalidated':opposite,'invalidation_reason':'OPPOSITE_STRUCTURE_AFTER_ORIGIN'} if opposite else {})
    if z.get('region_status') in ('INVALIDADA','EXPIRADA'):
        return z
    if zone.get('region_status')=='CONFIRMADA':
        z['region_status']='CONFIRMADA'
    boundary = z['observed_after_m5']
    last = z.get('last_processed_m5',boundary)
    for candle in m5[:-1]:
        timestamp = str(candle['time'])
        if timestamp<=boundary or timestamp<=last:
            continue
        z['last_processed_m5']=timestamp
        if candle['low']<=stop if buy else candle['high']>=stop:
            z.update(region_status='INVALIDADA',region_valid=False,region_invalidated=True,
                     invalidation_reason='CLOSED_BAR_CROSSED_ZONE_INVALIDATION',monitoring_enabled=False,
                     invalidated_at=now.isoformat())
            z['monitor_timeline'].append(dict(event='INVALIDATED',broker_bar=timestamp,observed_at=now.isoformat()))
            break
        touched = candle['low']<=high and candle['high']>=low
        if touched and not z.get('touch_broker_bar'):
            z['touch_broker_bar']=timestamp
            z['touch_timestamp']=now.isoformat()
            z['monitor_timeline'].append(dict(event='REAL_RETEST',broker_bar=timestamp,observed_at=now.isoformat(),
                                             low=candle['low'],high=candle['high']))
            z['region_status']='AGUARDANDO_CONFIRMACAO'
        reaction = (candle['close']>candle['open'] and candle['close']>(low+high)/2 if buy else
                    candle['close']<candle['open'] and candle['close']<(low+high)/2)
        if touched and reaction and not z.get('structural_confirmations'):
            confirmation = dict(type='OB_RETEST_DEFENSE',event_id=z['source_event_id']+':'+timestamp,
                                source=SOURCE,source_bos=z['source_bos'],retest_candle=deepcopy(candle),
                                registered_after_bar=boundary,observed_at=now.isoformat())
            z.update(region_status='CONFIRMADA',structural_confirmations=[confirmation],
                     valid_confirmations=[confirmation],confirmation_history=[confirmation],
                     confirmation_broker_bar=timestamp,expires_at=(now+timedelta(minutes=3)).isoformat())
            z['monitor_timeline'].append(dict(event='RETEST_DEFENSE_CONFIRMED',broker_bar=timestamp,observed_at=now.isoformat()))
    z['monitor_timeline']=z.get('monitor_timeline',[])[-100:]
    z['monitoring_state']=z['region_status']
    z['state_machine_state']=z['region_status']
    z['updated_at']=now.isoformat()
    return z


def run_real_zone_cycle(symbol, m15, m5, smc, *, store=None, now=None):
    store=store or InterestZoneStore()
    now=now or datetime.now(timezone.utc)
    if len(m5)<2:
        return dict(created=0,active=0,confirmed_region=None,reason='NO_M5_DATA')
    zones=[z for z in store.list() if z.get('zone_source')==SOURCE and z.get('symbol')==symbol]
    active=[]
    for zone in zones:
        if zone.get('pre_operation_id') or zone.get('region_status') in ('INVALIDADA','EXPIRADA','CANCELADA','CONSUMIDA'):
            continue
        updated=advance_zone(zone,m5,smc,now=now)
        store.upsert(updated)
        if updated.get('region_valid') and updated.get('region_status') not in ('INVALIDADA','EXPIRADA'):
            active.append(updated)
    candidate,reason=detect_zone(symbol,m15,m5,smc,now=now)
    created=0
    if candidate is not None and not store.get(candidate['region_id']):
        active.append(store.upsert(candidate));created=1
    confirmed=None
    for z in reversed(active):
        # A missed historical reaction is not a current entry opportunity.
        if z.get('confirmation_broker_bar')!=str(m5[-2]['time']):
            continue
        check=validate_zone_for_execution({'region_id':z['region_id'],'ativo':symbol},store=store)
        if check.get('ok'):
            confirmed=check['region'];break
    return dict(created=created,active=len(active),confirmed_region=confirmed,reason=reason)
