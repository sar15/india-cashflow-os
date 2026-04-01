"""SVG sparkline generators for KPI dashboard cards.

Produces minimal inline SVG strings suitable for embedding in JSON
responses and rendering in the frontend dashboard.  No external
dependencies — pure string generation.

All financial values are accepted as integer minor units (paise)
and converted to display values only for visual scaling.
"""

from typing import List, Optional


def _normalize(values: List[float], *, height: float = 24.0) -> List[float]:
    """Scale values to fit within [0, height]."""
    if not values:
        return []
    min_val = min(values)
    max_val = max(values)
    spread = max_val - min_val
    if spread == 0:
        return [height / 2.0] * len(values)
    return [height - ((v - min_val) / spread) * height for v in values]


def sparkline_svg(
    values: List[int],
    *,
    width: int = 80,
    height: int = 24,
    stroke_color: str = "#0f8b8d",
    stroke_width: float = 1.5,
    fill: bool = True,
    fill_opacity: float = 0.15,
) -> str:
    """Generate a minimal SVG sparkline from integer minor-unit values.

    Args:
        values: List of financial values in minor units (paise).
        width: SVG viewport width in pixels.
        height: SVG viewport height in pixels.
        stroke_color: Line stroke color.
        stroke_width: Line stroke width.
        fill: Whether to add a gradient fill beneath the line.
        fill_opacity: Opacity of the fill area.

    Returns:
        SVG string ready for inline embedding.
    """
    if not values or len(values) < 2:
        return _empty_sparkline(width, height)

    display_values = [v / 100.0 for v in values]
    scaled = _normalize(display_values, height=float(height - 2))
    n = len(scaled)
    step = width / max(n - 1, 1)

    points = []
    for i, y in enumerate(scaled):
        x = round(i * step, 2)
        points.append("{x},{y}".format(x=x, y=round(y + 1, 2)))

    polyline_points = " ".join(points)

    fill_element = ""
    if fill:
        fill_points = "0,{h} ".format(h=height) + polyline_points + " {w},{h}".format(w=width, h=height)
        fill_element = (
            '<polygon points="{pts}" fill="{color}" opacity="{opacity}" />'
        ).format(pts=fill_points, color=stroke_color, opacity=fill_opacity)

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        'preserveAspectRatio="none">'
        '{fill_el}'
        '<polyline points="{pts}" fill="none" '
        'stroke="{color}" stroke-width="{sw}" '
        'stroke-linecap="round" stroke-linejoin="round" />'
        '</svg>'
    ).format(
        w=width,
        h=height,
        fill_el=fill_element,
        pts=polyline_points,
        color=stroke_color,
        sw=stroke_width,
    )
    return svg


def _empty_sparkline(width: int, height: int) -> str:
    """Return a flat-line sparkline for insufficient data."""
    mid = height // 2
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        '<line x1="0" y1="{m}" x2="{w}" y2="{m}" '
        'stroke="#d9e2ec" stroke-width="1" stroke-dasharray="3,3" />'
        '</svg>'
    ).format(w=width, h=height, m=mid)


def sparkline_bar_svg(
    values: List[int],
    *,
    width: int = 80,
    height: int = 24,
    bar_color: str = "#0f8b8d",
    negative_color: str = "#f07167",
) -> str:
    """Generate a bar-style sparkline for values that can be negative.

    Useful for net cash flow where positive/negative distinction matters.
    """
    if not values or len(values) < 2:
        return _empty_sparkline(width, height)

    display_values = [v / 100.0 for v in values]
    max_abs = max(abs(v) for v in display_values) or 1.0
    n = len(display_values)
    bar_width = max(1, (width - n + 1) // n)
    mid_y = height / 2.0

    bars = []
    for i, v in enumerate(display_values):
        x = i * (bar_width + 1)
        bar_height = abs(v) / max_abs * mid_y
        color = bar_color if v >= 0 else negative_color
        if v >= 0:
            y = mid_y - bar_height
        else:
            y = mid_y
        bars.append(
            '<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="{c}" rx="0.5" />'
            .format(x=x, y=round(y, 2), bw=bar_width, bh=round(max(bar_height, 0.5), 2), c=color)
        )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        'preserveAspectRatio="none">'
        '{bars}'
        '</svg>'
    ).format(w=width, h=height, bars="".join(bars))


def build_kpi_sparklines(
    weekly_closing_minor_units: List[int],
    weekly_inflow_minor_units: List[int],
    weekly_outflow_minor_units: List[int],
) -> dict:
    """Build sparkline SVGs for the main dashboard KPI cards.

    Returns a dict keyed by KPI name with SVG strings as values.
    """
    net_flow = [
        inflow - outflow
        for inflow, outflow in zip(weekly_inflow_minor_units, weekly_outflow_minor_units)
    ]

    return {
        "closing_cash": sparkline_svg(
            weekly_closing_minor_units,
            stroke_color="#0f8b8d",
        ),
        "cash_in": sparkline_svg(
            weekly_inflow_minor_units,
            stroke_color="#2cb67d",
        ),
        "cash_out": sparkline_svg(
            weekly_outflow_minor_units,
            stroke_color="#f07167",
        ),
        "net_cash_flow": sparkline_bar_svg(
            net_flow,
            bar_color="#0f8b8d",
            negative_color="#f07167",
        ),
    }
