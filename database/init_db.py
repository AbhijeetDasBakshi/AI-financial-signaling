from database.db import engine, Base
from database import models  # noqa

def init():
    Base.metadata.create_all(bind=engine)
    print("PostgreSQL tables created successfully.")

if __name__ == "__main__":
    init()