import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ZohoConfigurationError(RuntimeError):
    pass


class ZohoApiError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ZohoConfigurationError("{name} is required for live Zoho OAuth.".format(name=name))
    return value


def _accounts_server_url(override: Optional[str] = None) -> str:
    value = (override or os.getenv("ZOHO_ACCOUNTS_SERVER_URL") or "https://accounts.zoho.com").strip()
    return value.rstrip("/")


def _api_base_url(override: Optional[str] = None) -> str:
    value = (override or os.getenv("ZOHO_API_BASE_URL") or "https://www.zohoapis.com").strip()
    return value.rstrip("/")


def _parse_json_response(response) -> Dict:
    payload = response.read().decode("utf-8")
    if not payload:
        return {}
    return json.loads(payload)


def _http_request(method: str, url: str, *, headers: Optional[Dict[str, str]] = None, body: Optional[bytes] = None) -> Dict:
    request = Request(url, data=body, method=method, headers=headers or {})
    try:
        with urlopen(request, timeout=30) as response:
            return _parse_json_response(response)
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise ZohoApiError("Zoho request failed ({status}): {body}".format(status=exc.code, body=response_body)) from exc
    except URLError as exc:
        raise ZohoApiError("Unable to reach Zoho: {reason}".format(reason=exc.reason)) from exc


def _token_request(form_fields: Dict[str, str], *, accounts_server: Optional[str] = None) -> Dict:
    body = urlencode(form_fields).encode("utf-8")
    return _http_request(
        "POST",
        "{base}/oauth/v2/token".format(base=_accounts_server_url(accounts_server)),
        headers={"content-type": "application/x-www-form-urlencoded"},
        body=body,
    )


def build_zoho_authorization_url(state: str, redirect_uri: str) -> str:
    client_id = _get_required_env("ZOHO_CLIENT_ID")
    scopes = os.getenv(
        "ZOHO_SCOPES",
        "ZohoBooks.invoices.READ,ZohoBooks.bills.READ,ZohoBooks.contacts.READ,ZohoBooks.settings.READ",
    ).strip()
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scopes,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
    )
    return "{base}/oauth/v2/auth?{query}".format(base=_accounts_server_url(), query=query)


def exchange_zoho_authorization_code(code: str, redirect_uri: str, *, accounts_server: Optional[str] = None) -> Dict:
    token_payload = _token_request(
        {
            "grant_type": "authorization_code",
            "client_id": _get_required_env("ZOHO_CLIENT_ID"),
            "client_secret": _get_required_env("ZOHO_CLIENT_SECRET"),
            "redirect_uri": redirect_uri,
            "code": code,
        },
        accounts_server=accounts_server,
    )
    return normalize_token_payload(token_payload, accounts_server=accounts_server)


def refresh_zoho_access_token(refresh_token: str, *, accounts_server: Optional[str] = None) -> Dict:
    token_payload = _token_request(
        {
            "grant_type": "refresh_token",
            "client_id": _get_required_env("ZOHO_CLIENT_ID"),
            "client_secret": _get_required_env("ZOHO_CLIENT_SECRET"),
            "refresh_token": refresh_token,
        },
        accounts_server=accounts_server,
    )
    return normalize_token_payload(token_payload, accounts_server=accounts_server, refresh_token=refresh_token)


def normalize_token_payload(payload: Dict, *, accounts_server: Optional[str] = None, refresh_token: Optional[str] = None) -> Dict:
    expires_in = int(payload.get("expires_in") or payload.get("expires_in_sec") or 3600)
    return {
        "access_token": payload.get("access_token"),
        "refresh_token": payload.get("refresh_token") or refresh_token,
        "token_type": payload.get("token_type", "Bearer"),
        "api_domain": payload.get("api_domain") or _api_base_url(),
        "accounts_server": _accounts_server_url(accounts_server),
        "scope": payload.get("scope"),
        "expires_in": expires_in,
        "expires_at": (_utc_now() + timedelta(seconds=max(expires_in - 60, 0))).isoformat(),
    }


