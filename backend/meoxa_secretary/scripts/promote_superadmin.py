"""Promeut un utilisateur existant au rôle super-admin plateforme.

Usage :
    docker compose exec backend python -m meoxa_secretary.scripts.promote_superadmin mathieu@mdoservices.fr
"""

import sys

from sqlalchemy import select

from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.user import User


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m meoxa_secretary.scripts.promote_superadmin <email>")
        sys.exit(1)

    email = sys.argv[1].strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            print(f"Utilisateur introuvable : {email}")
            sys.exit(2)
        user.is_superadmin = True
        db.commit()
        print(f"✓ {email} est maintenant super-admin plateforme.")


if __name__ == "__main__":
    main()
