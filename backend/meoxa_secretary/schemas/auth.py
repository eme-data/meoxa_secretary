"""Schemas I/O pour l'authentification."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=10, max_length=200)
    organization_name: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MfaChallenge(BaseModel):
    """Réponse au login quand MFA activée — l'utilisateur doit ensuite poster /auth/mfa/login."""

    challenge_token: str
    mfa_required: bool = True


class MfaLoginRequest(BaseModel):
    challenge_token: str
    code: str


class MfaEnrollStart(BaseModel):
    secret: str
    provisioning_uri: str
    qr_code_png_b64: str


class MfaEnrollConfirm(BaseModel):
    secret: str
    code: str


class MfaEnrollConfirmResponse(BaseModel):
    backup_codes: list[str]


class UserMe(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    tenant_id: UUID
    role: str
    is_superadmin: bool
    totp_enabled: bool = False

    model_config = {"from_attributes": True}
