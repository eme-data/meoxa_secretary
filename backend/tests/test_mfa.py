"""Tests du service MFA (TOTP + backup codes)."""

import json

import pyotp
import pytest

from meoxa_secretary.services.mfa import MfaService


@pytest.fixture(autouse=True)
def _fernet_key(monkeypatch):
    """Cache le secret de chiffrement pour les tests."""
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-at-least-32-chars-long")
    monkeypatch.setenv(
        "SETTINGS_ENCRYPTION_KEY", "pXeWLB-qXkPc-n5yP0j8Z_bvJt8vHQFmjvSRlQ2qRiQ="
    )
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://meoxa:test@localhost:5432/test"
    )


def test_enrollment_generates_secret_and_qr() -> None:
    svc = MfaService()
    enroll = svc.start_enrollment("user@example.com")
    assert len(enroll.secret) == 32  # base32 length
    assert enroll.provisioning_uri.startswith("otpauth://")
    assert enroll.qr_code_png_b64  # non-empty base64


def test_confirm_with_good_code() -> None:
    svc = MfaService()
    enroll = svc.start_enrollment("user@example.com")
    # Génère le code TOTP courant
    code = pyotp.TOTP(enroll.secret).now()
    encrypted_secret, backup_codes = svc.confirm_enrollment(enroll.secret, code)
    assert encrypted_secret  # stored encrypted
    assert len(backup_codes) == MfaService.BACKUP_CODE_COUNT


def test_confirm_with_bad_code_raises() -> None:
    svc = MfaService()
    enroll = svc.start_enrollment("user@example.com")
    with pytest.raises(ValueError):
        svc.confirm_enrollment(enroll.secret, "000000")


def test_verify_totp() -> None:
    svc = MfaService()
    secret = pyotp.random_base32()
    code = pyotp.TOTP(secret).now()
    assert svc.verify_totp(secret, code)
    assert not svc.verify_totp(secret, "111111")


def test_backup_code_consumed_once() -> None:
    svc = MfaService()
    codes = ["ABCD1234EF", "WXYZ5678GH"]
    encrypted = svc.encrypt_backup_codes(codes)

    # Premier usage OK
    new_encrypted = svc.verify_and_consume_backup(encrypted, "abcd1234ef")
    assert new_encrypted is not None

    remaining = json.loads(_decrypt_for_test(new_encrypted))
    assert "ABCD1234EF" not in remaining
    assert "WXYZ5678GH" in remaining

    # Rejeu du même code doit échouer
    assert svc.verify_and_consume_backup(new_encrypted, "abcd1234ef") is None


def test_backup_code_unknown_rejected() -> None:
    svc = MfaService()
    encrypted = svc.encrypt_backup_codes(["ABCD1234EF"])
    assert svc.verify_and_consume_backup(encrypted, "NOTINLIST0") is None


def _decrypt_for_test(encrypted_json: str) -> str:
    from meoxa_secretary.core.crypto import decrypt

    return decrypt(encrypted_json)
