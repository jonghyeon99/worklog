
import os
import psycopg


def get_connection():
    return psycopg.connect(
        host="localhost",
        port=5432,
        dbname="worklog_db",
        user="worklog_user",
        password=os.environ["DB_PASSWORD"]
    )
