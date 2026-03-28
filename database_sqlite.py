import logging

import apsw

logger = logging.getLogger(__name__)

class MooncakeStore:
    """Database for user mooncake counts"""

    def __init__(self, db_path="pairs.db"):
        self.db_path = db_path

        self.conn = apsw.Connection(self.db_path)
        self.cleanup_conn = apsw.Connection(self.db_path)
        self.init_db()

        self.run  = True


    def init_db(self):
        """Initialize database"""
        cur = self.conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id    INTEGER PRIMARY KEY,
                value INTEGER NOT NULL DEFAULT 0
            )
        """)
        logger.info("Sqlite database initializes successfully")


    def set_value(self, user_id, value):
        """Set value for specified user"""
        with self.conn:
            self.conn.execute(
                "INSERT INTO users (id, value) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET value = excluded.value",
                (user_id, value),
            )


    def get_value(self, user_id):
        """Get value for specified user"""
        with self.conn:
            row = self.conn.execute("SELECT value FROM users WHERE id = ?", (user_id,)).fetchone()
            return row[0] if row else None


    def get_top(self, n):
        """Get top N ids and values"""
        with self.conn:
            return self.conn.execute("SELECT id, value FROM users ORDER BY value DESC LIMIT ?", (n,)).fetchall()


    def delete_user(self, user_id):
        """Delete speciied user"""
        with self.conn:
            self.conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


    def increment(self, user_id, amount=1):
        """Increment value for specified user"""
        with self.conn:
            self.conn.cursor().execute(
                "INSERT INTO users (id, value) VALUES (?, ?) "
                "ON CONFLICT (id) DO UPDATE SET value = users.value + ?",
                (user_id, amount, amount),
            )


    def decrement(self, user_id, amount=1):
        """Decrement value for specified user"""
        with self.conn:
            self.conn.cursor().execute("UPDATE users SET value = value - ? WHERE id = ?", (amount, user_id))
