"""Virtual-scroll video views using QListView + custom delegates."""

from PyQt6.QtWidgets import (
    QListView, QAbstractItemView, QStyledItemDelegate, QStyle,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QFontMetrics, QPixmap,
    QPainterPath, QBrush,
)

from ..database import Video
from ..video_utils import format_file_size
from .video_model import VideoModel, VideoRole, ThumbnailRole, TagsRole


# ── Grid delegate ─────────────────────────────────────────────────────────────

class VideoGridDelegate(QStyledItemDelegate):
    """Paints a card-style grid item: thumbnail + title + duration."""

    ITEM_W  = 190
    ITEM_H  = 170
    THUMB_W = 162
    THUMB_H = 91
    RADIUS  = 8

    def paint(self, painter: QPainter, option, index):
        video: Video = index.data(VideoRole)
        if video is None:
            return

        thumb: QPixmap = index.data(ThumbnailRole)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = option.rect.adjusted(3, 3, -3, -3)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered  = bool(option.state & QStyle.StateFlag.State_MouseOver)

        if selected:
            bg, border, bw = QColor("#2a4a6a"), QColor("#3498db"), 2
        elif hovered:
            bg, border, bw = QColor("#3d3d3d"), QColor("#4d4d4d"), 1
        else:
            bg, border, bw = QColor("#2d2d2d"), QColor("#3d3d3d"), 1

        path = QPainterPath()
        path.addRoundedRect(float(r.x()), float(r.y()),
                            float(r.width()), float(r.height()),
                            self.RADIUS, self.RADIUS)
        painter.fillPath(path, QBrush(bg))
        painter.setPen(QPen(border, bw))
        painter.drawPath(path)

        # Thumbnail
        pad_x     = (r.width() - self.THUMB_W) // 2
        thumb_rect = QRect(r.left() + pad_x, r.top() + 8, self.THUMB_W, self.THUMB_H)
        if thumb and not thumb.isNull():
            ox = thumb_rect.left() + (self.THUMB_W - thumb.width()) // 2
            oy = thumb_rect.top()  + (self.THUMB_H - thumb.height()) // 2
            painter.drawPixmap(ox, oy, thumb)
        else:
            painter.fillRect(thumb_rect, QColor("#1a1a1a"))
            painter.setPen(QColor("#555"))
            f = painter.font()
            f.setPixelSize(10)
            painter.setFont(f)
            painter.drawText(thumb_rect, Qt.AlignmentFlag.AlignCenter, "No Preview")

        # Title (word-wrap, max 2 lines)
        title_rect = QRect(r.left() + 6, thumb_rect.bottom() + 6,
                           r.width() - 12, 32)
        f = QFont()
        f.setPixelSize(11)
        painter.setFont(f)
        painter.setPen(QColor("#e0e0e0"))
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            | Qt.TextFlag.TextWordWrap,
            video.filename,
        )

        # Duration
        dur_rect = QRect(r.left() + 6, title_rect.bottom() + 2,
                         r.width() - 12, 16)
        f.setPixelSize(10)
        painter.setFont(f)
        painter.setPen(QColor("#888"))
        painter.drawText(
            dur_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            video.duration_str,
        )

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(self.ITEM_W, self.ITEM_H)


# ── List delegate ─────────────────────────────────────────────────────────────

