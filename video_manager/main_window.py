"""Main window for Video Manager application."""

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QFileDialog, QMenu, QToolBar, QStatusBar,
    QListWidget, QListWidgetItem, QStackedWidget, QFrame,
    QMessageBox, QProgressDialog, QApplication, QLineEdit,
    QComboBox, QCheckBox, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QShortcut

from .database import Database, Video
from .video_utils import (
    scan_folder_for_videos, generate_thumbnail,
    get_video_duration, format_duration
)
from .widgets.video_item import VideoGridWidget, VideoListWidget
from .widgets.tag_widget import TagWidget, TagFilterWidget, TagManagerDialog


class FolderAddDialog(QDialog):
    """Dialog for adding a folder with options."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Folder")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select folder...")
        self.path_input.setReadOnly(True)
        path_layout.addWidget(self.path_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_folder)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        self.recursive_check = QCheckBox("Include subfolders (recursive scan)")
        layout.addWidget(self.recursive_check)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.folder_path = ""

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Video Folder")
        if folder:
            self.folder_path = folder
            self.path_input.setText(folder)

    def get_options(self) -> tuple[str, bool]:
        """Return (folder_path, recursive)."""
        return self.folder_path, self.recursive_check.isChecked()


class VideoScanWorker(QThread):
    """Worker thread for scanning videos."""

    progress = pyqtSignal(int, int)
    video_found = pyqtSignal(dict)
    finished = pyqtSignal()

    def __init__(self, folder_path: str, folder_id: int, recursive: bool = False):
        super().__init__()
        self.folder_path = folder_path
        self.folder_id = folder_id
        self.recursive = recursive

    def run(self):
        videos = scan_folder_for_videos(self.folder_path, recursive=self.recursive)
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

        self.current_sort_by = "filename"
        self.current_sort_order = "asc"
        self.current_search_query = ""
        self.current_tag_filter: list[int] = []
        self.show_favorites_only = False

        self.setWindowTitle("Video Manager")
        self.setMinimumSize(1200, 700)

        self._setup_ui()
        self._setup_toolbar()
        self._setup_statusbar()
        self._setup_shortcuts()
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
            QPushButton:checked {
                background-color: #3498db;
                border: 1px solid #2980b9;
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
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
            QComboBox {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
                padding: 5px 10px;
                border-radius: 4px;
                color: #e0e0e0;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
                selection-background-color: #3498db;
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
            QCheckBox {
                color: #e0e0e0;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
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

        search_bar = QWidget()
        search_bar.setStyleSheet("background-color: #252525; padding: 4px;")
        search_layout = QHBoxLayout(search_bar)
        search_layout.setContentsMargins(8, 8, 8, 8)
        search_layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search videos... (Ctrl+F)")
        self.search_input.setMaximumWidth(300)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input)

        search_layout.addWidget(QLabel("Sort:"))

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name", "Duration", "Date Added", "Favorites"])
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        search_layout.addWidget(self.sort_combo)

        self.sort_order_btn = QPushButton("Asc")
        self.sort_order_btn.setFixedWidth(50)
        self.sort_order_btn.setCheckable(True)
        self.sort_order_btn.clicked.connect(self._toggle_sort_order)
        search_layout.addWidget(self.sort_order_btn)

        search_layout.addSpacing(20)

        self.favorites_btn = QPushButton("Favorites")
        self.favorites_btn.setCheckable(True)
        self.favorites_btn.setToolTip("Show only favorites")
        self.favorites_btn.clicked.connect(self._toggle_favorites_filter)
        search_layout.addWidget(self.favorites_btn)

        search_layout.addStretch()

        right_layout.addWidget(search_bar)

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

        title_row = QHBoxLayout()

        self.favorite_btn = QPushButton()
        self.favorite_btn.setFixedSize(28, 28)
        self.favorite_btn.clicked.connect(self._toggle_current_favorite)
        self.favorite_btn.setToolTip("Toggle favorite")
        self._update_favorite_button(False)
        title_row.addWidget(self.favorite_btn)

        self.video_title = QLabel("Select a video")
        self.video_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_row.addWidget(self.video_title)
        title_row.addStretch()

        detail_layout.addLayout(title_row)

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

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QShortcut(QKeySequence("Ctrl+F"), self, self._focus_search)

        QShortcut(QKeySequence("Return"), self, self._play_selected_video)
        QShortcut(QKeySequence("Enter"), self, self._play_selected_video)

        QShortcut(QKeySequence("Delete"), self, self._delete_selected_video)

        QShortcut(QKeySequence("F"), self, self._toggle_current_favorite)

        QShortcut(QKeySequence("Escape"), self, self._clear_search)

    def _focus_search(self):
        """Focus the search input."""
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _clear_search(self):
        """Clear search and reset focus."""
        self.search_input.clear()
        self.search_input.clearFocus()

    def _play_selected_video(self):
        """Play currently selected video."""
        if self.selected_video_id:
            self._play_video(self.selected_video_id)

    def _delete_selected_video(self):
        """Delete currently selected video."""
        if self.selected_video_id:
            self._remove_video(self.selected_video_id)

    def _update_favorite_button(self, is_favorite: bool):
        """Update favorite button appearance."""
        if is_favorite:
            self.favorite_btn.setText("★")
            self.favorite_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f39c12;
                    border: none;
                    font-size: 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e67e22;
                }
            """)
        else:
            self.favorite_btn.setText("☆")
            self.favorite_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d3d3d;
                    border: 1px solid #4d4d4d;
                    font-size: 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
            """)

    def _toggle_current_favorite(self):
        """Toggle favorite status of current video."""
        if self.selected_video_id:
            new_status = self.db.toggle_favorite(self.selected_video_id)
            self._update_favorite_button(new_status)
            self._refresh_videos()

    def _toggle_favorites_filter(self):
        """Toggle showing only favorites."""
        self.show_favorites_only = self.favorites_btn.isChecked()
        self._refresh_videos()

    def _on_search_changed(self, text: str):
        """Handle search input change."""
        self.current_search_query = text
        self._refresh_videos()

    def _on_sort_changed(self, index: int):
        """Handle sort selection change."""
        sort_options = ["filename", "duration", "created_at", "favorite"]
        self.current_sort_by = sort_options[index]
        self._refresh_videos()

    def _toggle_sort_order(self):
        """Toggle sort order between asc and desc."""
        if self.sort_order_btn.isChecked():
            self.current_sort_order = "desc"
            self.sort_order_btn.setText("Desc")
        else:
            self.current_sort_order = "asc"
            self.sort_order_btn.setText("Asc")
        self._refresh_videos()

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

        fav_item = QListWidgetItem("★ Favorites")
        fav_item.setData(Qt.ItemDataRole.UserRole, "favorites")
        self.folder_list.addItem(fav_item)

        for folder in folders:
            item = QListWidgetItem(folder.name)
            item.setData(Qt.ItemDataRole.UserRole, folder.id)
            item.setToolTip(folder.path)
            self.folder_list.addItem(item)

        self._refresh_tags()

    def _add_folder(self):
        """Add a new folder to watch."""
        dialog = FolderAddDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            folder_path, recursive = dialog.get_options()
            if folder_path:
                folder = self.db.add_folder(folder_path)
                self._load_folders()
                self._scan_folder(folder.id, folder_path, recursive)

    def _scan_folder(self, folder_id: int, folder_path: str, recursive: bool = False):
        """Scan a folder for videos."""
        if self.scan_worker and self.scan_worker.isRunning():
            return

        self.progress_dialog = QProgressDialog(
            "Scanning videos...", "Cancel", 0, 100, self
        )
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.show()

        self.scan_worker = VideoScanWorker(folder_path, folder_id, recursive)
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
        data = item.data(Qt.ItemDataRole.UserRole)
        if data == "favorites":
            self.current_folder_id = None
            self.show_favorites_only = True
            self.favorites_btn.setChecked(True)
        else:
            self.current_folder_id = data
            self.show_favorites_only = False
            self.favorites_btn.setChecked(False)
        self._refresh_videos()

    def _refresh_videos(self):
        """Refresh video list with current filters."""
        if self.current_tag_filter:
            videos = self.db.get_videos_by_tags(
                self.current_tag_filter,
                sort_by=self.current_sort_by,
                sort_order=self.current_sort_order,
                search_query=self.current_search_query
            )
        else:
            videos = self.db.get_videos(
                folder_id=self.current_folder_id,
                sort_by=self.current_sort_by,
                sort_order=self.current_sort_order,
                search_query=self.current_search_query,
                favorites_only=self.show_favorites_only
            )

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
            self._update_favorite_button(video.favorite)

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
        video = self.db.get_video(video_id)

        play_action = menu.addAction("Play")
        play_action.triggered.connect(lambda: self._play_video(video_id))

        menu.addSeparator()

        if video and video.favorite:
            fav_action = menu.addAction("Remove from Favorites")
        else:
            fav_action = menu.addAction("Add to Favorites")
        fav_action.triggered.connect(lambda: self._toggle_video_favorite(video_id))

        menu.addSeparator()

        open_folder_action = menu.addAction("Open Containing Folder")
        open_folder_action.triggered.connect(
            lambda: self._open_containing_folder(video_id)
        )

        menu.addSeparator()

        delete_action = menu.addAction("Remove from Library")
        delete_action.triggered.connect(lambda: self._remove_video(video_id))

        menu.exec(pos)

    def _toggle_video_favorite(self, video_id: int):
        """Toggle favorite status of a video."""
        new_status = self.db.toggle_favorite(video_id)
        if video_id == self.selected_video_id:
            self._update_favorite_button(new_status)
        self._refresh_videos()

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
            if video_id == self.selected_video_id:
                self.selected_video_id = None
                self.video_title.setText("Select a video")
                self.video_info.setText("")
            self._refresh_videos()

    def _folder_context_menu(self, pos):
        """Show context menu for folder."""
        item = self.folder_list.itemAt(pos)
        if not item:
            return

        folder_id = item.data(Qt.ItemDataRole.UserRole)
        if folder_id is None or folder_id == "favorites":
            return

        menu = QMenu(self)

        rescan_action = menu.addAction("Rescan Folder")
        rescan_action.triggered.connect(
            lambda: self._rescan_folder(folder_id)
        )

        rescan_recursive_action = menu.addAction("Rescan with Subfolders")
        rescan_recursive_action.triggered.connect(
            lambda: self._rescan_folder(folder_id, recursive=True)
        )

        menu.addSeparator()

        remove_action = menu.addAction("Remove Folder")
        remove_action.triggered.connect(
            lambda: self._remove_folder(folder_id)
        )

        menu.exec(self.folder_list.mapToGlobal(pos))

    def _rescan_folder(self, folder_id: int, recursive: bool = False):
        """Rescan a folder."""
        folders = self.db.get_folders()
        for folder in folders:
            if folder.id == folder_id:
                self._scan_folder(folder.id, folder.path, recursive)
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
        self.current_tag_filter = tag_ids
        self._refresh_videos()

    def _open_tag_manager(self):
        """Open tag manager dialog."""
        dialog = TagManagerDialog(self.db, self)
        dialog.exec()
        self._refresh_tags()

    def closeEvent(self, event):
        """Handle window close."""
        self.db.close()
        super().closeEvent(event)
