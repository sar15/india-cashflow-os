"""Parser for Zoho Books JSON export payloads.

Handles uploaded ``{ invoices: [...], bills: [...] }`` JSON files
that users export from Zoho Books.  This is a **file parser**, not
an API client — it never makes network requests.
"""

from datetime import date

from cashflow_os.utils.dates import today_ist
from typing import Dict, List

from cashflow_os.domain.models import (
    BankBalanceSnapshot,
    CanonicalCashEvent,
    Counterparty,
    EntityType,
    EventType,
    ImportBatch,
    ImportIssue,
    ParsedImportBundle,
    RelationshipType,
    Severity,
    SourceType,
)
from cashflow_os.ingestion.errors import FileParseError
from cashflow_os.utils.dates import parse_date_value
from cashflow_os.utils.money import to_minor_units


def parse_zoho_payload(org_id: str, filename: str, payload: Dict) -> ParsedImportBundle:
    batch = ImportBatch(org_id=org_id, source_type=SourceType.ZOHO_EXPORT, filename=filename)
    counterparties: Dict[str, Counterparty] = {}
    issues = []
    events: List[CanonicalCashEvent] = []
    bank_balance_amount = payload.get("bank_balance") or payload.get("cash_balance") or 0
    bank_balance = BankBalanceSnapshot(org_id=org_id, as_of_date=today_ist(), balance_minor_units=to_minor_units(bank_balance_amount))

    for index, invoice in enumerate(payload.get("invoices", []), start=1):
        try:
            customer_name = invoice.get("customer_name") or invoice.get("customer_name_formatted") or "Zoho Customer"
            counterparty = counterparties.get(customer_name)
            if counterparty is None:
                counterparty = Counterparty(entity_name=customer_name, relationship_type=RelationshipType.CUSTOMER)
                counterparties[customer_name] = counterparty
            amount = to_minor_units(invoice.get("balance") or invoice.get("total") or 0)
            tds_amount = to_minor_units(invoice.get("tds_amount") or 0)
            document_date = parse_date_value(invoice.get("date"))
            due_date = parse_date_value(invoice.get("due_date"))
            if invoice.get("date") and document_date is None:
                issues.append(
                    ImportIssue(
                        code="invalid_date",
                        severity=Severity.WARNING,
                        message="Invoice row {row} contains an invalid date.".format(row=index),
                        row_number=index,
                        field_name="date",
                    )
                )
            if invoice.get("due_date") and due_date is None:
                issues.append(
                    ImportIssue(
                        code="invalid_date",
                        severity=Severity.WARNING,
                        message="Invoice row {row} contains an invalid due date.".format(row=index),
                        row_number=index,
                        field_name="due_date",
                    )
                )
            events.append(
                CanonicalCashEvent(
                    org_id=org_id,
                    source_id="zoho.books",
                    import_batch_id=batch.import_batch_id,
                    event_type=EventType.INFLOW,
                    entity_type=EntityType.INVOICE,
                    counterparty_id=counterparty.counterparty_id,
                    counterparty_name=counterparty.entity_name,
                    document_number=str(invoice.get("invoice_number") or invoice.get("invoice_id")),
                    document_date=document_date,
                    due_date=due_date,
                    gross_minor_units=amount,
                    tax_minor_units=to_minor_units(invoice.get("tax_amount") or 0),
                    tds_minor_units=tds_amount,
                    net_minor_units=max(amount - tds_amount, 0),
                    notes="Imported from Zoho Books export file",
                )
            )
        except FileParseError:
            raise
        except Exception as inv_exc:
            raise FileParseError(
                "Invoice {index}: {error}".format(index=index, error=str(inv_exc)),
                filename=filename,
                row_number=index,
            ) from inv_exc

    for index, bill in enumerate(payload.get("bills", []), start=1):
        try:
            vendor_name = bill.get("vendor_name") or bill.get("vendor_name_formatted") or "Zoho Vendor"
            counterparty = counterparties.get(vendor_name)
            if counterparty is None:
                counterparty = Counterparty(entity_name=vendor_name, relationship_type=RelationshipType.VENDOR)
                counterparties[vendor_name] = counterparty
            amount = to_minor_units(bill.get("balance") or bill.get("total") or 0)
            document_date = parse_date_value(bill.get("date"))
            due_date = parse_date_value(bill.get("due_date"))
            if bill.get("date") and document_date is None:
                issues.append(
                    ImportIssue(
                        code="invalid_date",
                        severity=Severity.WARNING,
                        message="Bill row {row} contains an invalid date.".format(row=index),
                        row_number=index,
                        field_name="date",
                    )
                )
            if bill.get("due_date") and due_date is None:
                issues.append(
                    ImportIssue(
                        code="invalid_date",
                        severity=Severity.WARNING,
                        message="Bill row {row} contains an invalid due date.".format(row=index),
                        row_number=index,
                        field_name="due_date",
                    )
                )
            events.append(
                CanonicalCashEvent(
                    org_id=org_id,
                    source_id="zoho.books",
                    import_batch_id=batch.import_batch_id,
                    event_type=EventType.OUTFLOW,
                    entity_type=EntityType.BILL,
                    counterparty_id=counterparty.counterparty_id,
                    counterparty_name=counterparty.entity_name,
                    document_number=str(bill.get("bill_number") or bill.get("bill_id")),
                    document_date=document_date,
                    due_date=due_date,
                    gross_minor_units=amount,
                    net_minor_units=amount,
                    notes="Imported from Zoho Books export file",
                )
            )
        except FileParseError:
            raise
        except Exception as bill_exc:
            raise FileParseError(
                "Bill {index}: {error}".format(index=index, error=str(bill_exc)),
                filename=filename,
                row_number=index,
            ) from bill_exc

    batch.event_count = len(events)
    batch.counterparty_count = len(counterparties)
    batch.unresolved_issues = issues
    return ParsedImportBundle(
        import_batch=batch,
        bank_balance=bank_balance,
        counterparties=list(counterparties.values()),
        events=events,
    )
