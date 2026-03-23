import os
import sqlite3
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/assistant.db")


def ask_question(prompt: str) -> str:
    return input(prompt)


def create_schema(db: sqlite3.Connection):
    db.executescript(
        """
        -- Sessions table
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            channel_id TEXT,
            thread_ts TEXT,
            session_type TEXT NOT NULL DEFAULT 'dm',
            created_at INTEGER NOT NULL DEFAULT (unixepoch()),
            last_activity INTEGER NOT NULL DEFAULT (unixepoch()),
            metadata TEXT
        );

        -- Messages table
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            slack_ts TEXT,
            thread_ts TEXT,
            created_at INTEGER NOT NULL DEFAULT (unixepoch()),
            metadata TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        -- Scheduled tasks
        CREATE TABLE scheduled_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            thread_ts TEXT,
            task_description TEXT NOT NULL,
            cron_expression TEXT,
            scheduled_time INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL DEFAULT (unixepoch()),
            executed_at INTEGER,
            metadata TEXT
        );

        -- Pairing codes
        CREATE TABLE pairing_codes (
            code TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at INTEGER NOT NULL DEFAULT (unixepoch()),
            expires_at INTEGER NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0
        );

        -- Approved users
        CREATE TABLE approved_users (
            user_id TEXT PRIMARY KEY,
            approved_at INTEGER NOT NULL DEFAULT (unixepoch()),
            approved_by TEXT
        );

        -- Indexes
        CREATE INDEX idx_messages_session ON messages(session_id);
        CREATE INDEX idx_messages_created ON messages(created_at);
        CREATE INDEX idx_sessions_user ON sessions(user_id);
        CREATE INDEX idx_sessions_channel ON sessions(channel_id);
        CREATE INDEX idx_scheduled_tasks_status ON scheduled_tasks(status);
        CREATE INDEX idx_pairing_codes_user ON pairing_codes(user_id);
        """
    )


def main():
    print("🗄️  Maantra AI - Database Setup\n")

    db_path = Path(DATABASE_PATH)

    if db_path.exists():
        answer = ask_question(
            f"Database already exists at {DATABASE_PATH}.\nReset it? (y/N): "
        )

        if answer.lower() != "y":
            print("Setup cancelled.")
            return

        print("Removing existing database...")
        db_path.unlink()

    db_dir = db_path.parent

    if not db_dir.exists():
        print(f"Creating directory: {db_dir}")
        db_dir.mkdir(parents=True)

    print(f"Creating database: {DATABASE_PATH}")

    conn = sqlite3.connect(DATABASE_PATH)

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    print("Creating schema...")
    create_schema(conn)

    conn.commit()

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    print("\nTables created:")

    for table in tables:
        name = table[0]
        count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"  • {name} ({count} rows)")

    conn.close()

    print("\n✅ Database setup complete!")
    print(f"\nDatabase location: {DATABASE_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Setup failed:", e)
        sys.exit(1)