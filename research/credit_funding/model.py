"""Daily research assessments and monthly cash stress; never a trading control."""
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd


def aware(value):
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp) or timestamp.tzinfo is None:
        raise ValueError('Explicit timezone-aware timestamp required.')
    return timestamp.tz_convert('UTC')


def number(value, name, minimum=None):
    if isinstance(value, (bool, np.bool_, str)) or value is None:
        raise ValueError(f'{name} must be a finite number.')
    result = float(value)
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        raise ValueError(f'Invalid {name}.')
    return result


def eligible_records(records, asof):
    now = aware(asof)
    result = []
    for record in records:
        available = aware(record['eligible_at'])
        if not record.get('source_url') or not record.get('availability_basis'):
            raise ValueError('Source and availability basis required.')
        published = pd.Timestamp(record['published_on']).date()
        if available.tz_convert('America/New_York').date() < published:
            raise ValueError('Availability precedes publication.')
        if available <= now:
            result.append(record)
    return sorted(result, key=lambda r: aware(r['eligible_at']))


def funding_assessment(document, asof, max_age_days=180):
    now = aware(asof)
    if number(max_age_days,'fundamental maximum age',0) == 0:
        raise ValueError('Positive fundamental maximum age required.')
    if len({r['issuer'] for key in ['fundamentals','financing_events'] for r in document[key]}) != 1:
        raise ValueError('Assess one issuer at a time; do not mix company disclosures.')
    financials = eligible_records(document['fundamentals'], now)
    events = eligible_records(document['financing_events'], now)
    result = {'funding_state': 'UNKNOWN', 'historical_investment_gap_usdm': None,
              'financing_access': 'NO_QUALIFIED_EVENT', 'renewal_exposure': False,
              'current_usable_cash': None, 'forward_funding_gap': None,
              'forward_model_status': 'UNKNOWN_REQUIRES_POOL_SPECIFIC_MONTHLY_INPUTS',
              'default_probability': None, 'asof_utc': now.isoformat()}
    if financials:
        # A late amendment to an old period must not supersede newer accounts.
        # For the same period, use the latest version actually available as of now.
        latest = max(financials,key=lambda r:(pd.Timestamp(r['period_end']),aware(r['eligible_at'])))
        age = (now.tz_convert('America/New_York').date()-pd.Timestamp(latest['period_end']).date()).days
        if age < 0:
            raise ValueError('Financial period ends after decision.')
        result['fundamental_age_days'] = age
        if age <= max_age_days:
            gap = number(latest['cash_capex_h1'], 'capex', 0)-number(latest['operating_cash_flow_h1'], 'OCF')
            result['historical_investment_gap_usdm'] = gap
            result['funding_state'] = 'FUNDING_VULNERABILITY' if gap > 0 and number(latest['debt_principal'], 'debt', 0) > 0 else 'NO_RULE_FLAG'
        else:
            result['reason'] = 'Stale financial period; current condition unknown.'
    recent = [e for e in events if (now-aware(e['eligible_at'])).total_seconds() <= max_age_days*86400]
    result['event_ids'] = [e['event_id'] for e in recent]
    if any(e['kind'] == 'completed_financing' for e in recent):
        result['financing_access'] = 'RECENT_COMPLETED_FINANCING'
    elif any(e['kind'] == 'committed_facility' for e in recent):
        result['financing_access'] = 'COMMITTED_FACILITY_ANNOUNCED'
    result['renewal_exposure'] = any(e.get('loan_term_years', 0) > e.get('average_contract_years', float('inf')) for e in recent)
    if result['renewal_exposure']:
        result['funding_state'] = 'FUNDING_VULNERABILITY'
    return result


