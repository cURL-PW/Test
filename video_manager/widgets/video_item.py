"""Virtual-scroll video views using QListView + custom delegates.

Delegates pull colors from the active theme (video_manager.theme.current())
so both dark and light modes render consistently.
"""

from PyQt6.QtWidgets import (
    QListView, QAbstractItemView, QStyledItemDelegate, QStyle,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QFontMetrics, QPixmap,
    QPainterPath, QBrush,
)

from ..database import Video
from ..video_utils import format_file_size
from .. import theme
from .video_model import VideoModel, VideoRole, ThumbnailRole, TagsRole


def _rounded(painter: QPainter, rect: QRect, radius: float,
             fill: QColor | None = None,
             border: QColor | None = None, border_width: int = 1):
    """Draw a rounded rect with optional fill and border."""
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect), radius, radius)
    if fill is not None:
        painter.fillPath(path, QBrush(fill))
    if border is not None:
        painter.setPen(QPen(border, border_width))
        painter.drawPath(path)
    return path


def _draw_thumbnail(painter: QPainter, thumb_rect: QRect,
                    thumb: QPixmap, video: Video, radius: float,
                    badge_font_px: int = 10):
    """Rounded thumbnail with duration badge, favorite star and progress bar."""
    t = theme.current()

    clip = QPainterPath()
    clip.addRoundedRect(QRectF(thumb_rect), radius, radius)
    painter.save()
    painter.setClipPath(clip)

    painter.fillRect(thumb_rect, QColor(t.thumb_bg))
    if thumb and not thumb.isNull():
        ox = thumb_rect.left() + (thumb_rect.width() - thumb.width()) // 2
        oy = thumb_rect.top() + (thumb_rect.height() - thumb.height()) // 2
        painter.drawPixmap(ox, oy, thumb)
    else:
        painter.setPen(QColor(t.text_faint))
        f = QFont()
        f.setPixelSize(max(9, badge_font_px))
        painter.setFont(f)
        painter.drawText(thumb_rect, Qt.AlignmentFlag.AlignCenter, "No Preview")

    # watch progress along the bottom edge
    if video.duration > 0 and video.playback_position > 0:
        pct = min(1.0, video.playback_position / video.duration)
        bar = QRect(thumb_rect.left(), thumb_rect.bottom() - 2,
                    int(thumb_rect.width() * pct), 3)
        painter.fillRect(bar, QColor(t.accent))

    painter.restore()

    # duration badge (bottom-right)
    if video.duration > 0:
        f = QFont()
        f.setPixelSize(badge_font_px)
        f.setBold(True)
        fm = QFontMetrics(f)
        text = video.duration_str
        bw = fm.horizontalAdvance(text) + 10
        bh = fm.height() + 2
        badge = QRect(thumb_rect.right() - bw - 4,
                      thumb_rect.bottom() - bh - 4, bw, bh)
        _rounded(painter, badge, 4, fill=QColor(20, 23, 28, 210))
        painter.setFont(f)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, text)

    # favorite star (top-right)
    if video.favorite:
        star = QRect(thumb_rect.right() - 22, thumb_rect.top() + 4, 18, 18)
        _rounded(painter, star, 9, fill=QColor(20, 23, 28, 210))
        f = QFont()
        f.setPixelSize(11)
        painter.setFont(f)
        painter.setPen(QColor(t.warning))
        painter.drawText(star, Qt.AlignmentFlag.AlignCenter, "★")


def _card_colors(option):
    """Resolve card background/border colors from state + theme."""
    t = theme.current()
    selected = bool(option.state & QStyle.StateFlag.State_Selected)
    hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
    if selected:
        return QColor(t.surface3), QColor(t.accent), 2
    if hovered:
        return QColor(t.surface2), QColor(t.border_strong), 1
    return QColor(t.surface), QColor(t.border), 1


# ── Grid delegate ─────────────────────────────────────────────────────────────

