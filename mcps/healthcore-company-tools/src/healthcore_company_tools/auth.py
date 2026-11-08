"""Check the existing staff login token with MCP Auth.

mcpauth 0.1.1's built-in ``"jwt"`` mode requires a JWKS URI and only
accepts RS/PS/ES signatures. The staff token is HS256 with the shared
secret, so this module uses the documented custom verifier. That
function checks the signature and the expiry. The bearer middleware
then checks the issuer and the audience.

The same middleware requires the issuer to be a URL, so the fixed
issuer is ``https://healthcore-api``.
"""

from __future__ import annotations

import os

import jwt
from mcpauth import MCPAuth
from healthcore_company_tools.audit import auth_failures, request_id_var
from mcpauth.config import (
    AuthServerConfig,
    AuthServerType,
    AuthorizationServerMetadata,
)
from mcpauth.exceptions import (
    MCPAuthTokenVerificationException,
    MCPAuthTokenVerificationExceptionCode,
)
from mcpauth.types import AuthInfo

ISSUER = os.getenv("HEALTHCORE_TOKEN_ISSUER", "https://healthcore-api").strip()
AUDIENCE = os.getenv("HEALTHCORE_TOKEN_AUDIENCE", "healthcore-company-tools").strip()
INCIDENT_SCOPE = "incidents:read"
INVENTORY_SCOPE = "inventory:read"


def _secret() -> str:
    secret = os.getenv("SECRET_KEY", "").strip()
    if not secret:
        raise MCPAuthTokenVerificationException(
            MCPAuthTokenVerificationExceptionCode.TOKEN_VERIFICATION_FAILED
        )
    return secret


def verify_staff_token(token: str) -> AuthInfo:
    """Check the HS256 signature and expiry. Issuer and audience stay with MCP Auth."""

    try:
        claims = jwt.decode(
            token,
            _secret(),
            algorithms=["HS256"],
            options={"verify_aud": False, "verify_iss": False},
        )
    except jwt.ExpiredSignatureError as exc:
        auth_failures[request_id_var.get()] = "TOKEN_EXPIRED"
        raise MCPAuthTokenVerificationException(
            MCPAuthTokenVerificationExceptionCode.INVALID_TOKEN,
            cause=exc,
        ) from exc
    except jwt.PyJWTError as exc:
        auth_failures[request_id_var.get()] = "INVALID_TOKEN"
        raise MCPAuthTokenVerificationException(
            MCPAuthTokenVerificationExceptionCode.INVALID_TOKEN,
            cause=exc,
        ) from exc
    if claims.get("typ") == "reset" or not claims.get("sub") or not claims.get("iss"):
        auth_failures[request_id_var.get()] = "INVALID_TOKEN"
        raise MCPAuthTokenVerificationException(
            MCPAuthTokenVerificationExceptionCode.INVALID_TOKEN
        )
    raw_scope = claims.get("scope") or ""
    scopes = raw_scope.split() if isinstance(raw_scope, str) else list(raw_scope)
    return AuthInfo(
        token=token,
        issuer=str(claims["iss"]),
        subject=str(claims["sub"]),
        audience=claims.get("aud"),
        scopes=scopes,
        claims={key: value for key, value in claims.items() if key != "token"},
    )


def build_mcp_auth() -> MCPAuth:
    metadata = AuthorizationServerMetadata(
        issuer=ISSUER,
        authorization_endpoint=f"{ISSUER}/auth/login",
        token_endpoint=f"{ISSUER}/auth/login",
        response_types_supported=["code"],
        grant_types_supported=["authorization_code"],
        code_challenge_methods_supported=["S256"],
    )
    return MCPAuth(
        server=AuthServerConfig(metadata=metadata, type=AuthServerType.OAUTH)
    )
