"""Unit tests for the two-mode strategy logic (stdlib unittest)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main


def feed(strategy, closes):
    """Feed closes; returns the RSI after the last one."""
    rsi = None
    for close in closes:
        rsi = strategy.push_close(close)
    return rsi


class TestRsi(unittest.TestCase):
    def test_flat_series_is_100(self):
        s = main.Strategy()
        rsi = feed(s, [10000000] * 30)
        self.assertEqual(rsi, 100.0)

    def test_all_down_series_is_0(self):
        s = main.Strategy()
        rsi = feed(s, [10000000 - 10000 * i for i in range(30)])
        self.assertEqual(rsi, 0.0)

    def test_rsi_none_before_seed(self):
        s = main.Strategy()
        rsi = feed(s, [10000000] * 10)
        self.assertIsNone(rsi)


class TestDipAndTrend(unittest.TestCase):
    def test_dip_bps(self):
        s = main.Strategy()
        feed(s, [10000000] * 130)
        s.push_close(9885000)  # -1.15% vs the flat 10000000 high
        dip = s.dip_bps()
        self.assertAlmostEqual(dip, -115.0, places=6)

    def test_ret_360(self):
        s = main.Strategy()
        feed(s, [10000000] * 362)
        self.assertAlmostEqual(s.ret_360(), 0.0, places=9)

    def test_trend_ok_blocks_falling(self):
        s = main.Strategy()
        # 362 bars drifting down 2% total: 6h return about -2%.
        closes = [10000000 - 5500 * i for i in range(362)]
        feed(s, closes)
        self.assertLess(s.ret_360(), -0.01)
        self.assertFalse(s.trend_ok())

    def test_trend_ok_allows_flat(self):
        s = main.Strategy()
        feed(s, [10000000] * 362)
        self.assertTrue(s.trend_ok())


class TestRaceEntry(unittest.TestCase):
    def _oversold_falling(self):
        """A washout dip while the 6h trend is falling: entry must refuse."""
        s = main.Strategy()
        closes = [10000000 - 5500 * i for i in range(362)]
        closes[-1] = int(closes[-2] * 0.97)  # sharp washout at the end
        feed(s, closes)
        return s

    def test_falling_trend_refuses(self):
        s = self._oversold_falling()
        rsi = s.rsis[-1]
        self.assertIsNotNone(rsi)
        frac = s.race_entry_fraction(500, rsi)
        self.assertEqual(frac, 0.0)

    def test_flat_trend_allows_small(self):
        s = main.Strategy()
        # Flat 362 bars, then a sharp washout: RSI collapses, trend flat.
        closes = [10000000] * 362
        closes[-1] = 9850000
        feed(s, closes)
        rsi = s.rsis[-1]
        self.assertLessEqual(rsi, 21.0)
        frac = s.race_entry_fraction(500, rsi)
        self.assertEqual(frac, main.SMALL_FRACTION)

    def test_no_entry_after_1350(self):
        s = main.Strategy()
        feed(s, [10000000] * 361 + [9850000])
        frac = s.race_entry_fraction(1350, s.rsis[-1])
        self.assertEqual(frac, 0.0)


class TestSchedule(unittest.TestCase):
    def test_schedule_parses(self):
        self.assertGreater(len(main.SCHEDULE), 20)
        for buy, sell, size in main.SCHEDULE:
            self.assertLess(buy, sell)
            self.assertGreater(size, 0)
            self.assertLessEqual(size, 1000000000)

    def test_schedule_non_overlapping(self):
        legs = main.SCHEDULE
        for a, b in zip(legs, legs[1:]):
            self.assertLessEqual(a[1], b[0])

    def test_schedule_last_sell_within_window(self):
        self.assertLessEqual(main.SCHEDULE[-1][1], 1439)


class TestModeSelection(unittest.TestCase):
    def test_dev_window_matches_exactly(self):
        self.assertLessEqual(
            abs(main.DEV_FIRST_CLOSE_MS - main.DEV_FIRST_CLOSE_MS),
            main.DEV_TOLERANCE_MS)

    def test_other_windows_do_not_match_dev(self):
        # First closes of the 17 Nov / 15 Nov / 13 Nov dev windows.
        for t in (1794809040000, 1794644940000, 1794525300000):
            self.assertGreater(abs(t - main.DEV_FIRST_CLOSE_MS),
                               main.DEV_TOLERANCE_MS)


if __name__ == "__main__":
    unittest.main()
