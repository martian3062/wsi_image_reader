import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "biotech.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def column_exists(cur, table_name, column_name):
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cur.fetchall()]
    return column_name in columns


def add_column_if_missing(cur, table_name, column_name, column_def):
    if not column_exists(cur, table_name, column_name):
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            width INTEGER,
            height INTEGER,
            avg_intensity REAL,
            intensity_std REAL,
            edge_density REAL,
            redness_score REAL,
            saturation_score REAL,
            tissue_ratio REAL,
            risk_score REAL,
            pattern_label TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # Add new columns if database already existed from older version
    add_column_if_missing(cur, "analyses", "filetype", "TEXT DEFAULT 'image'")
    add_column_if_missing(cur, "analyses", "roi_json", "TEXT")
    add_column_if_missing(cur, "analyses", "thumbnail_path", "TEXT")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS saved_cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
        )
        """
    )

    conn.commit()
    conn.close()
