"""Database module for video manager using SQLite."""

import sqlite3
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class Video:
    """Video data model."""
    id: Optional[int]
    path: str
    filename: str
    duration: float
    thumbnail_path: Optional[str]
    folder_id: int

    @property
    def duration_str(self) -> str:
        """Format duration as HH:MM:SS."""
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"


@dataclass
class Folder:
    """Folder data model."""
    id: Optional[int]
    path: str
    name: str


@dataclass
class Tag:
    """Tag data model."""
    id: Optional[int]
    name: str


class Database:
    """SQLite database handler for video manager."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            app_data = Path.home() / ".video_manager"
            app_data.mkdir(exist_ok=True)
            db_path = str(app_data / "videos.db")

        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                duration REAL DEFAULT 0,
                thumbnail_path TEXT,
                folder_id INTEGER,
                FOREIGN KEY (folder_id) REFERENCES folders (id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT DEFAULT '#3498db'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS video_tags (
                video_id INTEGER,
                tag_id INTEGER,
                PRIMARY KEY (video_id, tag_id),
                FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_folder ON videos (folder_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_tags_video ON video_tags (video_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_tags_tag ON video_tags (tag_id)")

        self.conn.commit()

    # Folder operations
    def add_folder(self, path: str) -> Folder:
        """Add a new folder to watch."""
        name = os.path.basename(path)
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO folders (path, name) VALUES (?, ?)",
            (path, name)
        )
        self.conn.commit()

        cursor.execute("SELECT * FROM folders WHERE path = ?", (path,))
        row = cursor.fetchone()
        return Folder(id=row["id"], path=row["path"], name=row["name"])

    def get_folders(self) -> list[Folder]:
        """Get all registered folders."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM folders ORDER BY name")
        return [Folder(id=row["id"], path=row["path"], name=row["name"])
                for row in cursor.fetchall()]

    def remove_folder(self, folder_id: int):
        """Remove a folder and its videos."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        self.conn.commit()

    # Video operations
    def add_video(self, path: str, filename: str, duration: float,
                  thumbnail_path: Optional[str], folder_id: int) -> Video:
        """Add a new video."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO videos (path, filename, duration, thumbnail_path, folder_id)
            VALUES (?, ?, ?, ?, ?)
        """, (path, filename, duration, thumbnail_path, folder_id))
        self.conn.commit()

        video_id = cursor.lastrowid
        return Video(
            id=video_id, path=path, filename=filename,
            duration=duration, thumbnail_path=thumbnail_path, folder_id=folder_id
        )

    def get_video(self, video_id: int) -> Optional[Video]:
        """Get a video by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        if row:
            return Video(
                id=row["id"], path=row["path"], filename=row["filename"],
                duration=row["duration"], thumbnail_path=row["thumbnail_path"],
                folder_id=row["folder_id"]
            )
        return None

    def get_videos(self, folder_id: Optional[int] = None) -> list[Video]:
        """Get all videos, optionally filtered by folder."""
        cursor = self.conn.cursor()
        if folder_id is not None:
            cursor.execute("SELECT * FROM videos WHERE folder_id = ? ORDER BY filename", (folder_id,))
        else:
            cursor.execute("SELECT * FROM videos ORDER BY filename")

        return [Video(
            id=row["id"], path=row["path"], filename=row["filename"],
            duration=row["duration"], thumbnail_path=row["thumbnail_path"],
            folder_id=row["folder_id"]
        ) for row in cursor.fetchall()]

    def get_videos_by_tags(self, tag_ids: list[int]) -> list[Video]:
        """Get videos that have all specified tags."""
        if not tag_ids:
            return self.get_videos()

        cursor = self.conn.cursor()
        placeholders = ",".join("?" * len(tag_ids))
        cursor.execute(f"""
            SELECT v.* FROM videos v
            JOIN video_tags vt ON v.id = vt.video_id
            WHERE vt.tag_id IN ({placeholders})
            GROUP BY v.id
            HAVING COUNT(DISTINCT vt.tag_id) = ?
            ORDER BY v.filename
        """, (*tag_ids, len(tag_ids)))

        return [Video(
            id=row["id"], path=row["path"], filename=row["filename"],
            duration=row["duration"], thumbnail_path=row["thumbnail_path"],
            folder_id=row["folder_id"]
        ) for row in cursor.fetchall()]

    def remove_video(self, video_id: int):
        """Remove a video."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        self.conn.commit()

    def update_video_thumbnail(self, video_id: int, thumbnail_path: str):
        """Update video thumbnail path."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE videos SET thumbnail_path = ? WHERE id = ?",
            (thumbnail_path, video_id)
        )
        self.conn.commit()

    # Tag operations
    def add_tag(self, name: str) -> Tag:
        """Add a new tag."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO tags (name) VALUES (?)",
            (name,)
        )
        self.conn.commit()

        cursor.execute("SELECT * FROM tags WHERE name = ?", (name,))
        row = cursor.fetchone()
        return Tag(id=row["id"], name=row["name"])

    def get_tags(self) -> list[Tag]:
        """Get all tags."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM tags ORDER BY name")
        return [Tag(id=row["id"], name=row["name"])
                for row in cursor.fetchall()]

    def remove_tag(self, tag_id: int):
        """Remove a tag."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        self.conn.commit()

    def update_tag(self, tag_id: int, name: str):
        """Update tag name."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE tags SET name = ? WHERE id = ?", (name, tag_id))
        self.conn.commit()

    # Video-Tag associations
    def add_video_tag(self, video_id: int, tag_id: int):
        """Associate a tag with a video."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO video_tags (video_id, tag_id) VALUES (?, ?)",
            (video_id, tag_id)
        )
        self.conn.commit()

    def remove_video_tag(self, video_id: int, tag_id: int):
        """Remove a tag from a video."""
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM video_tags WHERE video_id = ? AND tag_id = ?",
            (video_id, tag_id)
        )
        self.conn.commit()

    def get_video_tags(self, video_id: int) -> list[Tag]:
        """Get all tags for a video."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT t.id, t.name FROM tags t
            JOIN video_tags vt ON t.id = vt.tag_id
            WHERE vt.video_id = ?
            ORDER BY t.name
        """, (video_id,))
        return [Tag(id=row["id"], name=row["name"])
                for row in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        self.conn.close()
