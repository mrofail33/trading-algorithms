from contextlib import closing
from decimal import Decimal as D
from pathlib import Path
import csv
import sqlite3
import tempfile
import unittest
from reconcile import reconcile, fifo, validate, export
from demo import dataset

def row(**kw):
    return dict(dict(exec_id='A', account='SIM', symbol='XYZ', side='BUY', quantity='10',
                     price='100', fee='1', multiplier='1', trade_date='2026-10-20'), **kw)

class ReconciliationTests(unittest.TestCase):
    def test_exact_match(self):
        self.assertEqual(reconcile([row()], [row()])['matched'], 1)
    def test_missing(self):
        self.assertEqual(reconcile([row()], [])['breaks'][0]['issue'], 'missing_clearing')
    def test_extra(self):
        self.assertEqual(reconcile([], [row()])['breaks'][0]['issue'], 'clearing_only')
    def test_each_mismatch_field(self):
        for field, value in dict(account='B',symbol='OTHER',side='SELL',quantity='11',price='101',fee='2',multiplier='100',trade_date='2026-10-21').items():
            with self.subTest(field=field):
                self.assertEqual(reconcile([row()], [row(**{field:value})])['breaks'][0]['fields'],field)
    def test_tolerance_inside(self):
        self.assertEqual(reconcile([row()], [row(price='100.004')])['matched'],1)
    def test_tolerance_boundary(self):
        self.assertEqual(reconcile([row()], [row(price='100.005')])['matched'],1)
    def test_tolerance_outside(self):
        self.assertEqual(len(reconcile([row()], [row(price='100.006')])['breaks']),1)
    def test_duplicate_clearing_quarantines_both(self):
        r = reconcile([row()], [row(),row()])
        self.assertEqual((r['matched'],len(r['breaks']),len(r['validation_issues'])),(0,0,2))
    def test_duplicate_execution(self):
        self.assertEqual(len(reconcile([row(),row()], [row()])['validation_issues']),2)
    def test_invalid_numeric(self):
        for value in ['NaN','Infinity','-1','bad']:
            with self.subTest(value=value): self.assertIsNotNone(validate(row(price=value)))
    def test_zero_quantity(self): self.assertIsNotNone(validate(row(quantity='0')))
    def test_fractional_quantity(self): self.assertIsNotNone(validate(row(quantity='1.5')))
    def test_bad_side(self): self.assertIsNotNone(validate(row(side='BID')))
    def test_bad_date(self): self.assertIsNotNone(validate(row(trade_date='2026-02-30')))
    def test_missing_field(self): self.assertIsNotNone(validate(row(account='')))
    def test_empty(self): self.assertEqual(reconcile([],[])['matched'],0)
    def test_partial_fills_match_by_exec_not_order(self):
        e=[row(exec_id='F1',quantity='2'),row(exec_id='F2',quantity='8')]
        self.assertEqual(reconcile(e,list(reversed(e)))['matched'],2)
    def test_full_long_pnl_after_fees(self):
        p=fifo([row(),row(exec_id='B',side='SELL',price='110')])[0]
        self.assertEqual(D(p['realized_pnl']),D('98'))
        self.assertEqual(D(p['position']),0)
    def test_short_cover(self):
        p=fifo([row(side='SELL',price='110'),row(exec_id='B')])[0]
        self.assertEqual(D(p['realized_pnl']),98)
    def test_option_multiplier(self):
        p=fifo([row(multiplier='100'),row(exec_id='B',side='SELL',price='101',multiplier='100')])[0]
        self.assertEqual(D(p['realized_pnl']),998)
    def test_partial_close_fee_allocation(self):
        p=fifo([row(),row(exec_id='B',side='SELL',quantity='4',price='110',fee='0.4')])[0]
        self.assertEqual((D(p['realized_pnl']),D(p['position']),D(p['deferred_open_fees'])),(D('39.2'),D('6'),D('0.6')))
    def test_fifo_lot_order(self):
        p=fifo([row(quantity='1',fee='0'),row(exec_id='B',quantity='1',price='120',fee='0'),row(exec_id='C',side='SELL',quantity='1',price='130',fee='0')])[0]
        self.assertEqual(D(p['realized_pnl']),30)
    def test_position_reversal(self):
        p=fifo([row(quantity='1',fee='0'),row(exec_id='B',side='SELL',quantity='3',price='110',fee='0')])[0]
        self.assertEqual((D(p['position']),D(p['realized_pnl'])),(-2,10))
    def test_account_isolation(self): self.assertEqual(len(fifo([row(),row(exec_id='B',account='B',side='SELL')])),2)
    def test_contract_isolation(self): self.assertEqual(len(fifo([row(),row(exec_id='B',symbol='XYZ-PUT',side='SELL')])),2)
    def test_invalid_fifo_rejected(self):
        with self.assertRaises(ValueError): fifo([row(),row()])
    def test_inconsistent_multiplier(self):
        with self.assertRaises(ValueError): fifo([row(),row(exec_id='B',multiplier='100')])
    def test_large_dataset_expected_breaks(self):
        e,c=dataset(); result=reconcile(e,c)
        self.assertEqual((len(e),len(c),result['matched'],len(result['breaks']),len(result['validation_issues'])),(2000,2010,1900,90,30))
        self.assertEqual(sum(x['issue']=='field_mismatch' for x in result['breaks']),70)
    def test_repeatable(self): self.assertEqual(dataset(),dataset())
    def test_csv_sqlite_exports(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            summary=export(*dataset(),tmp)
            with closing(sqlite3.connect(Path(tmp)/'reports.sqlite')) as c:
                self.assertEqual(c.execute('select count(*) from exceptions').fetchone()[0],summary['exception_rows'])
            with open(Path(tmp)/'exceptions.csv',newline='') as f:
                self.assertEqual(len(list(csv.DictReader(f))),90)

if __name__ == '__main__': unittest.main(verbosity=2)
