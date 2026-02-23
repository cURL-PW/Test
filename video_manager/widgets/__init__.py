"""Custom widgets for Video Manager."""

from .video_item import VideoView, VideoGridWidget, VideoListWidget
from .tag_widget import TagWidget, TagFilterWidget, TagManagerDialog
from .video_player import VideoPlayerWidget
from .statistics_dialog import StatisticsDialog
from .dialogs import (
    SettingsDialog, AdvancedSearchDialog, SmartCollectionDialog,
    PlaylistDialog, DuplicateFinderDialog, ExportImportDialog,
    MissingFilesDialog
)

__all__ = [
    "VideoView", "VideoGridWidget", "VideoListWidget",
    "TagWidget", "TagFilterWidget", "TagManagerDialog",
    "VideoPlayerWidget", "StatisticsDialog",
    "SettingsDialog", "AdvancedSearchDialog", "SmartCollectionDialog",
    "PlaylistDialog", "DuplicateFinderDialog", "ExportImportDialog",
    "MissingFilesDialog"
]
