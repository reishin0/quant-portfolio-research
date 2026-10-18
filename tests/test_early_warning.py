import unittest
from datetime import datetime
import numpy as np
import pandas as pd
from research.credit_funding import early_warning as ew
from research.credit_funding import early_warning_filings as ef


def bdays(n, start='2024-01-02'):
    return pd.bdate_range(start, periods=n)


class SeriesStateTest(unittest.TestCase):
    def test_requires_every_recent_observation_to_widen(self):
        idx = bdays(30)
        s = pd.Series(3.0, index=idx)
        s.iloc[-3:] = [4.0, 4.1, 4.2]
        state, widen = ew.series_state(s, widening_bp=100)
        self.assertEqual(state.iloc[-1], ew.WARN)
        s.iloc[-2] = 3.5
        state, _ = ew.series_state(s, widening_bp=100)
        self.assertEqual(state.iloc[-1], 'NO_FLAG')

    def test_gap_makes_window_unknown(self):
        idx = list(bdays(22)) + [pd.Timestamp('2024-03-15')]
        s = pd.Series(3.0, index=pd.DatetimeIndex(idx))
        state, _ = ew.series_state(s)
        self.assertEqual(state.iloc[-1], 'UNKNOWN')

    def test_published_next_session_is_strictly_later_and_fresh(self):
        state = pd.Series(['NO_FLAG', ew.WARN], index=pd.to_datetime(['2024-01-02', '2024-01-03']))
        sessions = pd.to_datetime(['2024-01-03', '2024-01-04', '2024-01-12'])
        out = ew.published_next_session(state, sessions)
        self.assertEqual(list(out), ['NO_FLAG', ew.WARN, 'UNKNOWN'])


class EpisodeTest(unittest.TestCase):
    def test_nonoverlapping_onsets_and_recovery(self):
        values = [100.0] * 60 + [79.0, 75.0, 85.0, 91.0, 92.0] + [70.0] + [100.0] * 5
        close = pd.Series(values, index=bdays(len(values)))
        eps = ew.episodes(close)
        self.assertEqual(eps.onset_pos.tolist(), [60, 65])
        self.assertEqual(eps.end_pos.iloc[0], 63)
        self.assertTrue((eps.onset_pos.iloc[1:].to_numpy() > eps.end_pos.iloc[:-1].to_numpy()).all())

    def test_price_drawdown_rearms_only_after_recovery(self):
        values = [100.0] * 60 + [89.0, 88.0, 94.0, 89.0, 96.0, 89.0]
        close = pd.Series(values, index=bdays(len(values)))
        _, p2, known = ew.price_signals(close)
        self.assertEqual(list(np.flatnonzero(p2)), [60, 65])
        self.assertFalse(known.iloc[:59].any())


class ClassificationTest(unittest.TestCase):
    def setUp(self):
        self.eps = pd.DataFrame(dict(onset=[0], end=[0], peak=[0], onset_pos=[30], end_pos=[40]))
        self.sample = pd.Series(True, index=bdays(100))

    def test_kinds(self):
        got = dict((p, k) for p, k, _ in ew.classify([10, 30, 35, 50, 95], self.eps, self.sample))
        self.assertEqual(got, {10: 'HIT', 30: 'SAME_DAY', 35: 'IN_EPISODE', 50: 'FALSE', 95: 'CENSORED'})

    def test_out_of_sample_alarm_is_ignored(self):
        sample = self.sample.copy()
        sample.iloc[10] = False
        self.assertEqual(ew.classify([10], self.eps, sample), [])

    def test_dedup_cooldown(self):
        alarm = pd.Series(False, index=bdays(80))
        alarm.iloc[[5, 6, 7, 20, 45]] = True
        self.assertEqual(ew.dedup(alarm), [5, 45])

    def test_recall_requires_full_eligible_window(self):
        alarm = pd.Series(False, index=bdays(100))
        alarm.iloc[25] = True
        rows = ew.recall(alarm, self.eps, self.sample)
        self.assertEqual(rows[0]['warned'], True)
        self.assertEqual(rows[0]['lead'], 5)
        sample = self.sample.copy()
        sample.iloc[15] = False
        self.assertEqual(ew.recall(alarm, self.eps, sample), [])


