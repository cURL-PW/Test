"""Main window for Video Manager application."""

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QFileDialog, QMenu, QToolBar, QStatusBar,
    QListWidget, QListWidgetItem, QStackedWidget, QFrame,
    QMessageBox, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QIcon

from .database import Database, Video
from .video_utils import (
    scan_folder_for_videos, generate_thumbnail,
    get_video_duration, format_duration
)
from .widgets.video_item import VideoGridWidget, VideoListWidget
from .widgets.tag_widget import TagWidget, TagFilterWidget, TagManagerDialog


class VideoScanWorker(QThread):
    """Worker thread for scanning videos."""

    progress = pyqtSignal(int, int)
    video_found = pyqtSignal(dict)
    finished = pyqtSignal()

    def __init__(self, folder_path: str, folder_id: int):
        super().__init__()
        self.folder_path = folder_path
        self.folder_id = folder_id

    def run(self):
        videos = scan_folder_for_videos(self.folder_path)
        total = len(videos)

        for i, video_path in enumerate(videos):
            self.progress.emit(i + 1, total)

            duration = get_video_duration(video_path)
            thumbnail = generate_thumbnail(video_path)

            self.video_found.emit({
                "path": video_path,
                "filename": os.path.basename(video_path),
                "duration": duration,
                "thumbnail": thumbnail,
                "folder_id": self.folder_id
            })

        self.finished.emit()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.db = Database()
        self.current_folder_id = None
        self.selected_video_id = None
        self.scan_worker = None

        self.setWindowTitle("Video Manager")
        self.setMinimumSize(1200, 700)

        self._setup_ui()
        self._setup_toolbar()
        self._setup_statusbar()
        self._load_folders()
        self._apply_dark_theme()

    def _apply_dark_theme(self):
        """Apply dark theme to the application."""
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QToolBar {
                background-color: #2d2d2d;
                border: none;
                spacing: 8px;
                padding: 4px;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
                padding: 6px 12px;
                border-radius: 4px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
            QListWidget {
                background-color: #252525;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3d3d3d;
            }
            QListWidget::item:selected {
                background-color: #3498db;
            }
            QListWidget::item:hover {
                background-color: #3d3d3d;
            }
            QSplitter::handle {
                background-color: #3d3d3d;
            }
            QStatusBar {
                background-color: #2d2d2d;
                border-top: 1px solid #3d3d3d;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4d4d4d;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5d5d5d;
            }
            QLineEdit {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
                padding: 6px;
                border-radius: 4px;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
            }
            QMenu::item {
                padding: 6px 20px;
            }
            QMenu::item:selected {
                background-color: #3498db;
            }
        """)

    def _setup_ui(self):
        """Setup the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)

        folder_header = QHBoxLayout()
        folder_header.addWidget(QLabel("Folders"))
        folder_header.addStretch()

        add_folder_btn = QPushButton("+")
        add_folder_btn.setFixedSize(28, 28)
        add_folder_btn.clicked.connect(self._add_folder)
        add_folder_btn.setToolTip("Add folder")
        folder_header.addWidget(add_folder_btn)

        left_layout.addLayout(folder_header)

        self.folder_list = QListWidget()
        self.folder_list.itemClicked.connect(self._on_folder_selected)
        self.folder_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_list.customContextMenuRequested.connect(self._folder_context_menu)
        left_layout.addWidget(self.folder_list)

        left_layout.addSpacing(12)

        self.tag_filter = TagFilterWidget()
        self.tag_filter.filter_changed.connect(self._on_tag_filter_changed)
        left_layout.addWidget(self.tag_filter)

        left_panel.setFixedWidth(250)
        splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.view_stack = QStackedWidget()

        self.grid_view = VideoGridWidget()
        self.grid_view.video_selected.connect(self._on_video_selected)
        self.grid_view.video_double_clicked.connect(self._play_video)
        self.grid_view.context_menu_requested.connect(self._video_context_menu)

        self.list_view = VideoListWidget()
        self.list_view.set_database(self.db)
        self.list_view.video_selected.connect(self._on_video_selected)
        self.list_view.video_double_clicked.connect(self._play_video)
        self.list_view.context_menu_requested.connect(self._video_context_menu)

        self.view_stack.addWidget(self.grid_view)
        self.view_stack.addWidget(self.list_view)

        right_layout.addWidget(self.view_stack)

        self.detail_panel = QFrame()
        self.detail_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.detail_panel.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-top: 1px solid #3d3d3d;
            }
        """)
        self.detail_panel.setFixedHeight(120)

        detail_layout = QVBoxLayout(self.detail_panel)
        detail_layout.setContentsMargins(12, 8, 12, 8)

        self.video_title = QLabel("Select a video")
        self.video_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        detail_layout.addWidget(self.video_title)

        self.video_info = QLabel("")
        self.video_info.setStyleSheet("color: #888; font-size: 12px;")
        detail_layout.addWidget(self.video_info)

        self.tag_widget = TagWidget()
        self.tag_widget.set_database(self.db)
        self.tag_widget.tags_changed.connect(self._refresh_tags)
        detail_layout.addWidget(self.tag_widget)

        right_layout.addWidget(self.detail_panel)

        splitter.addWidget(right_panel)
        splitter.setSizes([250, 950])

        main_layout.addWidget(splitter)

    def _setup_toolbar(self):
        """Setup the toolbar."""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        self.grid_action = QAction("Grid View", self)
        self.grid_action.setCheckable(True)
        self.grid_action.setChecked(True)
        self.grid_action.triggered.connect(lambda: self._set_view_mode("grid"))
        toolbar.addAction(self.grid_action)

        self.list_action = QAction("List View", self)
        self.list_action.setCheckable(True)
        self.list_action.triggered.connect(lambda: self._set_view_mode("list"))
        toolbar.addAction(self.list_action)

        toolbar.addSeparator()

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self._refresh_current_folder)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        tag_manager_action = QAction("Manage Tags", self)
        tag_manager_action.triggered.connect(self._open_tag_manager)
        toolbar.addAction(tag_manager_action)

    def _setup_statusbar(self):
        """Setup the status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("Ready")

    def _set_view_mode(self, mode: str):
        """Switch between grid and list view."""
        if mode == "grid":
            self.view_stack.setCurrentWidget(self.grid_view)
            self.grid_action.setChecked(True)
            self.list_action.setChecked(False)
        else:
            self.view_stack.setCurrentWidget(self.list_view)
            self.grid_action.setChecked(False)
            self.list_action.setChecked(True)

    def _load_folders(self):
        """Load folders from database."""
        self.folder_list.clear()
        folders = self.db.get_folders()

        all_item = QListWidgetItem("All Videos")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self.folder_list.addItem(all_item)

        for folder in folders:
            item = QListWidgetItem(folder.name)
            item.setData(Qt.ItemDataRole.UserRole, folder.id)
            item.setToolTip(folder.path)
            self.folder_list.addItem(item)

        self._refresh_tags()

    def _add_folder(self):
        """Add a new folder to watch."""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Video Folder"
        )
        if folder_path:
            folder = self.db.add_folder(folder_path)
            self._load_folders()
            self._scan_folder(folder.id, folder_path)

    def _scan_folder(self, folder_id: int, folder_path: str):
        """Scan a folder for videos."""
        if self.scan_worker and self.scan_worker.isRunning():
            return

        self.progress_dialog = QProgressDialog(
            "Scanning videos...", "Cancel", 0, 100, self
        )
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.show()

        self.scan_worker = VideoScanWorker(folder_path, folder_id)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.video_found.connect(self._on_video_found)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.start()

    def _on_scan_progress(self, current: int, total: int):
        """Update scan progress."""
        self.progress_dialog.setMaximum(total)
        self.progress_dialog.setValue(current)
        self.progress_dialog.setLabelText(f"Scanning videos... ({current}/{total})")

    def _on_video_found(self, video_info: dict):
        """Handle found video."""
        self.db.add_video(
            path=video_info["path"],
            filename=video_info["filename"],
            duration=video_info["duration"],
            thumbnail_path=video_info["thumbnail"],
            folder_id=video_info["folder_id"]
        )

    def _on_scan_finished(self):
        """Handle scan completion."""
        self.progress_dialog.close()
        self.statusbar.showMessage("Scan complete")
        self._refresh_videos()

    def _on_folder_selected(self, item: QListWidgetItem):
        """Handle folder selection."""
        self.current_folder_id = item.data(Qt.ItemDataRole.UserRole)
        self._refresh_videos()

    def _refresh_videos(self):
        """Refresh video list."""
        videos = self.db.get_videos(self.current_folder_id)
        self.grid_view.set_videos(videos)
        self.list_view.set_videos(videos)
        self.statusbar.showMessage(f"{len(videos)} videos")

    def _refresh_current_folder(self):
        """Refresh current folder by rescanning."""
        if self.current_folder_id:
            folders = self.db.get_folders()
            for folder in folders:
                if folder.id == self.current_folder_id:
                    self._scan_folder(folder.id, folder.path)
                    return
        self._refresh_videos()

    def _on_video_selected(self, video_id: int):
        """Handle video selection."""
        self.selected_video_id = video_id
        video = self.db.get_video(video_id)
        if video:
            self.video_title.setText(video.filename)
            self.video_info.setText(
                f"Duration: {video.duration_str} | Path: {video.path}"
            )
            self.tag_widget.set_video(video_id)

    def _play_video(self, video_id: int):
        """Play the selected video."""
        video = self.db.get_video(video_id)
        if video and os.path.exists(video.path):
            if sys.platform == "win32":
                os.startfile(video.path)
            elif sys.platform == "darwin":
                subprocess.run(["open", video.path])
            else:
                subprocess.run(["xdg-open", video.path])

    def _video_context_menu(self, video_id: int, pos):
        """Show context menu for video."""
        menu = QMenu(self)

        play_action = menu.addAction("Play")
        play_action.triggered.connect(lambda: self._play_video(video_id))

        menu.addSeparator()

        open_folder_action = menu.addAction("Open Containing Folder")
        open_folder_action.triggered.connect(
            lambda: self._open_containing_folder(video_id)
        )

        menu.addSeparator()

        delete_action = menu.addAction("Remove from Library")
        delete_action.triggered.connect(lambda: self._remove_video(video_id))

        menu.exec(pos)

    def _open_containing_folder(self, video_id: int):
        """Open the folder containing the video."""
        video = self.db.get_video(video_id)
        if video:
            folder_path = os.path.dirname(video.path)
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder_path])
            else:
                subprocess.run(["xdg-open", folder_path])

    def _remove_video(self, video_id: int):
        """Remove video from library."""
        reply = QMessageBox.question(
            self, "Remove Video",
            "Remove this video from the library?\n(The file will not be deleted)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.remove_video(video_id)
            self._refresh_videos()

    def _folder_context_menu(self, pos):
        """Show context menu for folder."""
        item = self.folder_list.itemAt(pos)
        if not item:
            return

        folder_id = item.data(Qt.ItemDataRole.UserRole)
        if folder_id is None:
            return

        menu = QMenu(self)

        rescan_action = menu.addAction("Rescan Folder")
        rescan_action.triggered.connect(
            lambda: self._rescan_folder(folder_id)
        )

        menu.addSeparator()

        remove_action = menu.addAction("Remove Folder")
        remove_action.triggered.connect(
            lambda: self._remove_folder(folder_id)
        )

        menu.exec(self.folder_list.mapToGlobal(pos))

    def _rescan_folder(self, folder_id: int):
        """Rescan a folder."""
        folders = self.db.get_folders()
        for folder in folders:
            if folder.id == folder_id:
                self._scan_folder(folder.id, folder.path)
                return

    def _remove_folder(self, folder_id: int):
        """Remove a folder from library."""
        reply = QMessageBox.question(
            self, "Remove Folder",
            "Remove this folder and all its videos from the library?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.remove_folder(folder_id)
            self._load_folders()
            self.current_folder_id = None
            self._refresh_videos()

    def _refresh_tags(self):
        """Refresh tag filter."""
        tags = self.db.get_tags()
        self.tag_filter.set_tags(tags)

    def _on_tag_filter_changed(self, tag_ids: list[int]):
        """Handle tag filter change."""
        if tag_ids:
            videos = self.db.get_videos_by_tags(tag_ids)
        else:
            videos = self.db.get_videos(self.current_folder_id)

        self.grid_view.set_videos(videos)
        self.list_view.set_videos(videos)
        self.statusbar.showMessage(f"{len(videos)} videos")

    def _open_tag_manager(self):
        """Open tag manager dialog."""
        dialog = TagManagerDialog(self.db, self)
        dialog.exec()
        self._refresh_tags()

    def closeEvent(self, event):
        """Handle window close."""
        self.db.close()
        super().closeEvent(event)
