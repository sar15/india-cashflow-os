from io import BytesIO
from typing import List

import xlsxwriter
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from cashflow_os.domain.models import ForecastRun, KPIValue, ReportPack
from cashflow_os.utils.money import format_inr


def _kpi_table(run: ForecastRun) -> List[List[str]]:
    rows = [["Metric", "Value"]]
    for item in run.kpis.top_kpis[:8]:
        if item.unit == "money":
            value = format_inr(int(item.value))
        else:
            value = str(item.value)
        rows.append([item.label, value])
    return rows


def _line_chart(run: ForecastRun) -> Drawing:
    drawing = Drawing(460, 170)
    chart = HorizontalLineChart()
    chart.x = 35
    chart.y = 30
    chart.height = 110
    chart.width = 380
    chart.data = [[bucket.closing_balance_minor_units / 100.0 for bucket in run.weekly_buckets]]
    chart.categoryAxis.categoryNames = [bucket.label for bucket in run.weekly_buckets]
    chart.lines[0].strokeColor = colors.HexColor("#0f8b8d")
    chart.categoryAxis.labels.angle = 30
    chart.valueAxis.valueMin = min(0, min(bucket.minimum_balance_minor_units for bucket in run.weekly_buckets) / 100.0)
    drawing.add(chart)
    drawing.add(String(40, 150, "13-Week Closing Cash", fontSize=12, fillColor=colors.HexColor("#12344d")))
    return drawing


def _bar_chart(run: ForecastRun) -> Drawing:
    drawing = Drawing(460, 170)
    chart = VerticalBarChart()
    chart.x = 40
    chart.y = 30
    chart.height = 110
    chart.width = 360
    chart.data = [
        [bucket.inflow_minor_units / 100.0 for bucket in run.weekly_buckets],
        [bucket.outflow_minor_units / 100.0 for bucket in run.weekly_buckets],
    ]
    chart.categoryAxis.categoryNames = [bucket.label for bucket in run.weekly_buckets]
    chart.bars[0].fillColor = colors.HexColor("#0f8b8d")
    chart.bars[1].fillColor = colors.HexColor("#f07167")
    chart.categoryAxis.labels.angle = 30
    drawing.add(chart)
    drawing.add(String(40, 150, "Cash In vs Cash Out", fontSize=12, fillColor=colors.HexColor("#12344d")))
    return drawing


def export_pdf(run: ForecastRun, report_pack: ReportPack) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CashflowTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#12344d"),
        spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "CashflowHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0b3c49"),
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "CashflowBody",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#334e68"),
    )

    story = [
        Paragraph(report_pack.title, title_style),
        Paragraph("As of {date} | Scenario: {scenario}".format(date=run.as_of_date.isoformat(), scenario=run.scenario.name), body_style),
        Spacer(1, 0.3 * cm),
        Paragraph("Executive Summary", heading_style),
        Paragraph(report_pack.sections[0].narrative, body_style),
        Spacer(1, 0.2 * cm),
    ]

    table = Table(_kpi_table(run), colWidths=[8.0 * cm, 6.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#12344d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9e2ec")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fbff"), colors.white]),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([table, Spacer(1, 0.4 * cm), _line_chart(run), Spacer(1, 0.3 * cm), _bar_chart(run), Spacer(1, 0.3 * cm)])

    story.append(Paragraph("Top Alerts", heading_style))
    alert_rows = [["Severity", "Title", "Due", "Amount"]]
    for alert in run.alerts[:6]:
        amount = format_inr(alert.amount_minor_units or 0) if alert.amount_minor_units is not None else "-"
        alert_rows.append([alert.severity.value.upper(), alert.title, alert.due_date.isoformat() if alert.due_date else "-", amount])
    alert_table = Table(alert_rows, colWidths=[2.5 * cm, 7.0 * cm, 3.0 * cm, 3.0 * cm])
    alert_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b3c49")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9e2ec")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#fff7ed"), colors.white]),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ]
        )
    )
    story.extend([alert_table, Spacer(1, 0.25 * cm)])

    story.append(Paragraph("Methodology Notes", heading_style))
    for note in report_pack.methodology_notes:
        story.append(Paragraph("• {note}".format(note=note), body_style))

    document.build(story)
    return buffer.getvalue()


