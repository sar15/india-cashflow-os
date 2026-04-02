import unittest

from cashflow_os.api.store import build_demo_forecast_input
from cashflow_os.forecast.engine import build_forecast_run


class ForecastEngineTestCase(unittest.TestCase):
    def setUp(self):
        self.forecast_input = build_demo_forecast_input()
        self.run = build_forecast_run(self.forecast_input)

    def test_generates_13_week_horizon(self):
        self.assertEqual(len(self.run.daily_points), 91)
        self.assertEqual(len(self.run.weekly_buckets), 13)

    def test_cash_conservation_holds(self):
        opening = self.run.daily_points[0].opening_balance_minor_units
        net_movement = sum(point.net_movement_minor_units for point in self.run.daily_points)
        closing = self.run.daily_points[-1].closing_balance_minor_units
        self.assertEqual(opening + net_movement, closing)

    def test_flags_msme_vendor_risk(self):
        msme_alerts = [alert for alert in self.run.alerts if alert.kind == "msme_43b_h"]
        self.assertTrue(msme_alerts)

    def test_builds_kpis(self):
        self.assertIsNotNone(self.run.kpis)
        keys = {item.key for item in self.run.kpis.top_kpis}
        self.assertIn("opening_cash", keys)
        self.assertIn("closing_cash", keys)

    def test_handles_zero_day_horizon(self):
        run = build_forecast_run(self.forecast_input.model_copy(update={"horizon_days": 0}))
        self.assertEqual(run.horizon_days, 1)


if __name__ == "__main__":
    unittest.main()
