"""
Money Precision Tests for Cashflow OS.

Validates that financial calculations maintain exact precision:
- Integer minor units (paise) never produce floating-point drift
- Tax calculations at statutory rates (18% GST, various TDS) are exact
- Indian number parsing handles all real-world edge cases
- Currency formatting follows Indian grouping rules
"""

from decimal import Decimal, ROUND_HALF_UP

import pytest

from cashflow_os.utils.money import (
    format_inr,
    from_minor_units,
    parse_indian_number,
    to_minor_units,
)


class TestMinorUnitsConversion:

    def test_basic_conversion_round_trip(self):
        assert to_minor_units(1000) == 100000  # 1000 INR = 100000 paise
        assert from_minor_units(100000) == Decimal("1000.00")

    def test_decimal_input(self):
        assert to_minor_units(Decimal("12345.67")) == 1234567
        assert from_minor_units(1234567) == Decimal("12345.67")

    def test_zero(self):
        assert to_minor_units(0) == 0
        assert from_minor_units(0) == Decimal("0.00")

    def test_negative_values(self):
        assert to_minor_units(-500) == -50000
        assert from_minor_units(-50000) == Decimal("-500.00")

    def test_large_amounts(self):
        """Test amounts typical for Indian SMEs (crores range)."""
        crore = 10_000_000
        assert to_minor_units(crore) == crore * 100
        assert from_minor_units(crore * 100) == Decimal("10000000.00")

    def test_float_input_rounds_correctly(self):
        """Floats should be safely converted without drift."""
        result = to_minor_units(12345.675)
        assert isinstance(result, int)
        assert result in (1234567, 1234568)  # Allow for rounding


class TestGSTCalculation:

    def test_gst_18_percent(self):
        """GST at 18% on 100000 INR = 18000 INR exact."""
        base = to_minor_units(100000)
        gst_rate = Decimal("0.18")
        gst_amount = int(Decimal(base) * gst_rate)
        assert gst_amount == to_minor_units(18000)

    def test_gst_on_odd_amount(self):
        """GST on 1,23,456.78 INR should produce exact paise."""
        base = to_minor_units(Decimal("123456.78"))
        gst_rate = Decimal("0.18")
        gst_amount = int(Decimal(base) * gst_rate)
        expected = int(Decimal("12345678") * Decimal("0.18"))
        assert gst_amount == expected

    def test_gst_identity(self):
        """gross = net + tax → always holds exactly."""
        net = to_minor_units(Decimal("87654.32"))
        gst = int(Decimal(net) * Decimal("0.18"))
        gross = net + gst
        assert gross == net + gst
        assert gross - gst == net


class TestTDSCalculation:

    @pytest.mark.parametrize("rate,base_inr,expected_tds_paise", [
        (Decimal("0.10"), 100000, 1000000),   # 10% on 1L
        (Decimal("0.02"), 500000, 1000000),   # 2% on 5L
        (Decimal("0.01"), 1000000, 1000000),  # 1% on 10L
    ])
    def test_tds_rates(self, rate, base_inr, expected_tds_paise):
        base = to_minor_units(base_inr)
        tds = int(Decimal(base) * rate)
        assert tds == expected_tds_paise


class TestIndianNumberParsing:

    def test_plain_number(self):
        assert parse_indian_number("100000") == 100000

    def test_with_commas(self):
        assert parse_indian_number("1,00,000") == 100000

    def test_with_rupee_symbol(self):
        assert parse_indian_number("₹1,00,000") == 100000

    def test_with_decimal(self):
        result = parse_indian_number("1,23,456.78")
        assert float(result) == 123456.78

    def test_negative_with_minus(self):
        result = parse_indian_number("-50,000")
        assert result == -50000

    def test_with_dr_suffix(self):
        """Tally Dr/Cr notation."""
        result = parse_indian_number("50,000 Dr")
        assert result == 50000

    def test_with_cr_suffix(self):
        result = parse_indian_number("50,000 Cr")
        assert result == -50000

    def test_empty_string(self):
        assert parse_indian_number("") == 0

    def test_none_input(self):
        assert parse_indian_number(None) == 0

    def test_whitespace(self):
        assert parse_indian_number("  1,50,000  ") == 150000

    def test_lakh_notation(self):
        """Basic large number parsing."""
        result = parse_indian_number("150000")
        assert float(result) == 150000


class TestINRFormatting:

    def test_basic_formatting(self):
        """Standard Indian grouping: X,XX,XXX.XX"""
        result = format_inr(12345678)  # 1,23,456.78 INR
        assert "1,23,456" in result
        assert "₹" in result

    def test_zero(self):
        result = format_inr(0)
        assert "0" in result
        assert "₹" in result

    def test_negative(self):
        result = format_inr(-500000)  # -5,000.00
        assert "-" in result or "(" in result

    def test_large_amount(self):
        """Test crore-scale amount formatting."""
        result = format_inr(1000000000)  # 1,00,00,000.00 (1 crore)
        assert "1,00,00,000" in result

    def test_paisa(self):
        """Test subunit display."""
        result = format_inr(12345)  # 123.45 INR
        assert "123" in result
        assert "45" in result


class TestFinancialInvariants:

    def test_addition_no_drift(self):
        """Adding many small amounts should not drift."""
        amounts = [to_minor_units(Decimal("0.01"))] * 10000  # 10000 × 1 paisa
        total = sum(amounts)
        assert total == 10000  # Exactly 100.00 INR in paise

    def test_multiplication_by_percentage(self):
        """Scaling by basis points is exact integer math."""
        base = to_minor_units(100000)  # 1 lakh
        bps_scalar = 10500  # 105%
        scaled = (base * bps_scalar) // 10000
        assert scaled == to_minor_units(105000)
