from vlt.db import get_db
from vlt.core.models import Thread
from sqlalchemy import select

db = next(get_db())
threads = db.scalars(select(Thread)).all()
print("--- ALL THREADS ---")
for t in threads:
    print(f"ID: '{t.id}' | Project: '{t.project_id}'")
print("-------------------")
