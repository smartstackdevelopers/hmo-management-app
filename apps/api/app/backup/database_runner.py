"""PostgreSQL backup runner — isolated environments only for restore drills."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.engine import Engine, make_url


def pg_dump_available() -> bool:
    return shutil.which("pg_dump") is not None


def _pg_env(database_url: str) -> dict[str, str]:
    env = os.environ.copy()
    url = make_url(database_url)
    if url.password:
        env["PGPASSWORD"] = url.password
    return env


def _connection_args(database_url: str) -> list[str]:
    url = make_url(database_url)
    args = []
    if url.host:
        args.extend(["-h", url.host])
    if url.port:
        args.extend(["-p", str(url.port)])
    if url.username:
        args.extend(["-U", url.username])
    db = url.database or "postgres"
    args.extend(["-d", db])
    return args


def run_pg_dump(database_url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["pg_dump", "--format=custom", "--no-owner", "--no-acl", *_connection_args(database_url)]
    with output_path.open("wb") as out:
        proc = subprocess.run(
            cmd,
            env=_pg_env(database_url),
            stdout=out,
            stderr=subprocess.PIPE,
            check=False,
        )
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError(f"pg_dump failed: {err[:500]}")


def verify_pg_dump_archive(path: Path) -> bool:
    if not pg_dump_available() or not path.is_file() or path.stat().st_size < 64:
        return False
    proc = subprocess.run(
        ["pg_restore", "--list", str(path)],
        capture_output=True,
        check=False,
    )
    return proc.returncode == 0


def run_config_manifest(engine: Engine, output_path: Path) -> dict[str, object]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with engine.connect() as conn:
        head = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        table_count = conn.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        ).scalar()
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "alembic_head": head,
        "public_table_count": table_count,
        "note": "Config manifest only — no secrets",
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