class VideoListDelegate(QStyledItemDelegate):
    """Paints a row-style list item: thumbnail + title + metadata + tags."""

    ITEM_H  = 66
    THUMB_W = 80
    THUMB_H = 45

    def paint(self, painter: QPainter, option, index):
        video: Video = index.data(VideoRole)
        if video is None:
            return

        thumb: QPixmap = index.data(ThumbnailRole)
        tags:  list    = index.data(TagsRole) or []

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = option.rect.adjusted(4, 2, -4, -2)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered  = bool(option.state & QStyle.StateFlag.State_MouseOver)

        if selected:
            bg, border, bw = QColor("#2a4a6a"), QColor("#3498db"), 2
        elif hovered:
            bg, border, bw = QColor("#3d3d3d"), QColor("#4d4d4d"), 1
        else:
            bg, border, bw = QColor("#2d2d2d"), QColor("#3d3d3d"), 1

        path = QPainterPath()
        path.addRoundedRect(float(r.x()), float(r.y()),
                            float(r.width()), float(r.height()), 6, 6)
        painter.fillPath(path, QBrush(bg))
        painter.setPen(QPen(border, bw))
        painter.drawPath(path)

        # Thumbnail
        thumb_rect = QRect(
            r.left() + 6,
            r.top() + (r.height() - self.THUMB_H) // 2,
            self.THUMB_W, self.THUMB_H,
        )
        if thumb and not thumb.isNull():
            ox = thumb_rect.left() + (self.THUMB_W - thumb.width()) // 2
            oy = thumb_rect.top()  + (self.THUMB_H - thumb.height()) // 2
            painter.drawPixmap(ox, oy, thumb)
        else:
            painter.fillRect(thumb_rect, QColor("#1a1a1a"))
            painter.setPen(QColor("#555"))
            f = QFont()
            f.setPixelSize(9)
            painter.setFont(f)
            painter.drawText(thumb_rect, Qt.AlignmentFlag.AlignCenter, "No Preview")

        # Text area (reserve right side for tags if present)
        text_x = thumb_rect.right() + 10
        tag_col_w = 130 if tags else 0
        text_w = r.right() - text_x - tag_col_w - 6

        # Title
        f = QFont()
        f.setPixelSize(13)
        f.setBold(True)
        painter.setFont(f)
        painter.setPen(QColor("#e0e0e0"))
        fm = QFontMetrics(f)
        elided = fm.elidedText(video.filename, Qt.TextElideMode.ElideRight, text_w)
        title_rect = QRect(text_x, r.top() + 8, text_w, 20)
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided,
        )

        # Metadata line
        meta_parts = [f"Duration: {video.duration_str}"]
        if video.file_size:
            meta_parts.append(f"Size: {format_file_size(video.file_size)}")
        f.setPixelSize(11)
        f.setBold(False)
        painter.setFont(f)
        painter.setPen(QColor("#888"))
        meta_rect = QRect(text_x, title_rect.bottom() + 4, text_w, 16)
        painter.drawText(
            meta_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "  |  ".join(meta_parts),
        )

        # Tags (right-aligned column)
        if tags:
            tf = QFont()
            tf.setPixelSize(10)
            painter.setFont(tf)
            tfm = QFontMetrics(tf)
            tag_x = r.right() - tag_col_w
            tag_y = r.top() + (r.height() - 20) // 2
            for tag in tags[:3]:
                tw = tfm.horizontalAdvance(tag.name) + 14
                tag_rect = QRect(tag_x, tag_y, tw, 20)
                if tag_rect.right() > r.right() - 4:
                    break
                painter.fillRect(tag_rect, QColor("#4a4a4a"))
                painter.setPen(QColor("#e0e0e0"))
                painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, tag.name)
                tag_x += tw + 4

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(400, self.ITEM_H)


# ── Unified view ──────────────────────────────────────────────────────────────

class VideoView(QListView):
    """
    QListView-based virtual-scroll view.
    mode='grid'  → IconMode with VideoGridDelegate
    mode='list'  → ListMode with VideoListDelegate

    Only the ~10-20 visible items are ever painted, so 1000+ item
    libraries open instantly.
    """

    video_selected       = pyqtSignal(int)
    video_double_clicked = pyqtSignal(int)
    context_menu_requested = pyqtSignal(int, object)

    def __init__(self, mode: str = "grid", db=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.db   = db

        self._model = VideoModel()
        self.setModel(self._model)
        self.setMouseTracking(True)

        if mode == "grid":
            self._delegate = VideoGridDelegate()
            self.setViewMode(QListView.ViewMode.IconMode)
            gw = VideoGridDelegate.ITEM_W + 6
            gh = VideoGridDelegate.ITEM_H + 6
            self.setGridSize(QSize(gw, gh))
            self.setResizeMode(QListView.ResizeMode.Adjust)
            self.setWordWrap(True)
        else:
            self._delegate = VideoListDelegate()
            self.setViewMode(QListView.ViewMode.ListMode)
            self.setResizeMode(QListView.ResizeMode.Adjust)

        self.setItemDelegate(self._delegate)
        self.setUniformItemSizes(True)
        self.setSpacing(2)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setStyleSheet("""
            QListView {
                background-color: #1e1e1e;
                border: none;
            }
            QListView::item:selected { background: transparent; }
            QListView::item:hover    { background: transparent; }
        """)

        self.selectionModel().currentChanged.connect(self._on_current_changed)
        self.doubleClicked.connect(self._on_double_clicked)

    # ── public API ────────────────────────────────────────────────────────────

    def set_videos(self, videos: list[Video]):
        """Load videos into the model (replaces the old set_videos on grid/list widgets)."""
        tags_map: dict[int, list] = {}
        if self.mode == "list" and self.db and videos:
            tags_map = self.db.get_tags_for_videos([v.id for v in videos])
        self._model.set_videos(videos, tags_map)

    def set_database(self, db):
        self.db = db

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_current_changed(self, current, _previous):
        video = self._model.get_video(current.row())
        if video:
            self.video_selected.emit(video.id)

    def _on_double_clicked(self, index):
        video = self._model.get_video(index.row())
        if video:
            self.video_double_clicked.emit(video.id)

    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            video = self._model.get_video(index.row())
            if video:
                self.context_menu_requested.emit(video.id, event.globalPos())


# ── Backward-compat aliases (used in __init__.py / main_window.py) ────────────
VideoGridWidget = VideoView   # type alias – callers can keep old name
VideoListWidget = VideoView   # type alias