def export_excel(run: ForecastRun, report_pack: ReportPack) -> bytes:
    buffer = BytesIO()
    workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
    summary = workbook.add_worksheet("Summary")
    weekly = workbook.add_worksheet("Weekly Forecast")
    alerts_sheet = workbook.add_worksheet("Alerts")
    trace_sheet = workbook.add_worksheet("Audit Trace")

    title_format = workbook.add_format({"bold": True, "font_size": 16, "font_color": "#12344d"})
    header_format = workbook.add_format({"bold": True, "bg_color": "#12344d", "font_color": "white", "border": 1})
    cell_format = workbook.add_format({"border": 1})
    currency_format = workbook.add_format({"border": 1, "num_format": '[$₹-en-IN]#,##0.00'})

    summary.write("A1", report_pack.title, title_format)
    summary.write("A3", "Metric", header_format)
    summary.write("B3", "Value", header_format)
    for row_index, item in enumerate(run.kpis.top_kpis, start=3):
        summary.write(row_index, 0, item.label, cell_format)
        if item.unit == "money":
            summary.write_number(row_index, 1, float(item.value) / 100.0, currency_format)
        else:
            summary.write(row_index, 1, item.value, cell_format)

    weekly_headers = ["Week", "Start", "End", "Opening", "Cash In", "Cash Out", "Net", "Closing", "Minimum"]
    for column_index, label in enumerate(weekly_headers):
        weekly.write(0, column_index, label, header_format)
    for row_index, bucket in enumerate(run.weekly_buckets, start=1):
        weekly.write(row_index, 0, bucket.label, cell_format)
        weekly.write(row_index, 1, bucket.start_date.isoformat(), cell_format)
        weekly.write(row_index, 2, bucket.end_date.isoformat(), cell_format)
        weekly.write_number(row_index, 3, bucket.opening_balance_minor_units / 100.0, currency_format)
        weekly.write_number(row_index, 4, bucket.inflow_minor_units / 100.0, currency_format)
        weekly.write_number(row_index, 5, bucket.outflow_minor_units / 100.0, currency_format)
        weekly.write_number(row_index, 6, bucket.net_movement_minor_units / 100.0, currency_format)
        weekly.write_number(row_index, 7, bucket.closing_balance_minor_units / 100.0, currency_format)
        weekly.write_number(row_index, 8, bucket.minimum_balance_minor_units / 100.0, currency_format)

    line_chart = workbook.add_chart({"type": "line"})
    line_chart.add_series(
        {
            "name": "Closing Cash",
            "categories": ["Weekly Forecast", 1, 0, len(run.weekly_buckets), 0],
            "values": ["Weekly Forecast", 1, 7, len(run.weekly_buckets), 7],
            "line": {"color": "#0f8b8d", "width": 2.25},
        }
    )
    line_chart.set_title({"name": "13-Week Closing Cash"})
    weekly.insert_chart("K2", line_chart)

    bar_chart = workbook.add_chart({"type": "column"})
    bar_chart.add_series(
        {
            "name": "Cash In",
            "categories": ["Weekly Forecast", 1, 0, len(run.weekly_buckets), 0],
            "values": ["Weekly Forecast", 1, 4, len(run.weekly_buckets), 4],
            "fill": {"color": "#0f8b8d"},
        }
    )
    bar_chart.add_series(
        {
            "name": "Cash Out",
            "categories": ["Weekly Forecast", 1, 0, len(run.weekly_buckets), 0],
            "values": ["Weekly Forecast", 1, 5, len(run.weekly_buckets), 5],
            "fill": {"color": "#f07167"},
        }
    )
    bar_chart.set_title({"name": "Weekly Cash In vs Cash Out"})
    weekly.insert_chart("K20", bar_chart)

    alert_headers = ["Severity", "Title", "Message", "Due Date", "Amount"]
    for column_index, label in enumerate(alert_headers):
        alerts_sheet.write(0, column_index, label, header_format)
    for row_index, alert in enumerate(run.alerts, start=1):
        alerts_sheet.write(row_index, 0, alert.severity.value.upper(), cell_format)
        alerts_sheet.write(row_index, 1, alert.title, cell_format)
        alerts_sheet.write(row_index, 2, alert.message, cell_format)
        alerts_sheet.write(row_index, 3, alert.due_date.isoformat() if alert.due_date else "-", cell_format)
        if alert.amount_minor_units is not None:
            alerts_sheet.write_number(row_index, 4, alert.amount_minor_units / 100.0, currency_format)
        else:
            alerts_sheet.write(row_index, 4, "-", cell_format)

    trace_headers = ["Event ID", "Subject", "Explanation", "Effective Date", "Signed Amount"]
    for column_index, label in enumerate(trace_headers):
        trace_sheet.write(0, column_index, label, header_format)
    for row_index, trace in enumerate(run.audit_trace, start=1):
        trace_sheet.write(row_index, 0, trace.event_id, cell_format)
        trace_sheet.write(row_index, 1, trace.subject, cell_format)
        trace_sheet.write(row_index, 2, trace.explanation, cell_format)
        trace_sheet.write(row_index, 3, trace.effective_date.isoformat() if trace.effective_date else "-", cell_format)
        if trace.signed_minor_units is not None:
            trace_sheet.write_number(row_index, 4, trace.signed_minor_units / 100.0, currency_format)
        else:
            trace_sheet.write(row_index, 4, "-", cell_format)

    workbook.close()
    return buffer.getvalue()

