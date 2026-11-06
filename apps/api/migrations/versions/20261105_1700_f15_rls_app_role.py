"""F1.5 create non-superuser role so FORCE RLS is enforceable in app/CI.

PostgreSQL superusers bypass RLS even with FORCE. The login role used in Compose/CI
is typically a superuser, so organisation policies only apply after SET LOCAL ROLE
to hmore_app.

Revision ID: 20261105_1700_f15
Revises: 20261105_1600_f15
Create Date: 2026-11-05 17:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20261105_1700_f15"
down_revision: Union[str, None] = "20261105_1600_f15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hmore_app') THEN
            CREATE ROLE hmore_app NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOLOGIN;
          END IF;
        END
        $$;
        """
    )
    op.execute("GRANT USAGE ON SCHEMA public TO hmore_app")
    op.execute(
        """
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hmore_app
        """
    )
    op.execute(
        """
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO hmore_app
        """
    )
    op.execute(
        """
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
          GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO hmore_app
        """
    )
    # Allow the migration/login role (often a superuser in CI) to assume hmore_app.
    op.execute(
        """
        DO $$
        DECLARE
          login_role text := current_user;
        BEGIN
          EXECUTE format('GRANT hmore_app TO %I', login_role);
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
          login_role text := current_user;
        BEGIN
          EXECUTE format('REVOKE hmore_app FROM %I', login_role);
        EXCEPTION WHEN undefined_object THEN
          NULL;
        END
        $$;
        """
    )
    op.execute(
        """
        ALTER DEFAULT PRIVILEGES IN SCHEMA public
          REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM hmore_app
        """
    )
    op.execute(
        """
        REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM hmore_app
        """
    )
    op.execute(
        """
        REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public FROM hmore_app
        """
    )
    op.execute("REVOKE USAGE ON SCHEMA public FROM hmore_app")
    op.execute("DROP ROLE IF EXISTS hmore_app")
