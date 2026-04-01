"""Tests for sparkline SVG generation.

Validates that sparkline generators produce valid SVG output
from integer minor-unit financial data without using floats
for money calculations.
"""

import pytest

from cashflow_os.reports.sparklines import (
    build_kpi_sparklines,
    sparkline_bar_svg,
    sparkline_svg,
)


class TestSparklineSVG:

    def test_basic_line_sparkline_returns_svg(self):
        values = [100000, 120000, 115000, 130000, 125000]
        result = sparkline_svg(values)
        assert result.startswith("<svg")
        assert "</svg>" in result
        assert "polyline" in result

    def test_sparkline_contains_stroke_color(self):
        values = [50000, 60000, 55000]
        result = sparkline_svg(values, stroke_color="#ff0000")
        assert "#ff0000" in result

    def test_sparkline_with_fill(self):
        values = [100, 200, 150, 300]
        result = sparkline_svg(values, fill=True)
        assert "polygon" in result

    def test_sparkline_without_fill(self):
        values = [100, 200, 150, 300]
        result = sparkline_svg(values, fill=False)
        assert "polygon" not in result

    def test_empty_values_returns_dashed_line(self):
        result = sparkline_svg([])
        assert "stroke-dasharray" in result

    def test_single_value_returns_dashed_line(self):
        result = sparkline_svg([100000])
        assert "stroke-dasharray" in result

    def test_constant_values_produce_flat_line(self):
        values = [500000] * 5
        result = sparkline_svg(values)
        assert "polyline" in result

    def test_negative_values_handled(self):
        values = [-100000, -50000, -75000, -25000]
        result = sparkline_svg(values)
        assert "polyline" in result

    def test_custom_dimensions(self):
        result = sparkline_svg([100, 200], width=120, height=32)
        assert 'width="120"' in result
        assert 'height="32"' in result


class TestBarSparklineSVG:

    def test_basic_bar_sparkline(self):
        values = [100000, -50000, 75000, -25000]
        result = sparkline_bar_svg(values)
        assert result.startswith("<svg")
        assert "rect" in result

    def test_positive_negative_colors(self):
        values = [100000, -50000]
        result = sparkline_bar_svg(
            values,
            bar_color="#00ff00",
            negative_color="#ff0000",
        )
        assert "#00ff00" in result
        assert "#ff0000" in result

    def test_empty_values_returns_dashed_line(self):
        result = sparkline_bar_svg([])
        assert "stroke-dasharray" in result


class TestBuildKPISparklines:

    def test_produces_all_four_sparklines(self):
        closing = [1000000, 1100000, 1050000, 1200000, 1150000]
        inflow = [500000, 600000, 550000, 700000, 650000]
        outflow = [450000, 500000, 480000, 550000, 520000]
        result = build_kpi_sparklines(closing, inflow, outflow)
        assert "closing_cash" in result
        assert "cash_in" in result
        assert "cash_out" in result
        assert "net_cash_flow" in result

    def test_sparklines_are_svg_strings(self):
        closing = [1000000, 1100000, 1050000]
        inflow = [500000, 600000, 550000]
        outflow = [450000, 500000, 480000]
        result = build_kpi_sparklines(closing, inflow, outflow)
        for key, svg in result.items():
            assert isinstance(svg, str), "Sparkline {key} is not a string".format(key=key)
            assert "<svg" in svg, "Sparkline {key} is not valid SVG".format(key=key)

    def test_uses_correct_colors(self):
        closing = [100, 200, 300]
        inflow = [100, 200, 300]
        outflow = [50, 100, 150]
        result = build_kpi_sparklines(closing, inflow, outflow)
        assert "#0f8b8d" in result["closing_cash"]
        assert "#2cb67d" in result["cash_in"]
        assert "#f07167" in result["cash_out"]
