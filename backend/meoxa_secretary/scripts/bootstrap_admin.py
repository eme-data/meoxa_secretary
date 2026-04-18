"""Création idempotente du premier super-admin plateforme.

Utilisé par le script d'installation. Lit ADMIN_EMAIL, ADMIN_PASSWORD,
ADMIN_ORG_NAME dans l'environnement.

Usage :
    docker compose exec -T -e ADMIN_EMAIL=x -e ADMIN_PASSWORD=y backend \
        python -m meoxa_secretary.scripts.bootstrap_admin
"""

import os
import sys

from slugify import slugify
from sqlalchemy import select

from meoxa_secretary.core.security import hash_password
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.tenant import Tenant
from meoxa_secretary.models.user import Membership, Role, User


def main() -> None:
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    org_name = os.environ.get("ADMIN_ORG_NAME", "MDO Services")
    full_name = os.environ.get("ADMIN_FULL_NAME", org_name + " admin")

    if not email or not password:
        print("ADMIN_EMAIL et ADMIN_PASSWORD requis", file=sys.stderr)
        sys.exit(1)
    if len(password) < 10:
        print("ADMIN_PASSWORD doit faire au moins 10 caractères", file=sys.stderr)
        sys.exit(2)

    with SessionLocal() as db:
        slug = slugify(org_name)[:80]
        tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
        if not tenant:
            tenant = Tenant(name=org_name, slug=slug)
            db.add(tenant)
            db.flush()

        user = db.scalar(select(User).where(User.email == email))
        if not user:
            user = User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(password),
                is_active=True,
                is_superadmin=True,
            )
            db.add(user)
            db.flush()
            created = True
        else:
            user.is_superadmin = True
            created = False

        if not db.scalar(
            select(Membership).where(
                Membership.user_id == user.id, Membership.tenant_id == tenant.id
            )
        ):
            db.add(Membership(user_id=user.id, tenant_id=tenant.id, role=Role.OWNER))
        db.commit()

    action = "créé" if created else "promu"
    print(f"OK — {email} {action} super-admin (org: {tenant.slug})")


if __name__ == "__main__":
    main()
