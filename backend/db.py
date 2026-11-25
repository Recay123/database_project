"""MySQL connector configuration. This module is not used by sample GET routes yet.

Backend teammate: import get_db and call SQL using %s parameters.
DB teammate: supply schema.sql and an initialization / sample data script.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')


def get_db():
    """Yield a MySQL connection; close it after each request.

    Use `connection.commit()` on a successful transaction and `rollback()` on error.
    Requires `mysql-connector-python` installed and a running MySQL server.
    """
    import mysql.connector

    connection = mysql.connector.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', '3306')),
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        database=os.getenv('DB_NAME', 'frame'),
        charset='utf8mb4',
    )
    try:
        yield connection
    finally:
        connection.close()
