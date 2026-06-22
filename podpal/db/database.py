from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from podpal.db.models import Base


# =====================================
# DATABASE
# =====================================

DATABASE_URL = "sqlite:///podblendz.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False
    }
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# =====================================
# INIT
# =====================================

def init_db():
    """
    Create all tables.
    """

    Base.metadata.create_all(
        bind=engine
    )


# =====================================
# SESSION
# =====================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
