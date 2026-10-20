from db import get_connection

try:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT current_database(),
                       current_user,
                       COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
            """)

            db_name, db_user, table_count = cur.fetchone()

            print("Database:", db_name)
            print("User:", db_user)
            print("Tables:", table_count)
            print("PostgreSQL 接続成功！!")

except Exception as e:
    print("PostgreSQL 接続失敗:", type(e).__name__)
