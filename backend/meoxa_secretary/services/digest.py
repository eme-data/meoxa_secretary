"""Digest matinal — résumé quotidien envoyé à l'owner du tenant.

Construit le contenu (emails urgents non traités, réunions du jour, actions Planner
en retard) et le pousse par email via Microsoft Graph `/me/sendMail` depuis la
BAL de l'owner lui-même.

Envoi "best-effort" : si le digest n'a rien à dire (aucun emails urgent, aucune
réunion, aucune action) on skip — pas de mail vide.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select, text

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.email import EmailStatus, EmailThread, EmailUrgency
from meoxa_secretary.models.meeting import Meeting
from meoxa_secretary.models.user import Membership, Role, User
from meoxa_secretary.services.microsoft_graph import MicrosoftGraphService
from meoxa_secretary.services.microsoft_integration import MicrosoftIntegrationError
from meoxa_secretary.services.settings import SettingsService

logger = get_logger(__name__)


@dataclass
class DigestContent:
    urgent_emails: list[EmailThread]
    drafted_emails: list[EmailThread]
    meetings_today: list[Meeting]

    @property
    def is_empty(self) -> bool:
        return (
            not self.urgent_emails
            and not self.drafted_emails
            and not self.meetings_today
        )


def build_digest(tenant_id: str) -> DigestContent:
    """Calcule le contenu du digest pour un tenant (scope RLS)."""
    tz_name = SettingsService().get_tenant(tenant_id, "general.timezone") or "Europe/Paris"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Europe/Paris")

    now_local = datetime.now(tz)
    start_of_day = datetime.combine(now_local.date(), time.min, tzinfo=tz)
    end_of_day = start_of_day + timedelta(days=1)

    with SessionLocal() as db:
        db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})

        urgent = db.scalars(
            select(EmailThread)
            .where(
                EmailThread.urgency == EmailUrgency.URGENT,
                EmailThread.status.in_([EmailStatus.PENDING, EmailStatus.DRAFTED]),
            )
            .order_by(EmailThread.received_at.desc().nullslast())
            .limit(5)
        ).all()

        drafted = db.scalars(
            select(EmailThread)
            .where(
                EmailThread.status == EmailStatus.DRAFTED,
                EmailThread.urgency != EmailUrgency.URGENT,
            )
            .order_by(EmailThread.received_at.desc().nullslast())
            .limit(5)
        ).all()

        meetings = db.scalars(
            select(Meeting)
            .where(
                Meeting.starts_at >= start_of_day.astimezone(UTC),
                Meeting.starts_at < end_of_day.astimezone(UTC),
            )
            .order_by(Meeting.starts_at)
        ).all()

    return DigestContent(
        urgent_emails=list(urgent),
        drafted_emails=list(drafted),
        meetings_today=list(meetings),
    )


def render_html(content: DigestContent, app_url: str, tenant_name: str) -> str:
    """Rend un HTML simple, inline-styled pour les clients mail."""
    today = date.today().strftime("%A %d %B %Y")

    def _email_row(t: EmailThread) -> str:
        subject = (t.subject or "(sans objet)").replace("<", "&lt;").replace(">", "&gt;")
        sender = (t.from_address or "").replace("<", "&lt;").replace(">", "&gt;")
        url = f"{app_url}/app/emails/{t.id}"
        return (
            f'<tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">'
            f'<a href="{url}" style="color:#0ea5e9;text-decoration:none;font-weight:600">{subject}</a>'
            f'<div style="color:#6b7280;font-size:12px">{sender}</div>'
            f'</td></tr>'
        )

    def _meeting_row(m: Meeting) -> str:
        title = (m.title or "(sans titre)").replace("<", "&lt;").replace(">", "&gt;")
        hour = m.starts_at.astimezone().strftime("%H:%M") if m.starts_at else "--:--"
        url = f"{app_url}/app/meetings/{m.id}"
        return (
            f'<tr><td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">'
            f'<span style="color:#6b7280;font-variant-numeric:tabular-nums">{hour}</span> '
            f'&middot; <a href="{url}" style="color:#0ea5e9;text-decoration:none">{title}</a>'
            f'</td></tr>'
        )

    sections: list[str] = []

    if content.urgent_emails:
        rows = "".join(_email_row(t) for t in content.urgent_emails)
        sections.append(
            f'<h2 style="font-size:16px;margin:24px 0 8px">🔥 À traiter en priorité ({len(content.urgent_emails)})</h2>'
            f'<table cellspacing="0" cellpadding="0" width="100%" style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">{rows}</table>'
        )

    if content.meetings_today:
        rows = "".join(_meeting_row(m) for m in content.meetings_today)
        sections.append(
            f'<h2 style="font-size:16px;margin:24px 0 8px">📅 Réunions du jour ({len(content.meetings_today)})</h2>'
            f'<table cellspacing="0" cellpadding="0" width="100%" style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">{rows}</table>'
        )

    if content.drafted_emails:
        rows = "".join(_email_row(t) for t in content.drafted_emails)
        sections.append(
            f'<h2 style="font-size:16px;margin:24px 0 8px">✉️ Brouillons prêts à relire ({len(content.drafted_emails)})</h2>'
            f'<table cellspacing="0" cellpadding="0" width="100%" style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">{rows}</table>'
        )

    body = "".join(sections) or '<p style="color:#6b7280">Rien de bloquant ce matin.</p>'

    return (
        '<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;'
        'max-width:600px;margin:0 auto;padding:24px;color:#111827">'
        f'<p style="color:#6b7280;font-size:13px;margin:0">Secretary by Meoxa &middot; {tenant_name}</p>'
        f'<h1 style="font-size:22px;margin:4px 0 24px">Bonjour, voici ton {today}</h1>'
        f'{body}'
        f'<p style="color:#9ca3af;font-size:12px;margin-top:32px">'
        f'Pour désactiver ce digest, va sur <a href="{app_url}/app/organization">les préférences du compte</a> '
        f'&middot; <code style="font-size:11px">digest.enabled = false</code>'
        '</p></div>'
    )


async def send_digest_for_tenant(tenant_id: str) -> bool:
    """Envoie le digest à l'owner du tenant via /me/sendMail. Retourne True si envoyé."""
    enabled = (
        SettingsService().get_tenant(tenant_id, "digest.enabled") or "true"
    ).lower() == "true"
    if not enabled:
        return False

    content = build_digest(tenant_id)
    if content.is_empty:
        logger.debug("digest.skip.empty", tenant_id=tenant_id)
        return False

    # Trouve l'owner (premier Role.OWNER actif du tenant)
    with SessionLocal() as db:
        owner = db.scalar(
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .where(
                Membership.tenant_id == UUID(tenant_id),
                Membership.role == Role.OWNER,
                User.is_active.is_(True),
            )
            .limit(1)
        )
        if not owner:
            logger.debug("digest.skip.no_owner", tenant_id=tenant_id)
            return False

        # Récupère aussi le nom du tenant pour l'affichage
        from meoxa_secretary.models.tenant import Tenant

        tenant = db.get(Tenant, UUID(tenant_id))
        tenant_name = tenant.name if tenant else "ton organisation"
        owner_id = str(owner.id)
        owner_email = owner.email

    from meoxa_secretary.config import get_settings

    app_url = (
        (get_settings().cors_origin_list[0] if get_settings().cors_origin_list else "")
        .rstrip("/")
    )
    html = render_html(content, app_url=app_url, tenant_name=tenant_name)

    try:
        graph = await MicrosoftGraphService.for_user(tenant_id, owner_id)
    except MicrosoftIntegrationError as exc:
        logger.debug("digest.skip.no_ms_integration", error=str(exc))
        return False

    try:
        await graph.send_mail(
            to=owner_email,
            subject=f"Secretary — ton digest du {date.today():%d/%m}",
            html_body=html,
            save_to_sent=False,
        )
    finally:
        await graph.aclose()

    logger.info("digest.sent", tenant_id=tenant_id, recipient=owner_email)
    return True
