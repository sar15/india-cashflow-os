"""Ingestion service — routes file uploads to the correct parser.

This module is the single entry point for all file-based imports.
It dispatches to the appropriate parser based on SourceType and
filename extension, and defines the FileParseError for structured
error reporting back to the user.
"""

from typing import Dict, Optional

from cashflow_os.domain.models import ParsedImportBundle, SourceType

from cashflow_os.ingestion.errors import FileParseError
from cashflow_os.ingestion.parsers.manual_template import parse_manual_csv, parse_manual_workbook
from cashflow_os.ingestion.parsers.tally_export import parse_tally_file


__all__ = ["FileParseError", "parse_import"]


def parse_import(
    org_id: str,
    source_type: SourceType,
    filename: str,
    file_bytes: Optional[bytes] = None,
    file_text: Optional[str] = None,
    payload: Optional[Dict] = None,
    source_hint: Optional[str] = None,
) -> ParsedImportBundle:
    try:

        if source_type == SourceType.TALLY_EXPORT:
            return parse_tally_file(
                org_id=org_id,
                filename=filename,
                file_bytes=file_bytes or (file_text or "").encode("utf-8"),
                source_hint=source_hint or "receivables",
            )

        if filename.lower().endswith(".csv"):
            return parse_manual_csv(org_id=org_id, filename=filename, file_text=file_text or (file_bytes or b"").decode("utf-8"))

        return parse_manual_workbook(org_id=org_id, filename=filename, file_bytes=file_bytes or b"")

    except FileParseError:
        raise
    except Exception as exc:
        raise FileParseError(
            "Could not parse '{filename}': {error}".format(filename=filename, error=str(exc)),
            filename=filename,
        ) from exc
