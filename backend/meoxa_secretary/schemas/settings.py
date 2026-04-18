"""Schemas I/O pour la configuration plateforme et tenant."""

from pydantic import BaseModel


class SettingOut(BaseModel):
    key: str
    label: str
    description: str
    kind: str
    options: list[str]
    is_secret: bool
    value: str           # "" pour les secrets (jamais renvoyés en clair)
    masked: str          # "sk-••••abcd" pour affichage
    has_value: bool = False


class SettingUpdate(BaseModel):
    value: str
