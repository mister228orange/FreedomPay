from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings


def _ensure_sqlite_dir(url: str) -> None:
    if url.startswith("sqlite:///"):
        path = Path(url.removeprefix("sqlite:///"))
        if path.parent and str(path.parent) not in (".", ""):
            path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.DATABASE_URL)
connect_args = (
    {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)


def init_db() -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        with engine.begin() as conn:
            cols = conn.execute(text("PRAGMA table_info(invoice)")).fetchall()
            names = {c[1] for c in cols}
            # Recreate when schema drifts (legacy Numeric amounts → VARCHAR strings)
            amount_type = next(
                (str(c[2]).upper() for c in cols if c[1] == "amount"), ""
            )
            if cols and (
                "amount_merchant" not in names
                or "amount_usd" not in names
                or amount_type in {"NUMERIC", "DECIMAL", "REAL", "FLOAT"}
            ):
                conn.execute(text("DROP TABLE invoice"))
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
