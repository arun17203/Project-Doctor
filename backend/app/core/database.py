from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

# Database Engine Configuration
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {}
if is_sqlite:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True if not is_sqlite else False,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency for database session lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Verify active database connection."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection check error: {e}")
        return False


def init_db():
    """Create tables if they do not exist."""
    # Import all models here so that Base.metadata has them registered
    import backend.app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    # Seed default developer demo user for instant login
    try:
        from backend.app.models.user import User
        from backend.app.core.security import hash_password
        with SessionLocal() as db:
            existing = db.query(User).filter(User.email == "developer@example.com").first()
            if not existing:
                demo_user = User(
                    name="Demo Developer",
                    email="developer@example.com",
                    password_hash=hash_password("password123"),
                    is_active=True,
                )
                db.add(demo_user)
                db.commit()
    except Exception as e:
        print(f"Auto-seed demo user notice: {e}")

