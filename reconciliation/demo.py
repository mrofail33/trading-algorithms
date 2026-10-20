"""Generate 2,000 synthetic fills and known clearing discrepancies."""
from copy import deepcopy
from pathlib import Path
import json
from reconcile import export, write_csv, FIELDS

def dataset():
    executions = []
    # Two opening and two closing partial fills per independent round trip.
    for n in range(500):
        option = n % 2 == 0
        base = dict(account=f'SIM-{n % 5}', symbol=(f'XYZ261218C{100+n:08d}' if option else f'EQ{n%10}'),
                    multiplier='100' if option else '1', trade_date=f'2026-10-{1+n%20:02d}')
        for leg, (side, price) in enumerate([('BUY','10.00'),('BUY','11.00'),('SELL','12.00'),('SELL','13.00')]):
            executions.append(dict(base, exec_id=f'E{n*4+leg:05d}', side=side, quantity='2', price=price, fee='0.50'))
    clearing = deepcopy(executions)
    clearing = clearing[10:]
    for n in range(10):
        clearing.append(dict(executions[n], exec_id=f'EXTRA{n}'))
    for start, field, value in [(20,'quantity','3'),(40,'price','10.25'),(60,'fee','9.00'),
                                 (80,'side','SELL'),(100,'account','SIM-OTHER'),
                                 (120,'multiplier','50'),(140,'trade_date','2026-11-01')]:
        for n in range(start, start+10):
            row = next(r for r in clearing if r['exec_id'] == f'E{n:05d}')
            row[field] = ('BUY' if row[field] == 'SELL' else 'SELL') if field == 'side' else value
    for n in range(160,170):
        clearing.append(deepcopy(next(r for r in clearing if r['exec_id']==f'E{n:05d}')))
    for n in range(180,190):
        next(r for r in clearing if r['exec_id']==f'E{n:05d}')['price'] = 'NaN'
    return executions, clearing

if __name__ == '__main__':
    root = Path(__file__).parent
    e, c = dataset()
    (root / 'data').mkdir(exist_ok=True)
    write_csv(root / 'data/executions.csv', e, ['exec_id'] + list(FIELDS))
    write_csv(root / 'data/clearing.csv', c, ['exec_id'] + list(FIELDS))
    print(json.dumps(export(e, c, root / 'reports'), indent=2))