def token_is_expired(token_payload: Optional[Dict]) -> bool:
    if not token_payload or not token_payload.get("expires_at"):
        return True
    try:
        expires_at = datetime.fromisoformat(str(token_payload["expires_at"]))
    except ValueError:
        return True
    return expires_at <= _utc_now()


def list_zoho_organizations(access_token: str, *, api_domain: Optional[str] = None) -> List[Dict]:
    payload = _http_request(
        "GET",
        "{base}/books/v3/organizations".format(base=_api_base_url(api_domain)),
        headers={"Authorization": "Zoho-oauthtoken {token}".format(token=access_token)},
    )
    return list(payload.get("organizations") or [])


def choose_default_organization(organizations: List[Dict]) -> Optional[Dict]:
    if not organizations:
        return None
    default_org = next((org for org in organizations if org.get("is_default_org")), None)
    return default_org or organizations[0]


def _fetch_paginated_collection(access_token: str, *, api_domain: str, organization_id: str, endpoint: str, response_key: str) -> List[Dict]:
    items: List[Dict] = []
    page = 1
    per_page = 200

    while True:
        query = urlencode({"organization_id": organization_id, "page": page, "per_page": per_page})
        payload = _http_request(
            "GET",
            "{base}/books/v3/{endpoint}?{query}".format(base=_api_base_url(api_domain), endpoint=endpoint, query=query),
            headers={"Authorization": "Zoho-oauthtoken {token}".format(token=access_token)},
        )
        batch = list(payload.get(response_key) or [])
        items.extend(batch)
        page_context = payload.get("page_context") or {}
        if not page_context:
            if len(batch) < per_page:
                break
        elif not page_context.get("has_more_page"):
            break
        page += 1

    return items


def fetch_zoho_import_payload(access_token: str, *, api_domain: str, organization_id: str) -> Dict:
    invoices = _fetch_paginated_collection(
        access_token,
        api_domain=api_domain,
        organization_id=organization_id,
        endpoint="invoices",
        response_key="invoices",
    )
    bills = _fetch_paginated_collection(
        access_token,
        api_domain=api_domain,
        organization_id=organization_id,
        endpoint="bills",
        response_key="bills",
    )
    return {
        "bank_balance": 0,
        "invoices": invoices,
        "bills": bills,
    }


def fetch_contacts(access_token: str, *, api_domain: str, organization_id: str) -> List[Dict]:
    """Fetch all contacts (customers + vendors) from Zoho Books.

    Returns the raw Zoho contact list, which can be used for
    counterparty enrichment and MSME status detection.
    """
    return _fetch_paginated_collection(
        access_token,
        api_domain=api_domain,
        organization_id=organization_id,
        endpoint="contacts",
        response_key="contacts",
    )


_MSME_CUSTOM_FIELD_LABELS = frozenset({
    "msme", "msme_registered", "is_msme", "msme_status",
    "udyam", "udyam_registered", "micro_small_medium",
})


def _is_msme_from_contact(contact: Dict) -> bool:
    """Detect MSME registration from Zoho custom fields or notes.

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
    """Enrich counterparty records with MSME status from Zoho contacts.

    Matches on contact_name vs entity_name (case-insensitive).
    Returns updated counterparty dicts with is_msme_registered set.
    """
    contact_msme_map: Dict[str, bool] = {}
    for contact in contacts:
        name = str(contact.get("contact_name") or contact.get("company_name") or "").strip().lower()
        if name:
            contact_msme_map[name] = _is_msme_from_contact(contact)

    enriched = []
    for cp in counterparties:
        cp_copy = dict(cp)
        entity_name = str(cp_copy.get("entity_name") or "").strip().lower()
        if entity_name in contact_msme_map:
            cp_copy["is_msme_registered"] = contact_msme_map[entity_name]
        enriched.append(cp_copy)
    return enriched