def credit_assessment(rows, asof, *, kind='issuer', history=20, persistence=3,
                      widening_bp=100., relative_bp=50., max_age_days=4, max_gap_days=4):
    """Require comparable OAS observations and a fixed prior reference window.

    Input rows describe one fixed issuer curve/peer basket, or one broad index.
    Repeated prints cannot masquerade as persistent days. No yield-as-OAS fallback.
    """
    if (kind not in {'issuer', 'broad'} or isinstance(history,bool) or isinstance(persistence,bool)
            or not isinstance(history,(int,np.integer)) or not isinstance(persistence,(int,np.integer))
            or history < 2 or persistence < 1):
        raise ValueError('Invalid credit policy.')
    for value,name in [(widening_bp,'widening threshold'),(relative_bp,'relative threshold'),
                       (max_age_days,'maximum age'),(max_gap_days,'maximum gap')]:
        if number(value,name,0) == 0:
            raise ValueError('Positive credit thresholds and freshness limits required.')
    now = aware(asof)
    def result(**fields):
        return dict(asof_utc=now.isoformat(),kind=kind,**fields)
    available = []
    for row in rows:
        released, observed = aware(row['eligible_at']), aware(row['observed_at'])
        if released < observed:
            raise ValueError('Credit observation available before it existed.')
        if released > now:
            continue
        if row.get('qualified') is not True or row.get('spread_kind') != 'OAS_BP' or not row.get('comparison_id'):
            return result(state='UNKNOWN',reason='Unqualified or incompatible spread measurement.')
        number(row['spread_bp'], 'spread')
        if kind == 'issuer':
            number(row['peer_spread_bp'], 'peer spread')
        available.append(row)
    available.sort(key=lambda r: aware(r['observed_at']))
    dates = [aware(r['observed_at']).tz_convert('America/New_York').date() for r in available]
    if len(dates) != len(set(dates)):
        raise ValueError('One qualified aggregate per observation day required.')
    if len(available) < history+persistence:
        return result(state='UNKNOWN',reason='Insufficient qualified prior history and persistence.',observations=len(available))
    selected = available[-history-persistence:]
    if len({r['comparison_id'] for r in selected}) != 1:
        return result(state='UNKNOWN',reason='Instrument/peer basket changed.')
    ages = [(aware(b['observed_at'])-aware(a['observed_at'])).total_seconds()/86400 for a,b in zip(selected, selected[1:])]
    if max(ages) > max_gap_days or (now-aware(selected[-1]['observed_at'])).total_seconds() > max_age_days*86400:
        return result(state='UNKNOWN',reason='Stale or discontinuous credit observations.')
    reference, recent = selected[:history], selected[history:]
    base = float(np.median([r['spread_bp'] for r in reference]))
    changes = [r['spread_bp']-base for r in recent]
    relative = None
    stress = all(value >= widening_bp for value in changes)
    if kind == 'issuer':
        residual = float(np.median([r['spread_bp']-r['peer_spread_bp'] for r in reference]))
        relative = [r['spread_bp']-r['peer_spread_bp']-residual for r in recent]
        stress = stress and all(value >= relative_bp for value in relative)
    return result(state=('ACTIVE_ISSUER_STRESS' if kind == 'issuer' else 'BROAD_CREDIT_STRESS') if stress else 'NO_RULE_FLAG',
            widening_bp=changes,peer_relative_bp=relative,reference_end=reference[-1]['observed_at'],
            persistence_observations=persistence,
            reason='Untuned research threshold; not a probability or trading instruction.')


def assessment_state(assessment, now, kind):
    """Do not reuse stale, future, untyped or unstamped assessment objects."""
    allowed={'UNKNOWN','NO_RULE_FLAG','ACTIVE_ISSUER_STRESS' if kind=='issuer' else 'BROAD_CREDIT_STRESS'}
    if (not isinstance(assessment,dict) or assessment.get('kind')!=kind
            or not assessment.get('asof_utc') or assessment.get('state') not in allowed):
        return 'UNKNOWN'
    return assessment['state'] if aware(assessment['asof_utc'])==aware(now) else 'UNKNOWN'


