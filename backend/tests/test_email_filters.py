"""Tests du matcher de filtrage emails (sans DB — pure logique)."""

from unittest.mock import MagicMock, patch

from meoxa_secretary.services.email_filters import _matches, should_skip


def test_matches_substring() -> None:
    assert _matches("newsletter", "Super newsletter du jour")
    assert not _matches("marketing", "Support technique")


def test_matches_glob() -> None:
    assert _matches("*.newsletter.com", "promo@fr.newsletter.com")
    assert _matches("noreply@*", "noreply@stripe.com")
    assert not _matches("noreply@*", "contact@stripe.com")


@patch("meoxa_secretary.services.email_filters.SettingsService")
def test_should_skip_by_sender(mock_settings_cls) -> None:
    mock = MagicMock()
    mock.get_tenant.side_effect = lambda _t, key: {
        "emails.skip_senders": "noreply@, *.newsletter.com",
        "emails.skip_subject_patterns": "",
    }[key]
    mock_settings_cls.return_value = mock

    skip, reason = should_skip("tenant-x", "noreply@stripe.com", "Reçu de paiement")
    assert skip
    assert "noreply@" in reason

    skip, _ = should_skip("tenant-x", "contact@stripe.com", "Reçu")
    assert not skip


@patch("meoxa_secretary.services.email_filters.SettingsService")
def test_should_skip_by_subject(mock_settings_cls) -> None:
    mock = MagicMock()
    mock.get_tenant.side_effect = lambda _t, key: {
        "emails.skip_senders": "",
        "emails.skip_subject_patterns": "[SPAM], Désinscription",
    }[key]
    mock_settings_cls.return_value = mock

    skip, _ = should_skip("tenant-x", "sender@ok.com", "[SPAM] Offre limitée")
    assert skip

    skip, _ = should_skip("tenant-x", "sender@ok.com", "Facture du mois")
    assert not skip


@patch("meoxa_secretary.services.email_filters.SettingsService")
def test_should_skip_empty_filters_passes(mock_settings_cls) -> None:
    mock = MagicMock()
    mock.get_tenant.return_value = ""
    mock_settings_cls.return_value = mock

    skip, _ = should_skip("tenant-x", "anyone@any.com", "Any subject")
    assert not skip
