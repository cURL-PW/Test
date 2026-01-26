"""Video item widgets for grid and list views."""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QSizePolicy, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QAction

from ..database import Video
from ..video_utils import format_duration, format_file_size


class VideoThumbnail(QLabel):
    """Thumbnail widget for video."""

    def __init__(self, size: QSize = QSize(160, 90), parent=None):
        super().__init__(parent)
        self.thumb_size = size
        self.setFixedSize(size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border-radius: 4px;
            }
        """)
        self._set_placeholder()

    def _set_placeholder(self):
        """Set placeholder when no thumbnail."""
        self.setText("No Preview")
        self.setStyleSheet(self.styleSheet() + "color: #666;")

    def set_thumbnail(self, path: str):
        """Load and display thumbnail."""
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    self.thumb_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.setPixmap(scaled)
                return
        self._set_placeholder()


class VideoItemWidget(QFrame):
    """Widget representing a single video item in grid view."""

    clicked = pyqtSignal(int)
    double_clicked = pyqtSignal(int)
    context_menu_requested = pyqtSignal(int, object)

    def __init__(self, video: Video, parent=None):
        super().__init__(parent)
        self.video = video
        self.selected = False

        self.setFixedSize(180, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.thumbnail = VideoThumbnail(QSize(160, 90))
        if video.thumbnail_path:
            self.thumbnail.set_thumbnail(video.thumbnail_path)
        layout.addWidget(self.thumbnail)

        self.title_label = QLabel(video.filename)
        self.title_label.setWordWrap(True)
        self.title_label.setMaximumHeight(32)
        self.title_label.setStyleSheet("font-size: 11px;")
        self.title_label.setToolTip(video.filename)
        layout.addWidget(self.title_label)

        self.duration_label = QLabel(video.duration_str)
        self.duration_label.setStyleSheet("font-size: 10px; color: #888;")
        layout.addWidget(self.duration_label)

    def _update_style(self):
        """Update widget style based on selection state."""
        if self.selected:
            self.setStyleSheet("""
                VideoItemWidget {
                    background-color: #2a4a6a;
                    border: 2px solid #3498db;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                VideoItemWidget {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 8px;
                }
                VideoItemWidget:hover {
                    background-color: #3d3d3d;
                    border: 1px solid #4d4d4d;
                }
            """)

    def set_selected(self, selected: bool):
        """Set selection state."""
        self.selected = selected
        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.video.id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.video.id)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        self.context_menu_requested.emit(self.video.id, event.globalPos())


class VideoListItemWidget(QFrame):
    """Widget representing a single video item in list view."""

    clicked = pyqtSignal(int)
    double_clicked = pyqtSignal(int)
    context_menu_requested = pyqtSignal(int, object)

    def __init__(self, video: Video, tags: list = None, parent=None):
        super().__init__(parent)
        self.video = video
        self.selected = False

        self.setFixedHeight(60)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        self.thumbnail = VideoThumbnail(QSize(80, 45))
        if video.thumbnail_path:
            self.thumbnail.set_thumbnail(video.thumbnail_path)
        layout.addWidget(self.thumbnail)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self.title_label = QLabel(video.filename)
        self.title_label.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.title_label.setToolTip(video.filename)
        info_layout.addWidget(self.title_label)

        meta_layout = QHBoxLayout()
        meta_layout.setSpacing(16)

        self.duration_label = QLabel(f"Duration: {video.duration_str}")
        self.duration_label.setStyleSheet("font-size: 11px; color: #888;")
        meta_layout.addWidget(self.duration_label)

        try:
            size = os.path.getsize(video.path)
            size_label = QLabel(f"Size: {format_file_size(size)}")
            size_label.setStyleSheet("font-size: 11px; color: #888;")
            meta_layout.addWidget(size_label)
        except Exception:
            pass

        meta_layout.addStretch()
        info_layout.addLayout(meta_layout)

        layout.addLayout(info_layout, 1)

        if tags:
            tags_layout = QHBoxLayout()
            tags_layout.setSpacing(4)
            for tag in tags[:3]:
                tag_label = QLabel(tag.name)
                tag_label.setStyleSheet(f"""
                    background-color: {tag.color};
                    color: white;
                    padding: 2px 6px;
                    border-radius: 8px;
                    font-size: 10px;
                """)
                tags_layout.addWidget(tag_label)
            if len(tags) > 3:
                more_label = QLabel(f"+{len(tags) - 3}")
                more_label.setStyleSheet("color: #888; font-size: 10px;")
                tags_layout.addWidget(more_label)
            layout.addLayout(tags_layout)

    def _update_style(self):
        """Update widget style based on selection state."""
        if self.selected:
            self.setStyleSheet("""
                VideoListItemWidget {
                    background-color: #2a4a6a;
                    border: 2px solid #3498db;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                VideoListItemWidget {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 6px;
                }
                VideoListItemWidget:hover {
                    background-color: #3d3d3d;
                }
            """)

    def set_selected(self, selected: bool):
        """Set selection state."""
        self.selected = selected
        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.video.id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.video.id)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        self.context_menu_requested.emit(self.video.id, event.globalPos())


class VideoGridWidget(QScrollArea):
    """Grid view widget for displaying videos."""

    video_selected = pyqtSignal(int)
    video_double_clicked = pyqtSignal(int)
    context_menu_requested = pyqtSignal(int, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.videos: dict[int, VideoItemWidget] = {}
        self.selected_id = None

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { border: none; background-color: #1e1e1e; }")

        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(12, 12, 12, 12)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.setWidget(self.container)

    def set_videos(self, videos: list[Video]):
        """Set videos to display."""
        for widget in self.videos.values():
            widget.deleteLater()
        self.videos.clear()
        self.selected_id = None

        col = 0
        row = 0
        cols = max(1, self.width() // 195)

        for video in videos:
            widget = VideoItemWidget(video)
            widget.clicked.connect(self._on_video_clicked)
            widget.double_clicked.connect(self.video_double_clicked.emit)
            widget.context_menu_requested.connect(self.context_menu_requested.emit)

            self.grid_layout.addWidget(widget, row, col)
            self.videos[video.id] = widget

            col += 1
            if col >= cols:
                col = 0
                row += 1

    def _on_video_clicked(self, video_id: int):
        """Handle video click."""
        if self.selected_id and self.selected_id in self.videos:
            self.videos[self.selected_id].set_selected(False)

        self.selected_id = video_id
        if video_id in self.videos:
            self.videos[video_id].set_selected(True)

        self.video_selected.emit(video_id)

    def resizeEvent(self, event):
        """Re-layout on resize."""
        super().resizeEvent(event)
        if self.videos:
            videos = [w.video for w in self.videos.values()]
            self.set_videos(videos)


class VideoListWidget(QScrollArea):
    """List view widget for displaying videos."""

    video_selected = pyqtSignal(int)
    video_double_clicked = pyqtSignal(int)
    context_menu_requested = pyqtSignal(int, object)

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.videos: dict[int, VideoListItemWidget] = {}
        self.selected_id = None

        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea { border: none; background-color: #1e1e1e; }")

        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setSpacing(6)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setWidget(self.container)

    def set_database(self, db):
        """Set database reference."""
        self.db = db

    def set_videos(self, videos: list[Video]):
        """Set videos to display."""
        for widget in self.videos.values():
            widget.deleteLater()
        self.videos.clear()
        self.selected_id = None

        for video in videos:
            tags = self.db.get_video_tags(video.id) if self.db else []
            widget = VideoListItemWidget(video, tags)
            widget.clicked.connect(self._on_video_clicked)
            widget.double_clicked.connect(self.video_double_clicked.emit)
            widget.context_menu_requested.connect(self.context_menu_requested.emit)

            self.list_layout.addWidget(widget)
            self.videos[video.id] = widget

    def _on_video_clicked(self, video_id: int):
        """Handle video click."""
        if self.selected_id and self.selected_id in self.videos:
            self.videos[self.selected_id].set_selected(False)

        self.selected_id = video_id
        if video_id in self.videos:
            self.videos[video_id].set_selected(True)

        self.video_selected.emit(video_id)
