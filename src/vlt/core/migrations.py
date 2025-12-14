from vlt.db import engine, Base
from vlt.core import models # Import models to register them with Base

def init_db():
    """Initializes the database schema."""
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
