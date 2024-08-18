import sqlite3
import logging

logging.basicConfig(level=logging.DEBUG)

def create_tables():
    logging.info("create_tables function called")
    try:
        conn = sqlite3.connect('WA2.db')
        cursor = conn.cursor()

        # Create user table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                scores_20 INTEGER NOT NULL DEFAULT 0,
                scores_30 INTEGER NOT NULL DEFAULT 0,
                scores_40 INTEGER NOT NULL DEFAULT 0,
                scores_50 INTEGER NOT NULL DEFAULT 0
            )
        ''')

        # Create leaderboard table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leaderboard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_type TEXT NOT NULL,
                username TEXT NOT NULL,
                score INTEGER NOT NULL,
                FOREIGN KEY(username) REFERENCES user(username)
            )
        ''')

        # Add is_admin column if it doesn't exist
        try:
            cursor.execute('''
                ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0
            ''')
        except sqlite3.OperationalError as e:
            if 'duplicate column name' not in str(e):
                logging.error(f"Error altering table: {e}")
                raise

        conn.commit()
        logging.info("Tables created/altered successfully and connection closed")
    except Exception as e:
        logging.error(f"Error in create_tables: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_tables()
