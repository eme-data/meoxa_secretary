"""Modèles SQLAlchemy — importés ici pour qu'Alembic les détecte."""

from meoxa_secretary.models.audit import AuditLog
from meoxa_secretary.models.base import Base
from meoxa_secretary.models.billing import SubscriptionStatus, TenantSubscription
from meoxa_secretary.models.email import EmailStatus, EmailThread, EmailUrgency
from meoxa_secretary.models.integration import MicrosoftIntegration
from meoxa_secretary.models.invitation import Invitation, InvitationStatus
from meoxa_secretary.models.meeting import Meeting, MeetingTranscript
from meoxa_secretary.models.memory import EMBEDDING_DIM, MemoryEntry, MemorySourceType
from meoxa_secretary.models.setting import PlatformSetting, TenantSetting
from meoxa_secretary.models.subscription import GraphResourceType, GraphSubscription
from meoxa_secretary.models.tenant import Tenant
from meoxa_secretary.models.usage import LlmTaskKind, LlmUsageEvent
from meoxa_secretary.models.user import Membership, User

__all__ = [
    "Base",
    "Tenant",
    "User",
    "Membership",
    "MicrosoftIntegration",
    "EmailThread",
    "EmailStatus",
    "EmailUrgency",
    "Meeting",
    "MeetingTranscript",
    "PlatformSetting",
    "TenantSetting",
    "AuditLog",
    "GraphSubscription",
    "GraphResourceType",
    "TenantSubscription",
    "SubscriptionStatus",
    "MemoryEntry",
    "MemorySourceType",
    "EMBEDDING_DIM",
    "LlmUsageEvent",
    "LlmTaskKind",
    "Invitation",
    "InvitationStatus",
]
