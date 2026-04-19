"""Application Celery — broker Redis + beat scheduler pour les tâches récurrentes."""

from celery import Celery
from celery.schedules import crontab

from meoxa_secretary.config import get_settings
from meoxa_secretary.core.observability import init_sentry

# Init Sentry avant Celery — l'intégration `CeleryIntegration` capture ensuite
# toutes les exceptions dans les tâches.
init_sentry()

_settings = get_settings()

celery_app = Celery(
    "meoxa_secretary",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
    include=[
        "meoxa_secretary.workers.tasks.emails",
        "meoxa_secretary.workers.tasks.meetings",
        "meoxa_secretary.workers.tasks.agenda",
        "meoxa_secretary.workers.tasks.graph_notifications",
        "meoxa_secretary.workers.tasks.tenant",
        "meoxa_secretary.workers.tasks.memory",
        "meoxa_secretary.workers.tasks.billing",
        "meoxa_secretary.workers.tasks.planner",
        "meoxa_secretary.workers.tasks.retention",
        "meoxa_secretary.workers.tasks.digest",
        "meoxa_secretary.workers.tasks.onboarding",
    ],
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    timezone="Europe/Paris",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=60 * 30,       # 30 min max par tâche (transcription longue)
    task_soft_time_limit=60 * 25,
    result_expires=60 * 60 * 24,
)

celery_app.conf.beat_schedule = {
    # Fallback — désactivable quand les webhooks Graph sont stables en prod.
    "sync-emails-every-5-min": {
        "task": "meoxa_secretary.workers.tasks.emails.sync_all_tenants",
        "schedule": crontab(minute="*/5"),
    },
    "sync-calendars-every-15-min": {
        "task": "meoxa_secretary.workers.tasks.agenda.sync_all_tenants",
        "schedule": crontab(minute="*/15"),
    },
    # Renouvellement des souscriptions Graph (TTL max 3j côté Microsoft).
    "renew-graph-subscriptions-every-6-hours": {
        "task": "meoxa_secretary.workers.tasks.graph_notifications.renew_subscriptions",
        "schedule": crontab(minute=15, hour="*/6"),
    },
    # Purge des tenants en fin de délai de suppression (RGPD) — quotidien 04:00 UTC.
    "purge-due-tenants-daily": {
        "task": "meoxa_secretary.workers.tasks.tenant.purge_due_tenants",
        "schedule": crontab(minute=0, hour=4),
    },
    # Rétention transcripts par tenant — quotidien 04:30 UTC.
    "apply-retention-daily": {
        "task": "meoxa_secretary.workers.tasks.retention.apply_retention_all",
        "schedule": crontab(minute=30, hour=4),
    },
    # Digest matinal : tick une fois par heure (à :05) et chaque tenant décide
    # de s'auto-envoyer si son heure locale == digest.hour.
    "send-digests-hourly": {
        "task": "meoxa_secretary.workers.tasks.digest.send_all_digests",
        "schedule": crontab(minute=5, hour="*"),
    },
}
