"""Video data model for virtual-scroll views."""

import os
from PyQt6.QtCore import (
    QAbstractListModel, Qt, QModelIndex, QRunnable, QThreadPool,
    pyqtSignal, QObject, QSize,
)
from PyQt6.QtGui import QPixmap

from ..database import Video

# ── Custom item-data roles ────────────────────────────────────────────────────
VideoRole    = Qt.ItemDataRole.UserRole       # Video dataclass
ThumbnailRole = Qt.ItemDataRole.UserRole + 1  # QPixmap (async)
TagsRole     = Qt.ItemDataRole.UserRole + 2   # list[Tag]


# ── Background thumbnail loader ───────────────────────────────────────────────

class _ThumbSignals(QObject):
    loaded = pyqtSignal(int, QPixmap)   # video_id, pixmap


class ThumbnailLoader(QRunnable):
    """Loads one thumbnail from disk on a thread-pool thread."""

    def __init__(self, video_id: int, thumb_path: str,
                 target_size: QSize, signals: "_ThumbSignals"):
        super().__init__()
        self._video_id   = video_id
        self._thumb_path = thumb_path
        self._target     = target_size
        self.signals     = signals
        self.setAutoDelete(True)

    def run(self):                              # called from worker thread
        pixmap = QPixmap()
        if self._thumb_path and os.path.exists(self._thumb_path):
            raw = QPixmap(self._thumb_path)
            if not raw.isNull():
                pixmap = raw.scaled(
                    self._target,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
        self.signals.loaded.emit(self._video_id, pixmap)


# ── Model ─────────────────────────────────────────────────────────────────────

class VideoModel(QAbstractListModel):
    """
    Stores a flat list of Video objects.
    Thumbnails are loaded asynchronously; only a QPixmap() placeholder is
    returned until the background load completes, at which point
    dataChanged is emitted so the view repaints the affected row.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._videos:     list[Video]        = []
        self._tags:       dict[int, list]    = {}   # video_id -> [Tag]
        self._thumbnails: dict[int, QPixmap] = {}   # video_id -> pixmap
        self._loading:    set[int]           = set()
        self._pool        = QThreadPool.globalInstance()
        self._thumb_size  = QSize(160, 90)          # default (grid)

    # ── public API ────────────────────────────────────────────────────────────

    def set_videos(self, videos: list[Video], tags_map: dict[int, list] | None = None):
        """Replace the entire list.  tags_map: {video_id: [Tag, ...]}"""
        self.beginResetModel()
        self._videos     = videos
        self._tags       = tags_map or {}
        self._thumbnails.clear()
        self._loading.clear()
        self.endResetModel()

    def set_thumb_size(self, size: QSize):
        """Change thumbnail target size and flush the cache."""
        self._thumb_size = size
        self._thumbnails.clear()
        self._loading.clear()
        if self._videos:
            self.dataChanged.emit(
                self.index(0),
                self.index(len(self._videos) - 1),
                [ThumbnailRole],
            )

    def get_video(self, row: int) -> Video | None:
        if 0 <= row < len(self._videos):
            return self._videos[row]
        return None

    def get_video_by_id(self, video_id: int) -> Video | None:
        for v in self._videos:
            if v.id == video_id:
                return v
        return None

    # ── QAbstractItemModel interface ──────────────────────────────────────────

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._videos)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._videos):
            return None
        video = self._videos[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return video.filename
        if role == VideoRole:
            return video
        if role == ThumbnailRole:
            return self._get_thumbnail(video)
        if role == TagsRole:
            return self._tags.get(video.id, [])
        return None

    # ── internals ─────────────────────────────────────────────────────────────

    def _get_thumbnail(self, video: Video) -> QPixmap:
        vid_id = video.id
        if vid_id in self._thumbnails:
            return self._thumbnails[vid_id]
        if vid_id not in self._loading:
            self._loading.add(vid_id)
            signals = _ThumbSignals()
            signals.loaded.connect(self._on_thumbnail_loaded)
            loader = ThumbnailLoader(vid_id, video.thumbnail_path,
                                     self._thumb_size, signals)
            self._pool.start(loader)
        return QPixmap()   # placeholder while loading

    def _on_thumbnail_loaded(self, video_id: int, pixmap: QPixmap):
        self._loading.discard(video_id)
        self._thumbnails[video_id] = pixmap       # cache even if null
        for i, v in enumerate(self._videos):
            if v.id == video_id:
                idx = self.index(i)
                self.dataChanged.emit(idx, idx, [ThumbnailRole])
                break
