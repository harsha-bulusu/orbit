from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./orbit.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    # Sized well above the default (5 + 10) so a leaked-connection demo run
    # shows the gauge climb rather than hanging once the pool is exhausted.
    pool_size=20,
    max_overflow=80,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@contextmanager
def db_session():
    from app.alerting import engine as alert_engine
    from app.telemetry.metrics_setup import get_instruments

    instruments = get_instruments()
    db = SessionLocal()
    if instruments:
        instruments["open_db_connections_total"].add(1)
    alert_engine.record_connection_delta(1)
    try:
        yield db
    finally:
        db.close()
        if instruments:
            instruments["open_db_connections_total"].add(-1)
        alert_engine.record_connection_delta(-1)


def get_db():
    with db_session() as db:
        yield db
