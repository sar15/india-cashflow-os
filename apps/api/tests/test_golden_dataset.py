"""
Golden Dataset Test for Cashflow OS.

Verifies that the forecast engine produces deterministic, auditable results
from a fixed input. This is the most critical test: if it fails, financial
outputs cannot be trusted.
"""

from datetime import date

import pytest

from cashflow_os.api.store import build_demo_forecast_input
from cashflow_os.domain.models import (
    ForecastInput,
    ForecastRun,
)
from cashflow_os.forecast.engine import build_forecast_run, build_standard_scenario_runs
from cashflow_os.reports.builder import build_report_pack
from cashflow_os.reports.exporters import export_pdf, export_excel


@pytest.fixture
def demo_input() -> ForecastInput:
    return build_demo_forecast_input()


@pytest.fixture
def demo_run(demo_input: ForecastInput) -> ForecastRun:
    return build_forecast_run(demo_input)


class TestGoldenDatasetProperties:

    def test_opening_plus_net_equals_closing(self, demo_run: ForecastRun):
        """Property: opening + net == closing (fundamental accounting identity)."""
        kpi_map = {}
        for group in [demo_run.kpis.top_kpis, demo_run.kpis.working_capital]:
            for item in group:
                kpi_map[item.key] = item

        opening_kpi = kpi_map.get("opening_cash")
        closing_kpi = kpi_map.get("closing_cash")
        net_kpi = kpi_map.get("net_cash_flow")
        assert opening_kpi and closing_kpi and net_kpi, "Missing core KPIs"

        first_bucket = demo_run.weekly_buckets[0]
        last_bucket = demo_run.weekly_buckets[-1]
        opening = first_bucket.opening_balance_minor_units
        closing = last_bucket.closing_balance_minor_units
        total_inflow = sum(b.inflow_minor_units for b in demo_run.weekly_buckets)
        total_outflow = sum(b.outflow_minor_units for b in demo_run.weekly_buckets)
        net = total_inflow - total_outflow
        assert opening + net == closing, (
            "Accounting identity violated: {o} + {n} != {c}".format(o=opening, n=net, c=closing)
        )

    def test_weekly_buckets_cover_horizon(self, demo_run: ForecastRun):
        total_days = 0
        for bucket in demo_run.weekly_buckets:
            days = (bucket.end_date - bucket.start_date).days + 1
            assert 1 <= days <= 7, "Invalid bucket span: {d} days".format(d=days)
            total_days += days
        assert total_days == demo_run.horizon_days

    def test_weekly_inflow_outflow_sum(self, demo_run: ForecastRun):
        """Sum of weekly inflows minus outflows must equal net movement."""
        total_inflow = sum(b.inflow_minor_units for b in demo_run.weekly_buckets)
        total_outflow = sum(b.outflow_minor_units for b in demo_run.weekly_buckets)
        first_opening = demo_run.weekly_buckets[0].opening_balance_minor_units
        last_closing = demo_run.weekly_buckets[-1].closing_balance_minor_units
        assert first_opening + total_inflow - total_outflow == last_closing

    def test_core_kpis_present(self, demo_run: ForecastRun):
        """Core KPIs from PRD must be present."""
        all_kpis = {}
        for group in [
            demo_run.kpis.top_kpis,
            demo_run.kpis.working_capital,
            demo_run.kpis.manufacturer,
            demo_run.kpis.compliance,
        ]:
            for item in group:
                all_kpis[item.key] = item

        assert len(all_kpis) >= 15, "Expected at least 15 KPIs, got {n}".format(n=len(all_kpis))

    def test_running_balance_monotonic_logic(self, demo_run: ForecastRun):
        for bucket in demo_run.weekly_buckets:
            expected_closing = (
                bucket.opening_balance_minor_units
                + bucket.inflow_minor_units
                - bucket.outflow_minor_units
            )
            assert bucket.closing_balance_minor_units == expected_closing, (
                "Week {w}: {o} + {i} - {out} != {c}".format(
                    w=bucket.week_index,
                    o=bucket.opening_balance_minor_units,
                    i=bucket.inflow_minor_units,
                    out=bucket.outflow_minor_units,
                    c=bucket.closing_balance_minor_units,
                )
            )

    def test_consecutive_bucket_continuity(self, demo_run: ForecastRun):
        for i in range(1, len(demo_run.weekly_buckets)):
            prev_closing = demo_run.weekly_buckets[i - 1].closing_balance_minor_units
            curr_opening = demo_run.weekly_buckets[i].opening_balance_minor_units
            assert prev_closing == curr_opening, (
                "Gap between week {prev} closing and week {curr} opening".format(
                    prev=i, curr=i + 1
                )
            )


class TestGoldenDatasetCompliance:

    def test_compliance_alerts_present(self, demo_run: ForecastRun):
        alert_titles = [a.title for a in demo_run.alerts]
        has_gst = any("GST" in t for t in alert_titles)
        has_tds = any("TDS" in t for t in alert_titles)
        has_epf = any("EPF" in t or "payroll" in t.lower() for t in alert_titles)
        assert has_gst or has_tds or has_epf, "No statutory compliance alerts found."

    def test_audit_trace_not_empty(self, demo_run: ForecastRun):
        assert len(demo_run.audit_trace) > 0


class TestGoldenDatasetScenarios:

    def test_scenario_variants_produce_different_results(self, demo_input: ForecastInput):
        runs = build_standard_scenario_runs(demo_input)
        assert len(runs) >= 2
        base_closing = runs[0].weekly_buckets[-1].closing_balance_minor_units
        stress_closing = runs[1].weekly_buckets[-1].closing_balance_minor_units
        assert base_closing != stress_closing, "Stress must differ from base"

    def test_all_scenario_runs_have_same_event_count(self, demo_input: ForecastInput):
        runs = build_standard_scenario_runs(demo_input)
        event_counts = [len(r.resolved_events) for r in runs]
        assert len(set(event_counts)) == 1


class TestGoldenDatasetReports:

    def test_report_pack_builds(self, demo_run: ForecastRun):
        report = build_report_pack(demo_run)
        assert report.forecast_run_id == demo_run.forecast_run_id
        assert len(report.charts) >= 8
        assert len(report.sections) >= 3

    def test_pdf_export_not_empty(self, demo_run: ForecastRun, tmp_path):
        report = build_report_pack(demo_run)
        out = tmp_path / "test.pdf"
        export_pdf(demo_run, report, out)
        assert out.exists()
        assert out.stat().st_size > 1000

    def test_excel_export_not_empty(self, demo_run: ForecastRun, tmp_path):
        report = build_report_pack(demo_run)
        out = tmp_path / "test.xlsx"
        export_excel(demo_run, report, out)
        assert out.exists()
        assert out.stat().st_size > 1000
