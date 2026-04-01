from typing import Dict, Optional

from cashflow_os.domain.models import ParsedImportBundle, SourceType
from cashflow_os.ingestion.manual_template import parse_manual_csv, parse_manual_workbook
from cashflow_os.ingestion.tally import parse_tally_file
from cashflow_os.ingestion.zoho import parse_zoho_payload


def parse_import(
    org_id: str,
    source_type: SourceType,
    filename: str,
    file_bytes: Optional[bytes] = None,
    file_text: Optional[str] = None,
    payload: Optional[Dict] = None,
    source_hint: Optional[str] = None,
) -> ParsedImportBundle:
    if source_type == SourceType.ZOHO:
        return parse_zoho_payload(org_id=org_id, filename=filename, payload=payload or {})

    if source_type == SourceType.TALLY:
        return parse_tally_file(
            org_id=org_id,
            filename=filename,
            file_bytes=file_bytes or (file_text or "").encode("utf-8"),
            source_hint=source_hint or "receivables",
        )

    if filename.lower().endswith(".csv"):
        return parse_manual_csv(org_id=org_id, filename=filename, file_text=file_text or (file_bytes or b"").decode("utf-8"))

    return parse_manual_workbook(org_id=org_id, filename=filename, file_bytes=file_bytes or b"")
