"""Database module for video manager using SQLite."""

import sqlite3
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Video:
    """Video data model."""
    id: Optional[int]
    path: str
    filename: str
    duration: float
    thumbnail_path: Optional[str]
    folder_id: int
    favorite: bool = False
    created_at: Optional[str] = None
    last_played: Optional[str] = None
    play_count: int = 0
    playback_position: float = 0.0
    width: int = 0
    height: int = 0
    fps: float = 0.0
    file_size: int = 0
    file_hash: Optional[str] = None

    @property
    def duration_str(self) -> str:
        """Format duration as HH:MM:SS."""
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def resolution_str(self) -> str:
        """Format resolution as WxH."""
        if self.width and self.height:
            return f"{self.width}x{self.height}"
        return "Unknown"

    @property
    def progress_percent(self) -> float:
        """Get playback progress as percentage."""
        if self.duration > 0:
            return (self.playback_position / self.duration) * 100
        return 0.0


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


@dataclass
class PlayHistory:
    """Play history entry."""
    id: Optional[int]
    video_id: int
    played_at: str
    video: Optional[Video] = None


@dataclass
class Statistics:
    """Library statistics."""
    total_videos: int = 0
    total_duration: float = 0.0
    total_size: int = 0
    favorites_count: int = 0
    tags_count: int = 0
    folders_count: int = 0
    recently_played: int = 0


@dataclass
class Playlist:
    """Playlist data model."""
    id: Optional[int]
    name: str
    created_at: Optional[str] = None


@dataclass
class PlaylistItem:
    """Playlist item data model."""
    id: Optional[int]
    playlist_id: int
    video_id: int
    position: int
    video: Optional[Video] = None


@dataclass
class SmartCollection:
    """Smart collection data model."""
    id: Optional[int]
    name: str
    filter_type: str  # duration, resolution, size, recent
    filter_operator: str  # gt, lt, eq
    filter_value: str