class SpreadTest(unittest.TestCase):
    def test_gspread_interpolates_and_keeps_missing_curve_unknown(self):
        bonds = pd.DataFrame(dict(cusip=['X', 'X'], tradeDate=['2024-01-02', '2024-01-03'],
                                  lastSalePrice=[99.0, 98.0], lastSaleYield=[6.0, 6.2]))
        meta = pd.DataFrame(dict(cusip=['X'], maturityDate=['2030-01-02']))
        curve = pd.DataFrame({1: [4.0, np.nan], 2: [4.0, 4.0], 3: [4.0, 4.0], 5: [4.0, 4.0], 7: [5.0, 5.0],
                              10: [5.0, 5.0], 20: [5.0, 5.0], 30: [5.0, 5.0]},
                             index=pd.to_datetime(['2024-01-02', '2024-01-03']))
        _, g = ew.gspread_panel(bonds, meta, curve)
        self.assertAlmostEqual(g.lastSaleYield.iloc[0], 6.0 - (4.0 + (6.0 - 5) / 2 * 1.0), places=2)
        self.assertTrue(np.isnan(g.lastSaleYield.iloc[1]))


class FilingTest(unittest.TestCase):
    def test_acceptance_is_eastern_and_alarm_after_close(self):
        sessions = pd.to_datetime(['2024-05-01', '2024-05-02', '2024-05-03'])
        before = ef.accepted_local('2024-05-01T15:59:00.000Z')
        after = ef.accepted_local('2024-05-01T16:30:00.000Z')
        self.assertEqual(ef.alarm_session(before, sessions), pd.Timestamp('2024-05-01'))
        self.assertEqual(ef.alarm_session(after, sessions), pd.Timestamp('2024-05-02'))

    def facts(self):
        def item(tag, start, end, val, accn, form, filed):
            return tag, dict(start=start, end=end, val=val, accn=accn, form=form, filed=filed)
        rows = [
            item('NetCashProvidedByUsedInOperatingActivities', '2023-01-01', '2023-12-31', 100, 'K', '10-K', '2024-02-20'),
            item('PaymentsToAcquirePropertyPlantAndEquipment', '2023-01-01', '2023-12-31', 80, 'K', '10-K', '2024-02-20'),
            item('NetCashProvidedByUsedInOperatingActivities', '2024-01-01', '2024-06-30', 20, 'Q', '10-Q', '2024-08-01'),
            item('PaymentsToAcquirePropertyPlantAndEquipment', '2024-01-01', '2024-06-30', 90, 'Q', '10-Q', '2024-08-01'),
            item('NetCashProvidedByUsedInOperatingActivities', '2023-01-01', '2023-06-30', 50, 'Q', '10-Q', '2024-08-01'),
            item('PaymentsToAcquirePropertyPlantAndEquipment', '2023-01-01', '2023-06-30', 40, 'Q', '10-Q', '2024-08-01'),
            item('CashAndCashEquivalentsAtCarryingValue', None, '2024-06-30', 10, 'Q', '10-Q', '2024-08-01'),
            item('LongTermDebt', None, '2024-06-30', 500, 'Q', '10-Q', '2024-08-01'),
            item('RestrictedCashCurrent', None, '2024-06-30', 1000, 'Q', '10-Q', '2024-08-01'),
        ]
        body = {}
        for tag, it in rows:
            body.setdefault(tag, {'units': {'USD': []}})['units']['USD'].append(
                {k: v for k, v in it.items() if v is not None})
        return {'facts': {'us-gaap': body}}

    def test_ttm_uses_prior_annual_and_never_counts_restricted_cash(self):
        subs = [{'filings': {'recent': {'accessionNumber': ['K', 'Q'], 'form': ['10-K', '10-Q'],
                                        'acceptanceDateTime': ['2024-02-20T08:00:00.000Z', '2024-08-01T17:00:00.000Z'],
                                        'filingDate': ['2024-02-20', '2024-08-01']}}}]
        sessions = pd.bdate_range('2024-01-02', '2024-12-31')
        recs = {r['accn']: r for r in ef.filing_records('X', self.facts(), subs, sessions)}
        q = recs['Q']
        self.assertEqual(q['ttm_ocf_usd'], 100 + 20 - 50)
        self.assertEqual(q['ttm_capex_usd'], 80 + 90 - 40)
        self.assertEqual(q['F1'], 'FUNDING_WATCH')
        self.assertEqual(q['F2'], 'FUNDING_GAP')
        self.assertEqual(q['alarm_session'], '2024-08-02')
        self.assertEqual(recs['K']['F1'], 'UNKNOWN')  # no debt tag in the annual filing: never assumed safe

    def test_older_period_revision_never_replaces_current_state(self):
        recs = [dict(acceptance_local='2024-08-01T17:00:00-04:00', period_end='2024-06-30'),
                dict(acceptance_local='2024-09-01T09:00:00-04:00', period_end='2024-03-31'),
                dict(acceptance_local='2024-11-01T09:00:00-04:00', period_end='2024-09-30')]
        out = ef.current_only(recs)
        self.assertEqual([r['state_effect'] for r in out], [True, False, True])
        self.assertEqual(out[1]['status'], 'OLDER_PERIOD_REVISION')

    def test_comparative_is_tag_and_accession_specific(self):
        f = ef.facts_frame(self.facts())
        val, _ = ef.same_tag(f, 'PaymentsToAcquirePropertyPlantAndEquipment', 'Q', pd.Timestamp('2023-07-02'), 181)
        self.assertEqual(val, 40)
        self.assertTrue(np.isnan(ef.same_tag(f, 'PaymentsToAcquirePropertyPlantAndEquipment', 'K',
                                             pd.Timestamp('2023-06-30'), 181)[0]))

    def test_stale_filing_state_becomes_unknown(self):
        sessions = pd.bdate_range('2024-01-02', '2024-12-31')
        filings = pd.DataFrame([dict(issuer='X', alarm_session='2024-01-03', period_end='2023-12-31',
                                     F1='FUNDING_WATCH', F2='NO_FLAG')])
        out = ew.funding_states(filings, 'X', sessions)
        self.assertEqual(out.F1.loc['2024-01-02'], 'UNKNOWN')
        self.assertEqual(out.F1.loc['2024-07-01'], 'FUNDING_WATCH')
        self.assertEqual(out.F1.loc['2024-12-31'], 'UNKNOWN')
        self.assertTrue(out.F1_alarm.loc['2024-01-03'])


class DependenceTest(unittest.TestCase):
    def test_permutation_and_bootstrap_are_reproducible(self):
        idx = bdays(300)
        g = pd.DataFrame(index=idx)
        g['m'] = True
        g['S_alarm'] = False
        g.iloc[[50, 150, 250], g.columns.get_loc('S_alarm')] = True
        g.attrs['episodes'] = pd.DataFrame(dict(onset=idx[[60, 160]], end=idx[[70, 170]], peak=1.0,
                                                onset_pos=[60, 160], end_pos=[70, 170]))
        panel = {'A': g}
        period = [str(idx[0].date()), str(idx[-1].date())]
        a = ew.permutation_p(panel, 'S', 'm', period, draws=50)
        b = ew.permutation_p(panel, 'S', 'm', period, draws=50)
        self.assertEqual(a, b)
        self.assertAlmostEqual(a[0], 2 / 3)
        alarms = pd.DataFrame(dict(issuer=['A', 'A'], kind=['HIT', 'FALSE']))
        lo, hi, n = ew.bootstrap_difference(alarms, alarms, ['A'], draws=20)
        self.assertEqual((lo, hi, n), (0.0, 0.0, 20))


if __name__ == '__main__':
    unittest.main()
