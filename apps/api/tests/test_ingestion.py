from datetime import date
from io import BytesIO
import unittest

from openpyxl import Workbook

from cashflow_os.ingestion.parsers.manual_template import parse_manual_workbook
from cashflow_os.ingestion.parsers.tally_export import parse_tally_file
from cashflow_os.utils.dates import parse_date_value


class DateParsingTestCase(unittest.TestCase):
    def test_parse_date_value_accepts_supported_formats(self):
        self.assertEqual(parse_date_value("2026-03-31"), date(2026, 3, 31))
        self.assertEqual(parse_date_value("31/03/2026"), date(2026, 3, 31))
        self.assertEqual(parse_date_value("31-Mar-2026"), date(2026, 3, 31))
        self.assertEqual(parse_date_value("31.March.2026"), date(2026, 3, 31))


class ManualTemplateParsingTestCase(unittest.TestCase):
    def test_manual_workbook_records_invalid_dates(self):
        workbook = Workbook()
        setup_sheet = workbook.active
        setup_sheet.title = "Setup"
        setup_sheet.append(["key", "value"])
        setup_sheet.append(["opening_cash_inr", 100000])
        setup_sheet.append(["as_of_date", "31-31-2026"])

        cash_events = workbook.create_sheet("Cash Events")
        cash_events.append(["counterparty", "event_type", "amount_inr", "due_date", "document_number"])
        cash_events.append(["Acme Retail", "inflow", 125000, "2026-99-10", "INV-001"])

        workbook_bytes = BytesIO()
        workbook.save(workbook_bytes)

        bundle = parse_manual_workbook(
            org_id="demo-org",
            filename="manual-template.xlsx",
            file_bytes=workbook_bytes.getvalue(),
        )

        issue_fields = {issue.field_name for issue in bundle.import_batch.unresolved_issues}
        self.assertIn("as_of_date", issue_fields)
        self.assertIn("due_date", issue_fields)


class TallyParsingTestCase(unittest.TestCase):
    def test_tally_xml_parsing_supports_invalid_date_warnings(self):
        xml_payload = b"""
        <ENVELOPE>
          <VOUCHER>
            <NAME>Acme Retail</NAME>
            <DATE>2026-04-05</DATE>
            <DUE_DATE>31/31/2026</DUE_DATE>
            <AMOUNT>1,250.50</AMOUNT>
            <INVOICE_NO>INV-001</INVOICE_NO>
          </VOUCHER>
        </ENVELOPE>
        """

        bundle = parse_tally_file(
            org_id="demo-org",
            filename="receivables.xml",
            file_bytes=xml_payload,
            source_hint="receivables",
        )

        self.assertEqual(len(bundle.events), 1)
        self.assertEqual(bundle.events[0].document_date, date(2026, 4, 5))
        self.assertIsNone(bundle.events[0].due_date)
        self.assertTrue(any(issue.field_name == "due_date" for issue in bundle.import_batch.unresolved_issues))




if __name__ == "__main__":
    unittest.main()
