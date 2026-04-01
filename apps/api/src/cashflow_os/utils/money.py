from decimal import Decimal, ROUND_HALF_UP
from typing import Union


PAISE_FACTOR = Decimal("100")


def to_minor_units(value: Union[str, int, float, Decimal]) -> int:
    decimal_value = Decimal(str(value or 0))
    return int((decimal_value * PAISE_FACTOR).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_minor_units(value: int) -> Decimal:
    return (Decimal(value) / PAISE_FACTOR).quantize(Decimal("0.01"))


def scale_minor_units(value: int, basis_points: int) -> int:
    scaled = (Decimal(value) * Decimal(basis_points) / Decimal(10000)).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )
    return int(scaled)


def safe_ratio(numerator: Union[int, Decimal], denominator: Union[int, Decimal]) -> Decimal:
    numerator_decimal = Decimal(str(numerator or 0))
    denominator_decimal = Decimal(str(denominator or 0))
    if denominator_decimal == 0:
        return Decimal("0")
    return (numerator_decimal / denominator_decimal).quantize(Decimal("0.01"))


def parse_indian_number(value: Union[str, int, float, Decimal, None]) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip()
    multiplier = Decimal("1")
    if text.lower().endswith("dr"):
        text = text[:-2].strip()
    elif text.lower().endswith("cr"):
        multiplier = Decimal("-1")
        text = text[:-2].strip()

    cleaned = text.replace(",", "").replace("₹", "").strip()
    if not cleaned:
        return Decimal("0")
    return Decimal(cleaned) * multiplier


def format_inr(value_minor_units: int) -> str:
    sign = "-" if value_minor_units < 0 else ""
    rupees = abs(value_minor_units) // 100
    paise = abs(value_minor_units) % 100
    digits = str(rupees)
    if len(digits) <= 3:
        grouped = digits
    else:
        grouped = digits[-3:]
        digits = digits[:-3]
        parts = []
        while digits:
            parts.append(digits[-2:])
            digits = digits[:-2]
        grouped = ",".join(reversed(parts)) + "," + grouped
    return "{sign}₹{grouped}.{paise:02d}".format(sign=sign, grouped=grouped, paise=paise)

