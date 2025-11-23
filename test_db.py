from sqlmodel import create_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print("Using database URL:", DATABASE_URL)

# Create engine
engine = create_engine(DATABASE_URL)

# Test connection
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("Connection works! Result:", result.fetchall())
except Exception as e:
    print("Connection failed:", e)
