"""Execution-level reconciliation and fee-adjusted FIFO; synthetic research only."""
from collections import Counter, defaultdict, deque
from contextlib import closing
from decimal import Decimal, InvalidOperation
import csv
import json
from pathlib import Path
import sqlite3
D = Decimal
FIELDS = ('account', 'symbol', 'side', 'quantity', 'price', 'fee', 'multiplier', 'trade_date')

def validate(row):
    try:
        if not all(str(row.get(k, '')).strip() for k in ('exec_id',) + FIELDS):
            return 'missing_field'
        if row['side'] not in ('BUY', 'SELL'):
            return 'invalid_side'
        for key in ('quantity', 'price', 'fee', 'multiplier'):
            value = D(str(row[key]))
            if not value.is_finite():
                return 'nonfinite_number'
            if value < 0 or (key in ('quantity', 'multiplier') and value <= 0):
                return 'invalid_number'
        if D(str(row['quantity'])) != D(str(row['quantity'])).to_integral_value():
            return 'fractional_quantity'
        from datetime import date
        date.fromisoformat(row['trade_date'])
    except (InvalidOperation, ValueError, TypeError):
        return 'invalid_value'
    return None

def index_rows(rows, source):
    counts = Counter(str(r.get('exec_id', '')) for r in rows)
    index, issues = {}, []
    for number, row in enumerate(rows, 1):
        reason = validate(row)
        if reason:
            issues.append(dict(source=source, row=number, exec_id=row.get('exec_id', ''), issue=reason))
        elif counts[row['exec_id']] > 1:
            issues.append(dict(source=source, row=number, exec_id=row['exec_id'], issue='duplicate_id'))
        else:
            index[row['exec_id']] = row
    return index, issues

def reconcile(executions, clearing, price_tolerance=D('0.005')):
    """Quarantine every duplicated ID; never silently overwrite a row."""
    e, ei = index_rows(executions, 'execution')
    c, ci = index_rows(clearing, 'clearing')
    blocked = {r['exec_id'] for r in ei + ci}
    breaks = []
    matched = 0
    for key in sorted((e.keys() | c.keys()) - blocked):
        if key not in c:
            breaks.append(dict(exec_id=key, issue='missing_clearing', fields=''))
        elif key not in e:
            breaks.append(dict(exec_id=key, issue='clearing_only', fields=''))
        else:
            mismatches = []
            for field in FIELDS:
                left, right = e[key][field], c[key][field]
                if field in ('quantity', 'price', 'fee', 'multiplier'):
                    delta = abs(D(str(left)) - D(str(right)))
                    different = delta > (price_tolerance if field == 'price' else D('0'))
                else:
                    different = left != right
                if different:
                    mismatches.append(field)
            if mismatches:
                breaks.append(dict(exec_id=key, issue='field_mismatch', fields=','.join(mismatches)))
            else:
                matched += 1
    return dict(matched=matched, breaks=breaks, validation_issues=ei + ci)

def fifo(rows):
    """Input order is authoritative execution sequence; fees allocated per unit.
    Exact contract symbols/accounts isolated. No expiration, assignment or FX.
    """
    indexed, issues = index_rows(rows, 'execution')
    if issues:
        raise ValueError('Invalid or duplicate execution records')
    lots = defaultdict(deque)
    realized = defaultdict(lambda: D('0'))
    multipliers = {}
    for row in indexed.values():
        key = (row['account'], row['symbol'])
        multiplier = D(str(row['multiplier']))
        if key in multipliers and multipliers[key] != multiplier:
            raise ValueError('Inconsistent contract multiplier')
        multipliers[key] = multiplier
        sign = 1 if row['side'] == 'BUY' else -1
        qty, price, fee = (D(str(row[k])) for k in ('quantity', 'price', 'fee'))
        unit_fee = fee / qty
        queue = lots[key]
        while qty and queue and queue[0][0] != sign:
            old_sign, old_qty, old_price, old_fee = queue[0]
            closed = min(qty, old_qty)
            realized[key] += closed * ((price - old_price) * old_sign * multiplier - old_fee - unit_fee)
            qty -= closed
            queue[0][1] -= closed
            if queue[0][1] == 0:
                queue.popleft()
        if qty:
            queue.append([sign, qty, price, unit_fee])
    return [dict(account=k[0], symbol=k[1], position=str(sum(x[0] * x[1] for x in lots[k])),
                 realized_pnl=str(realized[k]), deferred_open_fees=str(sum(x[1] * x[3] for x in lots[k])))
            for k in sorted(lots)]

def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def export(executions, clearing, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    result = reconcile(executions, clearing)
    accounting = fifo(executions) if not index_rows(executions, 'execution')[1] else []
    write_csv(folder / 'exceptions.csv', result['breaks'], ['exec_id', 'issue', 'fields'])
    write_csv(folder / 'validation.csv', result['validation_issues'], ['source', 'row', 'exec_id', 'issue'])
    write_csv(folder / 'positions.csv', accounting, ['account', 'symbol', 'position', 'realized_pnl', 'deferred_open_fees'])
    with closing(sqlite3.connect(folder / 'reports.sqlite')) as conn, conn:
        for table, data, fields in [('exceptions', result['breaks'], ['exec_id','issue','fields']),
                                     ('validation', result['validation_issues'], ['source','row','exec_id','issue']),
                                     ('positions', accounting, ['account','symbol','position','realized_pnl','deferred_open_fees'])]:
            conn.execute('DROP TABLE IF EXISTS ' + table)
            conn.execute('CREATE TABLE ' + table + ' (' + ','.join(f + ' TEXT' for f in fields) + ')')
            conn.executemany('INSERT INTO ' + table + ' VALUES (' + ','.join('?' for _ in fields) + ')',
                             [[str(r[f]) for f in fields] for r in data])
    summary = dict(execution_rows=len(executions), clearing_rows=len(clearing), matched=result['matched'],
                   exception_rows=len(result['breaks']), validation_rows=len(result['validation_issues']),
                   exception_types=dict(Counter(r['issue'] for r in result['breaks'])),
                   validation_types=dict(Counter(r['issue'] for r in result['validation_issues'])))
    (folder / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary
