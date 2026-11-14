#!/usr/bin/env python3
"""Assign HMore roles to Auth0 users (by email) before or after first login.

Usage (from apps/api with venv active and DATABASE_URL set):

  python scripts/bootstrap_identity.py grant-super-admin --email you@example.com
  python scripts/bootstrap_identity.py grant-org-role --email a@x.com --role tenant --org-slug demo-org
  python scripts/bootstrap_identity.py show-user --email a@x.com

Production requires HMORE_BOOTSTRAP_TOKEN and --token.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/bootstrap_identity.py` without installing the package.
_API_ROOT = Path(__file__).resolve().parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from app.core.config import get_settings
from app.db.session import check_database_connection, session_scope
from app.ops.identity_bootstrap import (
    BootstrapError,
    assert_bootstrap_allowed,
    describe_user,
    grant_org_role,
    grant_super_admin,
)
from app.rbac.roles import APPROVED_ROLE_COUNT, ROLE_DEFINITIONS


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap Auth0-linked HMore memberships by email.")
    parser.add_argument(
        "--token",
        help="HMORE_BOOTSTRAP_TOKEN (required when ENVIRONMENT is production)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_super = sub.add_parser("grant-super-admin", help="Grant platform Super Admin")
    p_super.add_argument("--email", required=True)
    p_super.add_argument("--display-name")

    p_org = sub.add_parser("grant-org-role", help="Grant an organisation-scoped role")
    p_org.add_argument("--email", required=True)
    p_org.add_argument(
        "--role",
        required=True,
        choices=[r.value for r in ROLE_DEFINITIONS],
    )
    p_org.add_argument("--org-slug", required=True)
    p_org.add_argument("--org-name", help="Used when creating a new organisation")
    p_org.add_argument("--display-name")

    p_show = sub.add_parser("show-user", help="Show user + memberships")
    p_show.add_argument("--email", required=True)

    sub.add_parser("list-roles", help=f"List the {APPROVED_ROLE_COUNT} approved roles")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    settings = get_settings()

    if args.command == "list-roles":
        for role, definition in ROLE_DEFINITIONS.items():
            scope = "platform" if definition.platform_scoped else "organisation"
            print(f"{role.value:28} {definition.display_name:28} ({scope})")
        return 0

    try:
        assert_bootstrap_allowed(settings, token=args.token)
    except BootstrapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not settings.database_url:
        print("error: DATABASE_URL is not set", file=sys.stderr)
        return 2

    if not check_database_connection():
        print(
            "error: Cannot reach PostgreSQL. Start Docker postgres and run `alembic upgrade head`.",
            file=sys.stderr,
        )
        return 2

    try:
        with session_scope() as session:
            if args.command == "grant-super-admin":
                result = grant_super_admin(
                    session,
                    args.email,
                    display_name=args.display_name,
                )
            elif args.command == "grant-org-role":
                result = grant_org_role(
                    session,
                    email=args.email,
                    role_value=args.role,
                    organisation_slug=args.org_slug,
                    organisation_name=args.org_name,
                    display_name=args.display_name,
                )
            elif args.command == "show-user":
                result = describe_user(session, args.email)
            else:
                print(f"error: unknown command {args.command}", file=sys.stderr)
                return 2
    except BootstrapError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())