"""MSME detection utilities for Indian counterparty enrichment.

Detects Micro, Small, and Medium Enterprise (MSME) registration status
from contact metadata, custom fields, and free-text notes.  This is
critical for Section 43B(h) compliance alerts in the forecast engine.

Relocated from the former zoho_client module because MSME detection
is a domain utility, not an API-integration concern.
"""

from typing import Dict, List, Optional


_MSME_CUSTOM_FIELD_LABELS = frozenset({
    "msme", "msme_registered", "is_msme", "msme_status",
    "udyam", "udyam_registered", "micro_small_medium",
})


def is_msme_from_contact(contact: Dict) -> bool:
    """Detect MSME registration from contact metadata.

    Checks:
    1. Custom fields with MSME-related labels
    2. Company name or notes containing UDYAM registration numbers
    """
    custom_fields = contact.get("custom_fields") or []
    for field in custom_fields:
        label = str(field.get("label") or "").strip().lower().replace(" ", "_")
        value = str(field.get("value") or "").strip().lower()
        if label in _MSME_CUSTOM_FIELD_LABELS and value in ("true", "yes", "1", "registered"):
            return True

    notes = str(contact.get("notes") or "").upper()
    company = str(contact.get("company_name") or "").upper()
    for text_value in (notes, company):
        if "UDYAM" in text_value or "MSME" in text_value:
            return True

    return False


def enrich_counterparties_from_contacts(
    contacts: List[Dict],
    counterparties: List[Dict],
) -> List[Dict]:
    """Enrich counterparty records with MSME status from contact data.

    Matches on contact_name vs entity_name (case-insensitive).
    Returns updated counterparty dicts with is_msme_registered set.
    """
    contact_msme_map: Dict[str, bool] = {}
    for contact in contacts:
        name = str(contact.get("contact_name") or contact.get("company_name") or "").strip().lower()
        if name:
            contact_msme_map[name] = is_msme_from_contact(contact)

    enriched = []
    for cp in counterparties:
        cp_copy = dict(cp)
        entity_name = str(cp_copy.get("entity_name") or "").strip().lower()
        if entity_name in contact_msme_map:
            cp_copy["is_msme_registered"] = contact_msme_map[entity_name]
        enriched.append(cp_copy)
    return enriched