@dataclass
class AppSettings:
    """Application settings."""
    theme: str = "dark"
    thumbnail_size: int = 180
    window_geometry: Optional[str] = None
    splitter_sizes: Optional[str] = None


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
        self._migrate_tables()

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
                favorite INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_played TEXT,
                play_count INTEGER DEFAULT 0,
                playback_position REAL DEFAULT 0,
                width INTEGER DEFAULT 0,
                height INTEGER DEFAULT 0,
                fps REAL DEFAULT 0,
                file_size INTEGER DEFAULT 0,
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS play_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id INTEGER NOT NULL,
                played_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
            )
        """)

        # Playlists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                video_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                FOREIGN KEY (playlist_id) REFERENCES playlists (id) ON DELETE CASCADE,
                FOREIGN KEY (video_id) REFERENCES videos (id) ON DELETE CASCADE
            )
        """)

        # Smart collections
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smart_collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                filter_type TEXT NOT NULL,
                filter_operator TEXT NOT NULL,
                filter_value TEXT NOT NULL
            )
        """)

        # Settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_folder ON videos (folder_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_filename ON videos (filename)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_favorite ON videos (favorite)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_last_played ON videos (last_played)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_tags_video ON video_tags (video_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_video_tags_tag ON video_tags (tag_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_play_history_video ON play_history (video_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_play_history_date ON play_history (played_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_playlist_items_playlist ON playlist_items (playlist_id)")

        self.conn.commit()

    def _migrate_tables(self):
        """Add new columns to existing tables if needed."""
        cursor = self.conn.cursor()

        cursor.execute("PRAGMA table_info(videos)")
        columns = [col[1] for col in cursor.fetchall()]

        migrations = [
            ("favorite", "INTEGER DEFAULT 0"),
            ("created_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
            ("last_played", "TEXT"),
            ("play_count", "INTEGER DEFAULT 0"),
            ("playback_position", "REAL DEFAULT 0"),
            ("width", "INTEGER DEFAULT 0"),
            ("height", "INTEGER DEFAULT 0"),
            ("fps", "REAL DEFAULT 0"),
            ("file_size", "INTEGER DEFAULT 0"),
            ("file_hash", "TEXT"),
        ]

        for col_name, col_type in migrations:
            if col_name not in columns:
                cursor.execute(f"ALTER TABLE videos ADD COLUMN {col_name} {col_type}")

        self.conn.commit()

    def _row_to_video(self, row) -> Video:
        """Convert database row to Video object."""
        keys = row.keys()
        return Video(
            id=row["id"],
            path=row["path"],
            filename=row["filename"],
            duration=row["duration"],
            thumbnail_path=row["thumbnail_path"],
            folder_id=row["folder_id"],
            favorite=bool(row["favorite"]) if "favorite" in keys else False,
            created_at=row["created_at"] if "created_at" in keys else None,
            last_played=row["last_played"] if "last_played" in keys else None,
            play_count=row["play_count"] if "play_count" in keys else 0,
            playback_position=row["playback_position"] if "playback_position" in keys else 0.0,
            width=row["width"] if "width" in keys else 0,
            height=row["height"] if "height" in keys else 0,
            fps=row["fps"] if "fps" in keys else 0.0,
            file_size=row["file_size"] if "file_size" in keys else 0,
            file_hash=row["file_hash"] if "file_hash" in keys else None,
        )

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
                  thumbnail_path: Optional[str], folder_id: int,
                  width: int = 0, height: int = 0, fps: float = 0.0,
                  file_size: int = 0) -> Video:
        """Add a new video."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO videos
            (path, filename, duration, thumbnail_path, folder_id, created_at, width, height, fps, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (path, filename, duration, thumbnail_path, folder_id,
              datetime.now().isoformat(), width, height, fps, file_size))
        self.conn.commit()

        video_id = cursor.lastrowid
        return Video(
            id=video_id, path=path, filename=filename,
            duration=duration, thumbnail_path=thumbnail_path, folder_id=folder_id,
            width=width, height=height, fps=fps, file_size=file_size
        )

    def get_video(self, video_id: int) -> Optional[Video]:
        """Get a video by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_video(row)
        return None

    def get_videos(self, folder_id: Optional[int] = None,
                   sort_by: str = "filename", sort_order: str = "asc",
                   search_query: str = "", favorites_only: bool = False) -> list[Video]:
        """Get videos with filtering and sorting options."""
        cursor = self.conn.cursor()

        valid_sort_columns = {"filename", "duration", "created_at", "favorite", "last_played", "play_count"}
        if sort_by not in valid_sort_columns:
            sort_by = "filename"
        sort_order = "DESC" if sort_order.lower() == "desc" else "ASC"

        conditions = []
        params = []

        if folder_id is not None:
            conditions.append("folder_id = ?")
            params.append(folder_id)

        if search_query:
            conditions.append("filename LIKE ?")
            params.append(f"%{search_query}%")

        if favorites_only:
            conditions.append("favorite = 1")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        if sort_by == "favorite":
            order_clause = "ORDER BY favorite DESC, filename ASC"
        else:
            order_clause = f"ORDER BY {sort_by} {sort_order}"

        query = f"SELECT * FROM videos {where_clause} {order_clause}"
        cursor.execute(query, params)

        return [self._row_to_video(row) for row in cursor.fetchall()]

    def get_videos_by_tags(self, tag_ids: list[int], sort_by: str = "filename",
                           sort_order: str = "asc", search_query: str = "") -> list[Video]:
        """Get videos that have all specified tags."""
        if not tag_ids:
            return self.get_videos(sort_by=sort_by, sort_order=sort_order, search_query=search_query)

        cursor = self.conn.cursor()
        placeholders = ",".join("?" * len(tag_ids))

        valid_sort_columns = {"filename", "duration", "created_at", "favorite"}
        if sort_by not in valid_sort_columns:
            sort_by = "filename"
        sort_order = "DESC" if sort_order.lower() == "desc" else "ASC"

        search_condition = ""
        params = list(tag_ids)
        if search_query:
            search_condition = "AND v.filename LIKE ?"
            params.append(f"%{search_query}%")

        params.append(len(tag_ids))

        query = f"""
            SELECT v.* FROM videos v
            JOIN video_tags vt ON v.id = vt.video_id
            WHERE vt.tag_id IN ({placeholders}) {search_condition}
            GROUP BY v.id
            HAVING COUNT(DISTINCT vt.tag_id) = ?
            ORDER BY v.{sort_by} {sort_order}
        """
        cursor.execute(query, params)

        return [self._row_to_video(row) for row in cursor.fetchall()]

    def get_favorite_videos(self, sort_by: str = "filename", sort_order: str = "asc") -> list[Video]:
        """Get all favorite videos."""
        return self.get_videos(favorites_only=True, sort_by=sort_by, sort_order=sort_order)

    def get_recent_videos(self, limit: int = 20) -> list[Video]:
        """Get recently played videos."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM videos
            WHERE last_played IS NOT NULL
            ORDER BY last_played DESC
            LIMIT ?
        """, (limit,))
        return [self._row_to_video(row) for row in cursor.fetchall()]

    def toggle_favorite(self, video_id: int) -> bool:
        """Toggle favorite status and return new status."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT favorite FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        if row:
            new_status = 0 if row["favorite"] else 1
            cursor.execute("UPDATE videos SET favorite = ? WHERE id = ?", (new_status, video_id))
            self.conn.commit()
            return bool(new_status)
        return False

    def set_favorite(self, video_id: int, favorite: bool):
        """Set favorite status."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE videos SET favorite = ? WHERE id = ?", (1 if favorite else 0, video_id))
        self.conn.commit()

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

    def update_video_metadata(self, video_id: int, width: int, height: int,
                               fps: float, file_size: int):
        """Update video metadata."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE videos SET width = ?, height = ?, fps = ?, file_size = ?
            WHERE id = ?
        """, (width, height, fps, file_size, video_id))
        self.conn.commit()

    # Playback tracking
    def record_play(self, video_id: int):
        """Record that a video was played."""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            UPDATE videos SET last_played = ?, play_count = play_count + 1
            WHERE id = ?
        """, (now, video_id))

        cursor.execute("""
            INSERT INTO play_history (video_id, played_at) VALUES (?, ?)
        """, (video_id, now))

        self.conn.commit()

    def update_playback_position(self, video_id: int, position: float):
        """Update playback position for a video."""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE videos SET playback_position = ? WHERE id = ?",
            (position, video_id)
        )
        self.conn.commit()

    def get_playback_position(self, video_id: int) -> float:
        """Get saved playback position for a video."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT playback_position FROM videos WHERE id = ?", (video_id,))
        row = cursor.fetchone()
        return row["playback_position"] if row else 0.0

    def clear_playback_position(self, video_id: int):
        """Clear playback position (video finished)."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE videos SET playback_position = 0 WHERE id = ?", (video_id,))
        self.conn.commit()

    def get_play_history(self, limit: int = 50) -> list[PlayHistory]:
        """Get play history with video details."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT ph.id, ph.video_id, ph.played_at, v.*
            FROM play_history ph
            JOIN videos v ON ph.video_id = v.id
            ORDER BY ph.played_at DESC
            LIMIT ?
        """, (limit,))

        history = []
        for row in cursor.fetchall():
            video = self._row_to_video(row)
            history.append(PlayHistory(
                id=row["id"],
                video_id=row["video_id"],
                played_at=row["played_at"],
                video=video
            ))
        return history

    def clear_play_history(self):
        """Clear all play history."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM play_history")
        self.conn.commit()

    # Statistics
    def get_statistics(self) -> Statistics:
        """Get library statistics."""
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) as count, SUM(duration) as duration, SUM(file_size) as size FROM videos")
        row = cursor.fetchone()
        total_videos = row["count"] or 0
        total_duration = row["duration"] or 0.0
        total_size = row["size"] or 0

        cursor.execute("SELECT COUNT(*) as count FROM videos WHERE favorite = 1")
        favorites_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM tags")
        tags_count = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM folders")
        folders_count = cursor.fetchone()["count"]

        cursor.execute("""
            SELECT COUNT(*) as count FROM videos
            WHERE last_played IS NOT NULL
            AND datetime(last_played) > datetime('now', '-7 days')
        """)
        recently_played = cursor.fetchone()["count"]

        return Statistics(
            total_videos=total_videos,
            total_duration=total_duration,
            total_size=total_size,
            favorites_count=favorites_count,
            tags_count=tags_count,
            folders_count=folders_count,
            recently_played=recently_played
        )

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

    def get_tags_for_videos(self, video_ids: list[int]) -> dict[int, list[Tag]]:
        """Get tags for multiple videos in a single query."""
        if not video_ids:
            return {}
        cursor = self.conn.cursor()
        placeholders = ",".join("?" * len(video_ids))
        cursor.execute(f"""
            SELECT vt.video_id, t.id, t.name FROM tags t
            JOIN video_tags vt ON t.id = vt.tag_id
            WHERE vt.video_id IN ({placeholders})
            ORDER BY vt.video_id, t.name
        """, video_ids)
        result: dict[int, list[Tag]] = {}
        for row in cursor.fetchall():
            vid_id = row["video_id"]
            if vid_id not in result:
                result[vid_id] = []
            result[vid_id].append(Tag(id=row["id"], name=row["name"]))
        return result

    # Playlist operations
    def create_playlist(self, name: str) -> Playlist:
        """Create a new playlist."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO playlists (name) VALUES (?)",
            (name,)
        )
        self.conn.commit()
        return Playlist(id=cursor.lastrowid, name=name)

    def get_playlists(self) -> list[Playlist]:
        """Get all playlists."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM playlists ORDER BY name")
        return [Playlist(id=row["id"], name=row["name"], created_at=row["created_at"])
                for row in cursor.fetchall()]

    def get_playlist(self, playlist_id: int) -> Optional[Playlist]:
        """Get a playlist by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM playlists WHERE id = ?", (playlist_id,))
        row = cursor.fetchone()
        if row:
            return Playlist(id=row["id"], name=row["name"], created_at=row["created_at"])
        return None

    def update_playlist(self, playlist_id: int, name: str):
        """Update playlist name."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE playlists SET name = ? WHERE id = ?", (name, playlist_id))
        self.conn.commit()

    def delete_playlist(self, playlist_id: int):
        """Delete a playlist."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        self.conn.commit()

    def add_to_playlist(self, playlist_id: int, video_id: int):
        """Add a video to a playlist."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT MAX(position) FROM playlist_items WHERE playlist_id = ?",
            (playlist_id,)
        )
        row = cursor.fetchone()
        position = (row[0] or 0) + 1

        cursor.execute(
            "INSERT INTO playlist_items (playlist_id, video_id, position) VALUES (?, ?, ?)",
            (playlist_id, video_id, position)
        )
        self.conn.commit()

    def remove_from_playlist(self, playlist_id: int, video_id: int):
        """Remove a video from a playlist."""
        cursor = self.conn.cursor()
        cursor.execute(
            "DELETE FROM playlist_items WHERE playlist_id = ? AND video_id = ?",
            (playlist_id, video_id)
        )
        self.conn.commit()

    def get_playlist_videos(self, playlist_id: int) -> list[Video]:
        """Get all videos in a playlist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT v.* FROM videos v
            JOIN playlist_items pi ON v.id = pi.video_id
            WHERE pi.playlist_id = ?
            ORDER BY pi.position
        """, (playlist_id,))
        return [self._row_to_video(row) for row in cursor.fetchall()]

    def reorder_playlist(self, playlist_id: int, video_ids: list[int]):
        """Reorder videos in a playlist."""
        cursor = self.conn.cursor()
        for i, video_id in enumerate(video_ids):
            cursor.execute(
                "UPDATE playlist_items SET position = ? WHERE playlist_id = ? AND video_id = ?",
                (i, playlist_id, video_id)
            )
        self.conn.commit()

    # Smart collection operations
    def create_smart_collection(self, name: str, filter_type: str,
                                 filter_operator: str, filter_value: str) -> SmartCollection:
        """Create a smart collection."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO smart_collections (name, filter_type, filter_operator, filter_value) VALUES (?, ?, ?, ?)",
            (name, filter_type, filter_operator, filter_value)
        )
        self.conn.commit()
        return SmartCollection(
            id=cursor.lastrowid, name=name,
            filter_type=filter_type, filter_operator=filter_operator, filter_value=filter_value
        )

    def get_smart_collections(self) -> list[SmartCollection]:
        """Get all smart collections."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM smart_collections ORDER BY name")
        return [SmartCollection(
            id=row["id"], name=row["name"],
            filter_type=row["filter_type"], filter_operator=row["filter_operator"],
            filter_value=row["filter_value"]
        ) for row in cursor.fetchall()]

    def delete_smart_collection(self, collection_id: int):
        """Delete a smart collection."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM smart_collections WHERE id = ?", (collection_id,))
        self.conn.commit()

    def get_smart_collection_videos(self, collection: SmartCollection) -> list[Video]:
        """Get videos matching smart collection criteria."""
        cursor = self.conn.cursor()

        # Build query based on filter type
        if collection.filter_type == "duration":
            value = float(collection.filter_value) * 60  # Convert minutes to seconds
            if collection.filter_operator == "gt":
                condition = f"duration > {value}"
            elif collection.filter_operator == "lt":
                condition = f"duration < {value}"
            else:
                condition = f"duration = {value}"
        elif collection.filter_type == "resolution":
            if collection.filter_value == "4k":
                condition = "width >= 3840"
            elif collection.filter_value == "1080p":
                condition = "height >= 1080 AND height < 2160"
            elif collection.filter_value == "720p":
                condition = "height >= 720 AND height < 1080"
            else:
                condition = "height < 720"
        elif collection.filter_type == "size":
            value = float(collection.filter_value) * 1024 * 1024  # Convert MB to bytes
            if collection.filter_operator == "gt":
                condition = f"file_size > {value}"
            elif collection.filter_operator == "lt":
                condition = f"file_size < {value}"
            else:
                condition = f"file_size = {value}"
        elif collection.filter_type == "recent":
            days = int(collection.filter_value)
            condition = f"datetime(created_at) > datetime('now', '-{days} days')"
        else:
            return []

        query = f"SELECT * FROM videos WHERE {condition} ORDER BY filename"
        cursor.execute(query)
        return [self._row_to_video(row) for row in cursor.fetchall()]

    # Duplicate detection
    def update_video_hash(self, video_id: int, file_hash: str):
        """Update file hash for a video."""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE videos SET file_hash = ? WHERE id = ?", (file_hash, video_id))
        self.conn.commit()

    def find_duplicates(self) -> list[list[Video]]:
        """Find duplicate videos by file hash."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT file_hash, COUNT(*) as cnt FROM videos
            WHERE file_hash IS NOT NULL AND file_hash != ''
            GROUP BY file_hash HAVING cnt > 1
        """)
        duplicate_groups = []
        for row in cursor.fetchall():
            cursor.execute("SELECT * FROM videos WHERE file_hash = ?", (row["file_hash"],))
            videos = [self._row_to_video(r) for r in cursor.fetchall()]
            duplicate_groups.append(videos)
        return duplicate_groups

    def get_videos_without_hash(self) -> list[Video]:
        """Get videos that don't have a file hash yet."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM videos WHERE file_hash IS NULL OR file_hash = ''")
        return [self._row_to_video(row) for row in cursor.fetchall()]

    # Missing files check
    def find_missing_files(self) -> list[Video]:
        """Find videos whose files no longer exist."""
        import os
        videos = self.get_videos()
        return [v for v in videos if not os.path.exists(v.path)]

    # Settings operations
    def get_setting(self, key: str, default: str = "") -> str:
        """Get a setting value."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        """Set a setting value."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.conn.commit()

    def get_app_settings(self) -> AppSettings:
        """Get all application settings."""
        return AppSettings(
            theme=self.get_setting("theme", "dark"),
            thumbnail_size=int(self.get_setting("thumbnail_size", "180")),
            window_geometry=self.get_setting("window_geometry"),
            splitter_sizes=self.get_setting("splitter_sizes"),
        )

    def save_app_settings(self, settings: AppSettings):
        """Save application settings."""
        self.set_setting("theme", settings.theme)
        self.set_setting("thumbnail_size", str(settings.thumbnail_size))
        if settings.window_geometry:
            self.set_setting("window_geometry", settings.window_geometry)
        if settings.splitter_sizes:
            self.set_setting("splitter_sizes", settings.splitter_sizes)

    # Recently added videos
    def get_recently_added(self, days: int = 7, limit: int = 50) -> list[Video]:
        """Get recently added videos."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM videos
            WHERE datetime(created_at) > datetime('now', ? || ' days')
            ORDER BY created_at DESC
            LIMIT ?
        """, (f"-{days}", limit))
        return [self._row_to_video(row) for row in cursor.fetchall()]

    # Advanced search
    def advanced_search(self, search_query: str = "", min_duration: float = 0,
                        max_duration: float = 0, min_resolution: int = 0,
                        min_size: int = 0, max_size: int = 0,
                        tags: list[int] = None) -> list[Video]:
        """Advanced search with multiple criteria."""
        cursor = self.conn.cursor()
        conditions = []
        params = []

        if search_query:
            conditions.append("filename LIKE ?")
            params.append(f"%{search_query}%")

        if min_duration > 0:
            conditions.append("duration >= ?")
            params.append(min_duration)

        if max_duration > 0:
            conditions.append("duration <= ?")
            params.append(max_duration)

        if min_resolution > 0:
            conditions.append("height >= ?")
            params.append(min_resolution)

        if min_size > 0:
            conditions.append("file_size >= ?")
            params.append(min_size)

        if max_size > 0:
            conditions.append("file_size <= ?")
            params.append(max_size)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM videos {where_clause} ORDER BY filename"
        cursor.execute(query, params)
        videos = [self._row_to_video(row) for row in cursor.fetchall()]

        # Filter by tags if specified
        if tags:
            video_ids = set()
            for tag_id in tags:
                cursor.execute(
                    "SELECT video_id FROM video_tags WHERE tag_id = ?",
                    (tag_id,)
                )
                tag_video_ids = {row["video_id"] for row in cursor.fetchall()}
                video_ids = video_ids.intersection(tag_video_ids) if video_ids else tag_video_ids
            videos = [v for v in videos if v.id in video_ids]

        return videos

    # Auto-tagging
    def auto_tag_video(self, video_id: int, path: str):
        """Auto-generate tags from filename and path."""
        import os
        import re

        filename = os.path.basename(path)
        parent_folder = os.path.basename(os.path.dirname(path))

        # Clean filename: remove extension and common patterns
        name = os.path.splitext(filename)[0]
        name = re.sub(r'[\[\]\(\)\{\}]', ' ', name)
        name = re.sub(r'[_\-\.]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()

        # Extract potential tags
        words = set()
        for word in name.split():
            if len(word) >= 3 and not word.isdigit():
                words.add(word.lower())

        if parent_folder and len(parent_folder) >= 3:
            words.add(parent_folder.lower())

        # Add existing tags that match
        existing_tags = self.get_tags()
        tag_names = {t.name.lower(): t for t in existing_tags}

        for word in words:
            if word in tag_names:
                self.add_video_tag(video_id, tag_names[word].id)

    def close(self):
        """Close database connection."""
        self.conn.close()
