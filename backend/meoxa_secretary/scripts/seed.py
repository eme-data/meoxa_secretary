"""Crée un tenant + un utilisateur admin de démo (idempotent)."""

from slugify import slugify
from sqlalchemy import select

from meoxa_secretary.core.security import hash_password
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.tenant import Tenant
from meoxa_secretary.models.user import Membership, Role, User

DEMO_EMAIL = "demo@meoxa.local"
DEMO_PASSWORD = "ChangeMe-2026!"
DEMO_ORG = "Meoxa Demo"


def main() -> None:
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == slugify(DEMO_ORG)))
        if not tenant:
            tenant = Tenant(name=DEMO_ORG, slug=slugify(DEMO_ORG))
            db.add(tenant)
            db.flush()

        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if not user:
            user = User(
                email=DEMO_EMAIL,
                full_name="Admin Démo",
                password_hash=hash_password(DEMO_PASSWORD),
                is_superadmin=True,
            )
            db.add(user)
            db.flush()
        elif not user.is_superadmin:
            user.is_superadmin = True

        if not db.scalar(
            select(Membership).where(
                Membership.user_id == user.id, Membership.tenant_id == tenant.id
            )
        ):
            db.add(Membership(user_id=user.id, tenant_id=tenant.id, role=Role.OWNER))

        db.commit()
        print(f"OK — user={DEMO_EMAIL} password={DEMO_PASSWORD} tenant={tenant.slug}")


if __name__ == "__main__":
    main()
