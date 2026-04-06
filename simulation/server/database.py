"""SQLite database setup using SQLModel."""

from sqlmodel import SQLModel, Session, create_engine

from server.config import settings

# Ensure data directory exists
settings.data_dir.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    echo=False,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables():
    """Create all SQLModel tables if they don't exist."""
    # Import models to register them with SQLModel metadata
    from server.models import AuditLog, DecisionRecord, DelegateSession, DimensionScoreRecord  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session():
    """Yield a database session for dependency injection."""
    with Session(engine) as session:
        yield session