class VideoGridDelegate(QStyledItemDelegate):
    """Card-style grid item: rounded thumbnail + title + metadata."""

    ITEM_W  = 190
    ITEM_H  = 172
    THUMB_W = 164
    THUMB_H = 92
    RADIUS  = 10

    def paint(self, painter: QPainter, option, index):
        video: Video = index.data(VideoRole)
        if video is None:
            return
        t = theme.current()
        thumb: QPixmap = index.data(ThumbnailRole)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = option.rect.adjusted(4, 4, -4, -4)
        bg, border, bw = _card_colors(option)
        _rounded(painter, r, self.RADIUS, fill=bg, border=border, border_width=bw)

        pad_x = (r.width() - self.THUMB_W) // 2
        thumb_rect = QRect(r.left() + pad_x, r.top() + 8,
                           self.THUMB_W, self.THUMB_H)
        _draw_thumbnail(painter, thumb_rect, thumb, video, 6)

        # title (2 lines max)
        title_rect = QRect(r.left() + 8, thumb_rect.bottom() + 7,
                           r.width() - 16, 30)
        f = QFont()
        f.setPixelSize(11)
        painter.setFont(f)
        painter.setPen(QColor(t.text))
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            | Qt.TextFlag.TextWordWrap,
            video.filename,
        )

        # metadata line: resolution or size
        meta = ""
        if video.width and video.height:
            meta = video.resolution_str
        elif video.file_size:
            meta = format_file_size(video.file_size)
        if meta:
            meta_rect = QRect(r.left() + 8, title_rect.bottom() + 3,
                              r.width() - 16, 14)
            f.setPixelSize(10)
            painter.setFont(f)
            painter.setPen(QColor(t.text_muted))
            painter.drawText(
                meta_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                meta,
            )

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(self.ITEM_W, self.ITEM_H)


# ── List delegate ─────────────────────────────────────────────────────────────

class VideoListDelegate(QStyledItemDelegate):
    """Row-style list item: thumbnail + title + metadata + tag pills."""

    ITEM_H  = 68
    THUMB_W = 84
    THUMB_H = 47

    def paint(self, painter: QPainter, option, index):
        video: Video = index.data(VideoRole)
        if video is None:
            return
        t = theme.current()
        thumb: QPixmap = index.data(ThumbnailRole)
        tags: list = index.data(TagsRole) or []

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = option.rect.adjusted(4, 2, -4, -2)
        bg, border, bw = _card_colors(option)
        _rounded(painter, r, 8, fill=bg, border=border, border_width=bw)

        thumb_rect = QRect(
            r.left() + 8,
            r.top() + (r.height() - self.THUMB_H) // 2,
            self.THUMB_W, self.THUMB_H,
        )
        _draw_thumbnail(painter, thumb_rect, thumb, video, 5, badge_font_px=9)

        text_x = thumb_rect.right() + 12
        tag_col_w = 140 if tags else 0
        text_w = r.right() - text_x - tag_col_w - 8

        # title
        f = QFont()
        f.setPixelSize(13)
        f.setBold(True)
        painter.setFont(f)
        painter.setPen(QColor(t.text))
        fm = QFontMetrics(f)
        elided = fm.elidedText(video.filename,
                               Qt.TextElideMode.ElideRight, text_w)
        title_rect = QRect(text_x, r.top() + 10, text_w, 20)
        painter.drawText(
            title_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided,
        )

        # metadata
        meta_parts = []
        if video.width and video.height:
            meta_parts.append(video.resolution_str)
        if video.file_size:
            meta_parts.append(format_file_size(video.file_size))
        if video.play_count:
            meta_parts.append(f"{video.play_count} plays")
        f.setPixelSize(11)
        f.setBold(False)
        painter.setFont(f)
        painter.setPen(QColor(t.text_muted))
        meta_rect = QRect(text_x, title_rect.bottom() + 4, text_w, 16)
        painter.drawText(
            meta_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "  ·  ".join(meta_parts),
        )

        # tag pills (right-aligned column)
        if tags:
            tf = QFont()
            tf.setPixelSize(10)
            painter.setFont(tf)
            tfm = QFontMetrics(tf)
            tag_x = r.right() - tag_col_w
            tag_y = r.top() + (r.height() - 20) // 2
            for tag in tags[:3]:
                tw = tfm.horizontalAdvance(tag.name) + 16
                tag_rect = QRect(tag_x, tag_y, tw, 20)
                if tag_rect.right() > r.right() - 6:
                    break
                _rounded(painter, tag_rect, 10, fill=QColor(t.surface3))
                painter.setPen(QColor(t.text_muted))
                painter.drawText(tag_rect,
                                 Qt.AlignmentFlag.AlignCenter, tag.name)
                tag_x += tw + 5

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
    libraries open instantly. Styling comes from the global app theme
    (QListView#videoView selectors).
    """

    video_selected       = pyqtSignal(int)
    video_double_clicked = pyqtSignal(int)
    context_menu_requested = pyqtSignal(int, object)

    def __init__(self, mode: str = "grid", db=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.db   = db
        self.setObjectName("videoView")

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

        self.selectionModel().currentChanged.connect(self._on_current_changed)
        self.doubleClicked.connect(self._on_double_clicked)

    # ── public API ────────────────────────────────────────────────────────────

    def set_videos(self, videos: list[Video]):
        """Load videos into the model."""
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


# ── Backward-compat aliases ───────────────────────────────────────────────────
VideoGridWidget = VideoView
VideoListWidget = VideoView
