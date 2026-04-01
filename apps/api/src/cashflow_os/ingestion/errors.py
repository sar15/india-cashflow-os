"""Custom exceptions for the ingestion pipeline.

This module exists separately from service.py to avoid circular imports
between the service dispatcher and the individual parsers.
"""

from typing import Optional


class FileParseError(Exception):
    """Raised when a file cannot be parsed due to malformed data.

    Carries structured context (filename, row, column, message) so the
    API layer can return an actionable HTTP 400 to the client.
    """

    def __init__(
        self,
        message: str,
        *,
        filename: Optional[str] = None,
        row_number: Optional[int] = None,
        column_name: Optional[str] = None,
    ):
        self.filename = filename
        self.row_number = row_number
        self.column_name = column_name
        super().__init__(message)