def combine_assessments(funding, issuer, broad, sector_states=None, equity_breadth=None,
                        sector_min=3, sector_fraction=.5, weak_fraction=.6):
    """Independent dimensions; issuer distress never implies a bearish index."""
    now=aware(funding['asof_utc'])
    if isinstance(sector_min,bool) or not isinstance(sector_min,(int,np.integer)) or sector_min<1:
        raise ValueError('Positive integer sector coverage required.')
    for value in [sector_fraction,weak_fraction]:
        if not 0<number(value,'breadth threshold')<=1:
            raise ValueError('Breadth thresholds must be in (0,1].')
    issuer_state=assessment_state(issuer,now,'issuer')
    credit_state=assessment_state(broad,now,'broad')
    sector_states = sector_states or {}
    states=[assessment_state(s,now,'issuer') for s in sector_states.values()]
    known = [s for s in states if s in {'ACTIVE_ISSUER_STRESS','NO_RULE_FLAG'}]
    sector = 'UNKNOWN'
    if len(known) == len(sector_states) and len(known) >= sector_min:
        sector = 'SECTOR_STRESS' if known.count('ACTIVE_ISSUER_STRESS')/len(known) >= sector_fraction else 'NO_RULE_FLAG'
    broad_state = 'UNKNOWN'
    # Breadth must come from a separately qualified same-decision-time input.
    if equity_breadth is not None:
        observed, released = aware(equity_breadth['observed_at']), aware(equity_breadth['eligible_at'])
        if released < observed:
            raise ValueError('Breadth available before observation.')
        qualified = (equity_breadth.get('qualified') is True and observed <= released <= now
                     and (now-observed).total_seconds() <= 86400)
        breadth = number(equity_breadth['weak_fraction'], 'qualified equity breadth', 0)
        if breadth > 1:
            raise ValueError('Breadth must be a fraction.')
        if qualified and credit_state != 'UNKNOWN':
            broad_state = 'BROAD_MARKET_STRESS' if credit_state == 'BROAD_CREDIT_STRESS' and breadth >= weak_fraction else 'NO_RULE_FLAG'
    action = 'REVIEW_ISSUER_EXPOSURE' if issuer_state == 'ACTIVE_ISSUER_STRESS' else 'WATCH_FUNDING' if funding['funding_state'] == 'FUNDING_VULNERABILITY' else 'INSUFFICIENT_EVIDENCE' if funding['funding_state'] == 'UNKNOWN' else 'NO_RULE_FLAG'
    return {'asof_utc':now.isoformat(),'funding_state': funding['funding_state'], 'issuer_credit_state': issuer_state,
            'sector_state': sector, 'broad_market_state': broad_state, 'research_action': action,
            'credit_input_rule':'All component assessments must be typed and evaluated at the same decision timestamp.',
            'trading_permission': 'NOT_CONNECTED', 'default_probability': None}


@dataclass(frozen=True)
class FundingScenario:
    name: str = 'baseline'
    floating_rate_shock_bp: float = 0.
    refinancing_rate_shock_bp: float = 0.
    discretionary_capex_fraction: float = 1.
    committed_access_fraction: float = 1.
    collateral_capacity_fraction: float = 1.


CASH_COLUMNS = ['operating_cash_flow', 'mandatory_capex', 'discretionary_capex',
                'principal_due', 'finance_lease_principal', 'other_nonoperating_payments',
                'unhedged_floating_balance', 'refinanced_fixed_balance', 'additional_receipt_shortfall']


