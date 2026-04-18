"""Service MFA TOTP (RFC 6238) + codes de secours à usage unique."""

from __future__ import annotations

import base64
import io
import json
import secrets
from dataclasses import dataclass

import pyotp
import qrcode

from meoxa_secretary.core.crypto import decrypt, encrypt


@dataclass
class MfaEnrollment:
    secret: str             # secret en clair, à afficher une seule fois
    provisioning_uri: str   # otpauth://...
    qr_code_png_b64: str    # image PNG en base64


class MfaService:
    """Encapsule la génération/vérification TOTP + codes de secours.

    Les secrets et codes de secours sont persistés chiffrés (Fernet) sur `User`.
    """

    ISSUER = "meoxa_secretary"
    BACKUP_CODE_COUNT = 10
    BACKUP_CODE_LENGTH = 10

    # ---------- Enrôlement ----------

    def start_enrollment(self, email: str) -> MfaEnrollment:
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=email, issuer_name=self.ISSUER)

        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return MfaEnrollment(
            secret=secret,
            provisioning_uri=uri,
            qr_code_png_b64=base64.b64encode(buf.getvalue()).decode(),
        )

    def confirm_enrollment(self, secret: str, code: str) -> tuple[str, list[str]]:
        """Vérifie le 1er code TOTP et génère les codes de secours.

        Retourne (encrypted_secret, plaintext_backup_codes).
        Les backup codes sont à afficher UNE SEULE FOIS au user.
        """
        if not self.verify_totp(secret, code):
            raise ValueError("Code TOTP invalide")

        plain_codes = [
            secrets.token_hex(self.BACKUP_CODE_LENGTH // 2).upper()
            for _ in range(self.BACKUP_CODE_COUNT)
        ]
        return encrypt(secret), plain_codes

    # ---------- Vérification ----------

    @staticmethod
    def verify_totp(secret_or_encrypted: str, code: str) -> bool:
        # Autorise un secret en clair (pendant enroll) ou chiffré (depuis la DB).
        try:
            plain = decrypt(secret_or_encrypted)
        except Exception:
            plain = secret_or_encrypted
        return pyotp.TOTP(plain).verify(code, valid_window=1)

    def verify_and_consume_backup(
        self, encrypted_codes_json: str | None, code: str
    ) -> str | None:
        """Vérifie un backup code et le retire de la liste (one-shot).

        Retourne le nouveau JSON chiffré (sans le code consommé) ou None si invalide.
        """
        if not encrypted_codes_json:
            return None
        try:
            plain = decrypt(encrypted_codes_json)
            codes: list[str] = json.loads(plain)
        except Exception:
            return None

        normalized = code.strip().upper()
        if normalized not in codes:
            return None
        codes.remove(normalized)
        return encrypt(json.dumps(codes))

    @staticmethod
    def encrypt_backup_codes(codes: list[str]) -> str:
        return encrypt(json.dumps(codes))
