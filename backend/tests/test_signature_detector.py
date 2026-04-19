"""Tests pour la détection automatique de signature dans sentItems."""

from meoxa_secretary.services.signature_detector import detect_signature_from_messages


SIG = """--
Jean Dupont
Cabinet Dupont Conseil
jean@dupont.fr"""


def _msg(body_text: str) -> dict:
    return {"body": {"content": body_text}}


def test_returns_none_when_too_few_messages():
    messages = [_msg(f"Bonjour,\n\nMerci.\n\n{SIG}")] * 3
    assert detect_signature_from_messages(messages) is None


def test_detects_common_signature():
    messages = [
        _msg(f"Bonjour Paul,\n\nMerci pour votre retour.\n\n{SIG}"),
        _msg(f"Bonjour Anne,\n\nTrès bien, je te tiens au courant.\n\n{SIG}"),
        _msg(f"Re,\n\nCi-joint le devis.\n\n{SIG}"),
        _msg(f"Bonjour,\n\nVoici mes disponibilités.\n\n{SIG}"),
        _msg(f"Hello,\n\nOK pour lundi.\n\n{SIG}"),
    ]
    result = detect_signature_from_messages(messages)
    assert result is not None
    assert "Jean Dupont" in result
    assert "jean@dupont.fr" in result


def test_ignores_quoted_reply_chain():
    body = f"""Bonjour,

Merci.

{SIG}

De : marie@exemple.fr
Envoyé : lundi
À : jean@dupont.fr
Objet : Re: dossier

Pourriez-vous…
"""
    messages = [_msg(body)] * 6
    result = detect_signature_from_messages(messages)
    assert result is not None
    assert "Jean Dupont" in result
    # Le contenu de la chaîne citée ne doit pas se retrouver dans la signature
    assert "marie@exemple.fr" not in result
    assert "Pourriez-vous" not in result


def test_returns_none_when_no_pattern():
    messages = [
        _msg("Un message complètement unique A."),
        _msg("Un message complètement unique B."),
        _msg("Un message complètement unique C."),
        _msg("Un message complètement unique D."),
        _msg("Un message complètement unique E."),
    ]
    assert detect_signature_from_messages(messages) is None