def funding_path(monthly, initial_cash, facilities, scenario=FundingScenario(), *,
                 cash_pool, currency='USD', units='millions', ocf_includes_interest_and_operating_leases=True):
    """One explicitly usable cash pool; missing forward schedules are not estimated.

    OCF includes baseline interest/operating leases; rate shocks are incremental.
    Floating and refinanced-fixed balances must be disjoint monthly exposures.
    No credit-line interest is inferred: include it in supplied OCF or incremental
    exposures. These are conditional cash scenarios, not a full debt pricing model.
    """
    if not cash_pool or currency != 'USD' or units != 'millions' or ocf_includes_interest_and_operating_leases is not True:
        raise ValueError('Explicit USD-million cash pool and net-OCF convention required.')
    if list(monthly.columns) != CASH_COLUMNS or not isinstance(monthly.index, pd.DatetimeIndex) or monthly.index.tz is not None:
        raise ValueError('Explicit monthly cash schema and naive month-end index required.')
    if not 1 <= len(monthly) <= 24 or not monthly.index.equals(pd.date_range(monthly.index[0], periods=len(monthly), freq='ME')):
        raise ValueError('Unique consecutive month ends required (1 to 24 months).')
    if not monthly.index.is_month_end.all() or not monthly.index.equals(monthly.index.normalize()):
        raise ValueError('Finite complete month-end forecast required.')
    monthly=monthly.apply(lambda column: column.map(lambda value:number(value,'monthly forecast')))
    if (monthly.drop(columns='operating_cash_flow') < 0).any().any():
        raise ValueError('Payments and exposure balances cannot be negative.')
    cash = number(initial_cash, 'usable initial cash', 0)
    for field in ['discretionary_capex_fraction','committed_access_fraction','collateral_capacity_fraction']:
        if not 0 <= number(getattr(scenario,field),field) <= 1:
            raise ValueError('Scenario capacity/spending fractions must be within [0,1].')
    for field in ['floating_rate_shock_bp','refinancing_rate_shock_bp']:
        number(getattr(scenario,field),field,0)
    capacities = {}
    for facility in facilities:
        key = facility['id']
        if not isinstance(key,str) or not key or key in capacities or facility['cash_pool'] != cash_pool or facility.get('qualified_drawable') is not True:
            raise ValueError('Unique, verified drawable same-pool facilities required.')
        start,end = pd.Timestamp(facility['drawable_from']),pd.Timestamp(facility['expires_on'])
        if (pd.isna(start) or pd.isna(end) or start.tzinfo is not None or end.tzinfo is not None
                or start!=start.normalize() or end!=end.normalize() or start > end):
            raise ValueError('Invalid facility availability dates.')
        capacities[key] = number(facility['capacity'], 'facility capacity', 0)*scenario.committed_access_fraction*scenario.collateral_capacity_fraction
    # Deterministic liquidity-preserving convention; not a cost-optimal treasury plan.
    facilities=sorted(facilities,key=lambda f:(pd.Timestamp(f['expires_on']),f['id']))
    rows = []
    for day,row in monthly.iterrows():
        start = day.replace(day=1)
        interest = (row.unhedged_floating_balance*scenario.floating_rate_shock_bp+row.refinanced_fixed_balance*scenario.refinancing_rate_shock_bp)/10000*day.days_in_month/365
        payments = row.mandatory_capex+row.discretionary_capex*scenario.discretionary_capex_fraction+row.principal_due+row.finance_lease_principal+row.other_nonoperating_payments+interest
        opening = cash
        cash += row.operating_cash_flow-row.additional_receipt_shortfall-payments
        draw = 0.
        # Require availability throughout the month. Intra-month timing is not modelled.
        for facility in facilities:
            if pd.Timestamp(facility['drawable_from']) <= start and pd.Timestamp(facility['expires_on']) >= day:
                amount = min(max(0.,-cash), capacities[facility['id']])
                capacities[facility['id']] -= amount
                draw += amount
                cash += amount
        rows.append({'month':day, 'opening_cash':opening, 'net_ocf_after_shortfall':row.operating_cash_flow-row.additional_receipt_shortfall,
                     'cash_payments':payments, 'incremental_interest':interest, 'committed_draw':draw,
                     'closing_cash':cash, 'unfunded_gap':max(0.,-cash),
                     'remaining_nominal_capacity':sum(capacities.values()),
                     'drawable_capacity':sum(capacities[f['id']] for f in facilities
                         if pd.Timestamp(f['drawable_from'])<=start and pd.Timestamp(f['expires_on'])>=day)})
    result = pd.DataFrame(rows).set_index('month')
    # Independent cumulative reconciliation prevents repeated counting of cash or draws.
    expected = initial_cash+(result.net_ocf_after_shortfall-result.cash_payments+result.committed_draw).cumsum()
    if not np.allclose(expected,result.closing_cash,atol=1e-10):
        raise RuntimeError('Cash accounting failed reconciliation.')
    result.attrs.update(scenario=scenario.name, cash_pool=cash_pool, currency=currency, units=units,
        peak_funding_gap=float(result.unfunded_gap.max()), evidence='Conditional monthly scenario; intra-month shortfalls may be hidden. Not a default forecast.')
    return result
