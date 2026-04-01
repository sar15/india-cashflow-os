from datetime import date, timedelta
import unittest

from cashflow_os.api.store import build_demo_forecast_input
from cashflow_os.domain.models import (
    BankBalanceSnapshot,
    CanonicalCashEvent,
    EntityType,
    EventType,
    ForecastInput,
    OrganizationProfile,
)
from cashflow_os.forecast.engine import build_forecast_run
from cashflow_os.reports.builder import build_report_pack
from cashflow_os.domain.models import ImportBatch, ReportPack, SourceType


class ReportingTestCase(unittest.TestCase):
    def test_aging_heatmaps_bucket_future_events_by_distance(self):
        as_of_date = date(2026, 4, 1)
        forecast_input = ForecastInput(
            profile=OrganizationProfile(org_id="org-1", company_name="Audit Test Industries"),
            as_of_date=as_of_date,
            opening_balance=BankBalanceSnapshot(
                org_id="org-1",
                as_of_date=as_of_date,
                balance_minor_units=0,
            ),
            events=[
                CanonicalCashEvent(
                    org_id="org-1",
                    source_id="test",
                    import_batch_id="batch-1",
                    event_type=EventType.INFLOW,
                    entity_type=EntityType.INVOICE,
                    document_number="INV-31-45",
                    due_date=as_of_date + timedelta(days=40),
                    gross_minor_units=10000,
                    net_minor_units=10000,
                ),
                CanonicalCashEvent(
                    org_id="org-1",
                    source_id="test",
                    import_batch_id="batch-1",
                    event_type=EventType.OUTFLOW,
                    entity_type=EntityType.BILL,
                    document_number="BILL-46-60",
                    due_date=as_of_date + timedelta(days=50),
                    gross_minor_units=20000,
                    net_minor_units=20000,
                ),
            ],
        )

        report_pack = build_report_pack(build_forecast_run(forecast_input))
        ar_chart = next(chart for chart in report_pack.charts if chart.title == "AR Aging Heatmap")
        ap_chart = next(chart for chart in report_pack.charts if chart.title == "AP Due Calendar")

        self.assertEqual(ar_chart.series[0].values, [0.0, 0.0, 100.0, 0.0, 0.0])
        self.assertEqual(ap_chart.series[0].values, [0.0, 0.0, 0.0, 200.0, 0.0])

    def test_build_report_pack_requires_weekly_buckets(self):
        run = build_forecast_run(build_demo_forecast_input())
        with self.assertRaisesRegex(ValueError, "weekly bucket"):
            build_report_pack(run.model_copy(update={"weekly_buckets": []}))

    def test_report_pack_charts_include_trace_points(self):
        report_pack = build_report_pack(build_forecast_run(build_demo_forecast_input()))

        weekly_chart = next(chart for chart in report_pack.charts if chart.title == "13-Week Cash Balance")
        weekly_trace_points = weekly_chart.meta["trace_points"]
        self.assertEqual(len(weekly_trace_points), len(weekly_chart.x_axis))
        self.assertEqual(weekly_trace_points[0]["label"], "Week 1")

        concentration_chart = next(chart for chart in report_pack.charts if chart.title == "Customer Concentration")
        self.assertEqual(len(concentration_chart.meta["trace_points"]), len(concentration_chart.x_axis))
        self.assertTrue(all("summary" in point for point in concentration_chart.meta["trace_points"]))

    def test_timestamp_defaults_are_timezone_aware(self):
        self.assertIsNotNone(ImportBatch(org_id="org-1", source_type=SourceType.MANUAL, filename="import.csv").created_at.tzinfo)
        self.assertIsNotNone(ReportPack(forecast_run_id="run-1", title="Test Report").generated_at.tzinfo)


if __name__ == "__main__":
    unittest.main()
