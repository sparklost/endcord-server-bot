import logging

import psycopg

logger = logging.getLogger(__name__)


class MooncakeStore:
    """Database for user mooncake counts"""

    def __init__(self, host, user, password, dbname):
        with psycopg.connect(host=host, user=user, password=password, dbname="postgres", autocommit=True) as admin_conn:
            with admin_conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
                if cur.fetchone() is None:
                    cur.execute(f"CREATE DATABASE {dbname}")
                    logger.info(f"Created database: {dbname}")

        self.conn = psycopg.connect(host=host, user=user, password=password, dbname=dbname, autocommit=True)
        self.cleanup_conn = psycopg.connect(host=host, user=user, password=password, dbname=dbname, autocommit=True)
        self.init_db()

        self.run  = True


    def init_db(self):
        """Initialize database"""
        with self.conn.cursor() as cur:

            cur.execute("PRAGMA journal_mode=WAL")  # not needed in postgres
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id    BIGINT PRIMARY KEY,
                    value BIGINT NOT NULL DEFAULT 0
                )
            """)
        logger.info("Postgresql database initializes successfully")


    def set_value(self, user_id, value):
        """Set value for specified user"""
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, value) VALUES (%s, %s) "
                "ON CONFLICT (id) DO UPDATE SET value = EXCLUDED.value",
                (user_id, value),
            )


    def get_value(self, user_id):
        """Get value for specified user"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT value FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return row[0] if row else None


    def get_top(self, n):
        """Get top N ids and values"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, value FROM users ORDER BY value DESC LIMIT %s", (n,))
            return cur.fetchall()


    def delete_user(self, user_id):
        """Delete speciied user"""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))


    def increment(self, user_id, amount=1):
        """Increment value for specified user"""
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, value) VALUES (%s, %s) "
                "ON CONFLICT (id) DO UPDATE SET value = users.value + %s",
                (user_id, amount, amount),
            )


    def decrement(self, user_id, amount=1):
        """Decrement value for specified user"""
        with self.conn.cursor() as cur:
            cur.execute("UPDATE users SET value = value - %s WHERE id = %s", (amount, user_id))
