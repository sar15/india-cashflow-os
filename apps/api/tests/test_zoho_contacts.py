"""Tests for Zoho contact fetching and MSME enrichment.

Validates the counterparty enrichment pipeline that detects
MSME status from Zoho Books contact metadata, custom fields,
and notes.
"""

import pytest

from cashflow_os.ingestion.zoho_client import (
    _is_msme_from_contact,
    enrich_counterparties_from_contacts,
)


class TestIsMSMEFromContact:

    def test_custom_field_true(self):
        contact = {
            "contact_name": "Apex Steel",
            "custom_fields": [
                {"label": "MSME Registered", "value": "Yes"},
            ],
        }
        assert _is_msme_from_contact(contact) is True

    def test_custom_field_false(self):
        contact = {
            "contact_name": "Big Corp",
            "custom_fields": [
                {"label": "MSME Registered", "value": "No"},
            ],
        }
        assert _is_msme_from_contact(contact) is False

    def test_udyam_in_notes(self):
        contact = {
            "contact_name": "Small Works",
            "notes": "UDYAM-MH-01-0012345, registered 2024",
            "custom_fields": [],
        }
        assert _is_msme_from_contact(contact) is True

    def test_msme_in_company_name(self):
        contact = {
            "contact_name": "MSMe Vendor Pvt Ltd",
            "company_name": "MSME Vendor Pvt Ltd",
            "custom_fields": [],
        }
        assert _is_msme_from_contact(contact) is True

    def test_no_msme_indicators(self):
        contact = {
            "contact_name": "Normal Vendor",
            "custom_fields": [],
        }
        assert _is_msme_from_contact(contact) is False

    def test_empty_custom_fields(self):
        contact = {
            "contact_name": "Test",
            "custom_fields": None,
        }
        assert _is_msme_from_contact(contact) is False

    def test_custom_field_registered_value(self):
        contact = {
            "contact_name": "Micro Enterprise",
            "custom_fields": [
                {"label": "Is MSME", "value": "Registered"},
            ],
        }
        assert _is_msme_from_contact(contact) is True

    def test_udyam_label_field(self):
        contact = {
            "contact_name": "Udyam Corp",
            "custom_fields": [
                {"label": "Udyam Registered", "value": "true"},
            ],
        }
        assert _is_msme_from_contact(contact) is True


class TestEnrichCounterpartiesFromContacts:

    def test_enriches_matching_counterparty(self):
        contacts = [
            {
                "contact_name": "Apex Steel",
                "custom_fields": [
                    {"label": "MSME Registered", "value": "Yes"},
                ],
            },
        ]
        counterparties = [
            {"entity_name": "Apex Steel", "is_msme_registered": False},
        ]
        result = enrich_counterparties_from_contacts(contacts, counterparties)
        assert result[0]["is_msme_registered"] is True

    def test_case_insensitive_matching(self):
        contacts = [
            {
                "contact_name": "apex steel",
                "custom_fields": [
                    {"label": "MSME", "value": "Yes"},
                ],
            },
        ]
        counterparties = [
            {"entity_name": "APEX STEEL", "is_msme_registered": False},
        ]
        result = enrich_counterparties_from_contacts(contacts, counterparties)
        assert result[0]["is_msme_registered"] is True

    def test_unmatched_counterparty_unchanged(self):
        contacts = [
            {
                "contact_name": "Some Other Vendor",
                "custom_fields": [
                    {"label": "MSME", "value": "Yes"},
                ],
            },
        ]
        counterparties = [
            {"entity_name": "Apex Steel", "is_msme_registered": False},
        ]
        result = enrich_counterparties_from_contacts(contacts, counterparties)
        assert result[0]["is_msme_registered"] is False

    def test_empty_contacts_returns_unchanged(self):
        counterparties = [
            {"entity_name": "Test Corp", "is_msme_registered": False},
        ]
        result = enrich_counterparties_from_contacts([], counterparties)
        assert result[0]["is_msme_registered"] is False

    def test_does_not_mutate_original(self):
        contacts = [
            {
                "contact_name": "Apex Steel",
                "custom_fields": [{"label": "MSME", "value": "Yes"}],
            },
        ]
        original = {"entity_name": "Apex Steel", "is_msme_registered": False}
        result = enrich_counterparties_from_contacts(contacts, [original])
        assert result[0]["is_msme_registered"] is True
        assert original["is_msme_registered"] is False

    def test_multiple_counterparties_mixed(self):
        contacts = [
            {
                "contact_name": "MSME Vendor A",
                "custom_fields": [{"label": "MSME", "value": "Yes"}],
            },
            {
                "contact_name": "Big Corp B",
                "custom_fields": [{"label": "MSME", "value": "No"}],
            },
        ]
        counterparties = [
            {"entity_name": "MSME Vendor A", "is_msme_registered": False},
            {"entity_name": "Big Corp B", "is_msme_registered": True},
            {"entity_name": "Unknown C", "is_msme_registered": False},
        ]
        result = enrich_counterparties_from_contacts(contacts, counterparties)
        assert result[0]["is_msme_registered"] is True
        assert result[1]["is_msme_registered"] is False
        assert result[2]["is_msme_registered"] is False
