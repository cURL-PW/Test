"""Custom widgets for Video Manager."""

from .video_item import VideoItemWidget, VideoGridWidget, VideoListWidget
from .tag_widget import TagWidget, TagFilterWidget, TagManagerDialog
from .video_player import VideoPlayerWidget
from .statistics_dialog import StatisticsDialog

__all__ = [
    "VideoItemWidget", "VideoGridWidget", "VideoListWidget",
    "TagWidget", "TagFilterWidget", "TagManagerDialog",
    "VideoPlayerWidget", "StatisticsDialog"
]
