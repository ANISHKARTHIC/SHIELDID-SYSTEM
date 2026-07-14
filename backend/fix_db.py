from backend.db.session import engine; from sqlalchemy import text; 
with engine.connect() as conn:
    conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector;'))
    conn.commit()

