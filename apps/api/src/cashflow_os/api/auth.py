import json
import os
from functools import lru_cache
from typing import Optional

from fastapi import Header, HTTPException, status
from pydantic import BaseModel


class AuthPrincipal(BaseModel):
    org_id: str
    role: str
    token_name: str


DEFAULT_TOKEN_REGISTRY = {
    "demo-owner-token": AuthPrincipal(org_id="demo-org", role="owner", token_name="Demo Owner"),
    "demo-finance-token": AuthPrincipal(org_id="demo-org", role="finance_manager", token_name="Demo Finance Manager"),
    "demo-accountant-token": AuthPrincipal(org_id="demo-org", role="accountant", token_name="Demo Accountant"),
    "demo-viewer-token": AuthPrincipal(org_id="demo-org", role="viewer", token_name="Demo Viewer"),
}


def demo_auth_enabled() -> bool:
    return os.getenv("CASHFLOW_DISABLE_DEMO_AUTH", "").strip().lower() not in {"1", "true", "yes"}


@lru_cache(maxsize=1)
def load_token_registry() -> dict[str, AuthPrincipal]:
    registry = {} if not demo_auth_enabled() else dict(DEFAULT_TOKEN_REGISTRY)
    raw_registry = os.getenv("CASHFLOW_AUTH_TOKENS_JSON")
    if not raw_registry:
        return registry

    payload = json.loads(raw_registry)
    if not isinstance(payload, dict):
        raise RuntimeError("CASHFLOW_AUTH_TOKENS_JSON must be a JSON object keyed by token.")

    registry.update(
        {
            token: AuthPrincipal.model_validate(
                {
                    "token_name": config.get("token_name") or config.get("name") or token,
                    **config,
                }
            )
            for token, config in payload.items()
        }
    )
    return registry


def _extract_token(authorization: Optional[str], x_api_key: Optional[str]) -> Optional[str]:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            return token.strip()
    if x_api_key:
        return x_api_key.strip()
    return None


def get_current_principal(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> AuthPrincipal:
    token = _extract_token(authorization, x_api_key)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API credentials.",
        )

    principal = load_token_registry().get(token)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API credentials.",
        )
    return principal


def require_roles(*roles: str):
    def dependency(
        authorization: Optional[str] = Header(default=None),
        x_api_key: Optional[str] = Header(default=None),
    ) -> AuthPrincipal:
        principal = get_current_principal(authorization=authorization, x_api_key=x_api_key)
        if roles and principal.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return principal

    return dependency


def ensure_org_access(principal: AuthPrincipal, org_id: str) -> None:
    if principal.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this organization.",
        )
