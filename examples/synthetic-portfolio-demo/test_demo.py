import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

import demo


class DemoTests(unittest.TestCase):
    def test_offline_and_repeatable(self):
        with patch("socket.socket", side_effect=AssertionError("unexpected network use")):
            first = demo.run_demo()
            second = demo.run_demo()
        pd.testing.assert_frame_equal(first.weights, second.weights)
        pd.testing.assert_frame_equal(first.metrics, second.metrics)
        self.assertListEqual(list(first.weights.index), [f"Asset {c}" for c in "ABCDEFGH"])
        self.assertIn(demo.BENCHMARK, first.metrics.columns)
        self.assertTrue(np.isfinite(first.metrics.to_numpy()).all())

    def test_long_only_fully_invested_and_capped(self):
        weights = demo.run_demo(seed=7).weights
        np.testing.assert_allclose(weights.sum(), 1, atol=1e-7, rtol=0)
        self.assertGreaterEqual(weights.to_numpy().min(), -1e-7)
        self.assertLessEqual(weights.to_numpy().max(), demo.MAX_WEIGHT + 1e-7)

    def test_evaluation_returns_do_not_change_fit(self):
        real = demo.research.load_prices

        def shock_evaluation(*args, **kwargs):
            prices, metadata = real(*args, **kwargs)
            prices = prices.copy()
            prices.iloc[demo.FIT_ROWS + 1:, 0] *= 0.5
            return prices, metadata

        baseline = demo.run_demo()
        with patch.object(demo.research, "load_prices", side_effect=shock_evaluation):
            stressed = demo.run_demo()
        self.assertLess(baseline.fit_end, baseline.evaluation_start)
        pd.testing.assert_frame_equal(baseline.weights, stressed.weights)
        self.assertFalse(baseline.metrics.equals(stressed.metrics))


if __name__ == "__main__":
    unittest.main()
