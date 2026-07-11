"""Additional dialogs for Video Manager."""

import os
import json
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox, QSlider,
    QListWidget, QListWidgetItem, QCheckBox, QGroupBox, QTabWidget,
    QWidget, QFileDialog, QMessageBox, QProgressDialog, QFrame,
    QScrollArea, QRadioButton, QButtonGroup, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from ..database import Database, SmartCollection, Playlist, AppSettings
from ..video_utils import get_file_hash, format_duration, format_file_size


class SettingsDialog(QDialog):
    """Application settings dialog."""

    settings_changed = pyqtSignal()

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Settings")
        self.setMinimumSize(450, 350)

        self._setup_ui()
        self._load_settings()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Theme selection
        theme_group = QGroupBox("Appearance")
        theme_layout = QFormLayout(theme_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        theme_layout.addRow("Theme:", self.theme_combo)

        self.thumbnail_slider = QSlider(Qt.Orientation.Horizontal)
        self.thumbnail_slider.setRange(120, 320)
        self.thumbnail_slider.setValue(180)
        self.thumbnail_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.thumbnail_slider.setTickInterval(40)

        thumb_layout = QHBoxLayout()
        thumb_layout.addWidget(self.thumbnail_slider)
        self.thumb_size_label = QLabel("180px")
        thumb_layout.addWidget(self.thumb_size_label)
        self.thumbnail_slider.valueChanged.connect(
            lambda v: self.thumb_size_label.setText(f"{v}px")
        )
        theme_layout.addRow("Thumbnail Size:", thumb_layout)

        layout.addWidget(theme_group)

        # Data management
        data_group = QGroupBox("Data Management")
        data_layout = QVBoxLayout(data_group)

        clear_cache_btn = QPushButton("Clear Thumbnail Cache")
        clear_cache_btn.clicked.connect(self._clear_cache)
        data_layout.addWidget(clear_cache_btn)

        clear_history_btn = QPushButton("Clear Play History")
        clear_history_btn.clicked.connect(self._clear_history)
        data_layout.addWidget(clear_history_btn)

        layout.addWidget(data_group)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _load_settings(self):
        settings = self.db.get_app_settings()
        self.theme_combo.setCurrentText(settings.theme.capitalize())
        self.thumbnail_slider.setValue(settings.thumbnail_size)

    def _save_settings(self):
        settings = AppSettings(
            theme=self.theme_combo.currentText().lower(),
            thumbnail_size=self.thumbnail_slider.value()
        )
        self.db.save_app_settings(settings)
        self.settings_changed.emit()
        self.accept()

    def _clear_cache(self):
        reply = QMessageBox.question(
            self, "Clear Cache",
            "Clear all cached thumbnails?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            cache_dir = Path.home() / ".video_manager" / "thumbnails"
            if cache_dir.exists():
                for f in cache_dir.glob("*.jpg"):
                    f.unlink()
            QMessageBox.information(self, "Done", "Thumbnail cache cleared.")

    def _clear_history(self):
        reply = QMessageBox.question(
            self, "Clear History",
            "Clear all play history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.clear_play_history()
            QMessageBox.information(self, "Done", "Play history cleared.")

    def _apply_style(self):
        """Styling is inherited from the global app theme."""
        pass


class AdvancedSearchDialog(QDialog):
    """Advanced search dialog with multiple criteria."""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.results = []
        self.setWindowTitle("Advanced Search")
        self.setMinimumSize(500, 400)

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Search criteria
        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Search in filename...")
        form.addRow("Name:", self.name_input)

        # Duration range
        duration_layout = QHBoxLayout()
        self.min_duration = QSpinBox()
        self.min_duration.setRange(0, 999)
        self.min_duration.setSuffix(" min")
        duration_layout.addWidget(self.min_duration)
        duration_layout.addWidget(QLabel("to"))
        self.max_duration = QSpinBox()
        self.max_duration.setRange(0, 999)
        self.max_duration.setSuffix(" min")
        duration_layout.addWidget(self.max_duration)
        form.addRow("Duration:", duration_layout)

        # Resolution
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["Any", "4K+", "1080p+", "720p+"])
        form.addRow("Resolution:", self.resolution_combo)

        # File size range
        size_layout = QHBoxLayout()
        self.min_size = QSpinBox()
        self.min_size.setRange(0, 99999)
        self.min_size.setSuffix(" MB")
        size_layout.addWidget(self.min_size)
        size_layout.addWidget(QLabel("to"))
        self.max_size = QSpinBox()
        self.max_size.setRange(0, 99999)
        self.max_size.setSuffix(" MB")
        size_layout.addWidget(self.max_size)
        form.addRow("File Size:", size_layout)

        layout.addLayout(form)

        # Tags selection
        tags_group = QGroupBox("Tags (optional)")
        tags_layout = QVBoxLayout(tags_group)
        self.tags_list = QListWidget()
        self.tags_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.tags_list.setMinimumHeight(80)
        self.tags_list.setMaximumHeight(160)
        tags_layout.addWidget(self.tags_list)

        # Load tags
        for tag in self.db.get_tags():
            item = QListWidgetItem(tag.name)
            item.setData(Qt.ItemDataRole.UserRole, tag.id)
            self.tags_list.addItem(item)

        layout.addWidget(tags_group)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self._do_search)
        button_layout.addWidget(search_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _do_search(self):
        # Get selected tags
        selected_tags = []
        for item in self.tags_list.selectedItems():
            selected_tags.append(item.data(Qt.ItemDataRole.UserRole))

        # Resolution mapping
        resolution_map = {"Any": 0, "4K+": 2160, "1080p+": 1080, "720p+": 720}
        min_res = resolution_map[self.resolution_combo.currentText()]

        self.results = self.db.advanced_search(
            search_query=self.name_input.text(),
            min_duration=self.min_duration.value() * 60,
            max_duration=self.max_duration.value() * 60 if self.max_duration.value() > 0 else 0,
            min_resolution=min_res,
            min_size=self.min_size.value() * 1024 * 1024,
            max_size=self.max_size.value() * 1024 * 1024 if self.max_size.value() > 0 else 0,
            tags=selected_tags if selected_tags else None
        )
        self.accept()

    def _apply_style(self):
        """Styling is inherited from the global app theme."""
        pass


class SmartCollectionDialog(QDialog):
    """Dialog for creating/editing smart collections."""

    def __init__(self, db: Database, collection: SmartCollection = None, parent=None):
        super().__init__(parent)
        self.db = db
        self.collection = collection
        self.setWindowTitle("Smart Collection" if not collection else "Edit Collection")
        self.setMinimumWidth(400)

        self._setup_ui()
        self._apply_style()

        if collection:
            self._load_collection()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()

        self.name_input = QLineEdit()
        form.addRow("Name:", self.name_input)

        self.filter_type = QComboBox()
        self.filter_type.addItems(["Duration", "Resolution", "File Size", "Recently Added"])
        self.filter_type.currentTextChanged.connect(self._on_filter_type_changed)
        form.addRow("Filter Type:", self.filter_type)

        self.operator_combo = QComboBox()
        self.operator_combo.addItems(["Greater than", "Less than", "Equal to"])
        form.addRow("Operator:", self.operator_combo)

        self.value_widget = QWidget()
        self.value_layout = QHBoxLayout(self.value_widget)
        self.value_layout.setContentsMargins(0, 0, 0, 0)

        self.value_spin = QSpinBox()
        self.value_spin.setRange(0, 99999)
        self.value_layout.addWidget(self.value_spin)

        self.value_label = QLabel("minutes")
        self.value_layout.addWidget(self.value_label)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["4K", "1080p", "720p", "SD"])
        self.resolution_combo.setVisible(False)
        self.value_layout.addWidget(self.resolution_combo)

        form.addRow("Value:", self.value_widget)

        layout.addLayout(form)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_filter_type_changed(self, text):
        self.value_spin.setVisible(True)
        self.value_label.setVisible(True)
        self.resolution_combo.setVisible(False)
        self.operator_combo.setVisible(True)

        if text == "Duration":
            self.value_label.setText("minutes")
        elif text == "Resolution":
            self.value_spin.setVisible(False)
            self.value_label.setVisible(False)
            self.resolution_combo.setVisible(True)
            self.operator_combo.setVisible(False)
        elif text == "File Size":
            self.value_label.setText("MB")
        elif text == "Recently Added":
            self.value_label.setText("days")
            self.operator_combo.setVisible(False)

    def _load_collection(self):
        if self.collection:
            self.name_input.setText(self.collection.name)
            type_map = {"duration": "Duration", "resolution": "Resolution",
                       "size": "File Size", "recent": "Recently Added"}
            self.filter_type.setCurrentText(type_map.get(self.collection.filter_type, "Duration"))

            op_map = {"gt": "Greater than", "lt": "Less than", "eq": "Equal to"}
            self.operator_combo.setCurrentText(op_map.get(self.collection.filter_operator, "Greater than"))

            if self.collection.filter_type == "resolution":
                self.resolution_combo.setCurrentText(self.collection.filter_value)
            else:
                self.value_spin.setValue(int(self.collection.filter_value))

    def _save(self):
        if not self.name_input.text():
            QMessageBox.warning(self, "Error", "Please enter a name.")
            return

        type_map = {"Duration": "duration", "Resolution": "resolution",
                   "File Size": "size", "Recently Added": "recent"}
        filter_type = type_map[self.filter_type.currentText()]

        op_map = {"Greater than": "gt", "Less than": "lt", "Equal to": "eq"}
        operator = op_map[self.operator_combo.currentText()]

        if filter_type == "resolution":
            value = self.resolution_combo.currentText()
        else:
            value = str(self.value_spin.value())

        if self.collection:
            self.db.delete_smart_collection(self.collection.id)

        self.db.create_smart_collection(
            self.name_input.text(), filter_type, operator, value
        )
        self.accept()

    def _apply_style(self):
        """Styling is inherited from the global app theme."""
        pass


class PlaylistDialog(QDialog):
    """Playlist management dialog."""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Playlists")
        self.setMinimumSize(500, 400)

        self._setup_ui()
        self._load_playlists()
        self._apply_style()

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        # Left panel - playlist list
        left_panel = QVBoxLayout()

        left_panel.addWidget(QLabel("Playlists"))

        self.playlist_list = QListWidget()
        self.playlist_list.itemClicked.connect(self._on_playlist_selected)
        left_panel.addWidget(self.playlist_list)

        btn_layout = QHBoxLayout()
        add_btn = QPushButton("+")
        add_btn.setFixedWidth(40)
        add_btn.clicked.connect(self._add_playlist)
        btn_layout.addWidget(add_btn)

        del_btn = QPushButton("-")
        del_btn.setFixedWidth(40)
        del_btn.clicked.connect(self._delete_playlist)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()

        left_panel.addLayout(btn_layout)
        layout.addLayout(left_panel)

        # Right panel - playlist contents
        right_panel = QVBoxLayout()

        self.videos_label = QLabel("Videos in Playlist")
        right_panel.addWidget(self.videos_label)

        self.videos_list = QListWidget()
        right_panel.addWidget(self.videos_list)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_from_playlist)
        right_panel.addWidget(remove_btn)

        layout.addLayout(right_panel)

    def _load_playlists(self):
        self.playlist_list.clear()
        for playlist in self.db.get_playlists():
            item = QListWidgetItem(playlist.name)
            item.setData(Qt.ItemDataRole.UserRole, playlist.id)
            self.playlist_list.addItem(item)

    def _on_playlist_selected(self, item):
        playlist_id = item.data(Qt.ItemDataRole.UserRole)
        self.videos_list.clear()

        videos = self.db.get_playlist_videos(playlist_id)
        for video in videos:
            v_item = QListWidgetItem(f"{video.filename} ({video.duration_str})")
            v_item.setData(Qt.ItemDataRole.UserRole, video.id)
            self.videos_list.addItem(v_item)

        self.videos_label.setText(f"Videos in Playlist ({len(videos)})")

    def _add_playlist(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name:
            self.db.create_playlist(name)
            self._load_playlists()

    def _delete_playlist(self):
        item = self.playlist_list.currentItem()
        if item:
            reply = QMessageBox.question(
                self, "Delete Playlist",
                f"Delete playlist '{item.text()}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.db.delete_playlist(item.data(Qt.ItemDataRole.UserRole))
                self._load_playlists()
                self.videos_list.clear()

    def _remove_from_playlist(self):
        playlist_item = self.playlist_list.currentItem()
        video_item = self.videos_list.currentItem()
        if playlist_item and video_item:
            self.db.remove_from_playlist(
                playlist_item.data(Qt.ItemDataRole.UserRole),
                video_item.data(Qt.ItemDataRole.UserRole)
            )
            self._on_playlist_selected(playlist_item)

    def _apply_style(self):
        """Styling is inherited from the global app theme."""
        pass


class DuplicateHashWorker(QThread):
    """Worker thread for computing file hashes."""

    progress = pyqtSignal(int, int)
    finished = pyqtSignal()

    def __init__(self, db: Database):
        super().__init__()
        self.db = db

    def run(self):
        videos = self.db.get_videos_without_hash()
        total = len(videos)

        for i, video in enumerate(videos):
            self.progress.emit(i + 1, total)
            if os.path.exists(video.path):
                file_hash = get_file_hash(video.path)
                if file_hash:
                    self.db.update_video_hash(video.id, file_hash)

        self.finished.emit()


class DuplicateFinderDialog(QDialog):
    """Dialog for finding and managing duplicate videos."""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Find Duplicates")
        self.setMinimumSize(600, 450)

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Find duplicate videos by comparing file content.\n"
            "First, scan your library to compute file hashes."
        )
        info_label.setStyleSheet("color: #888;")
        layout.addWidget(info_label)

        # Scan button
        scan_btn = QPushButton("Scan for Duplicates")
        scan_btn.clicked.connect(self._start_scan)
        layout.addWidget(scan_btn)

        # Results
        layout.addWidget(QLabel("Duplicate Groups:"))
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self._on_group_selected)
        layout.addWidget(self.results_list)

        # Details
        layout.addWidget(QLabel("Files in Group:"))
        self.details_list = QListWidget()
        layout.addWidget(self.details_list)

        # Actions
        btn_layout = QHBoxLayout()
        keep_first_btn = QPushButton("Keep First, Remove Others")
        keep_first_btn.clicked.connect(self._keep_first)
        btn_layout.addWidget(keep_first_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _start_scan(self):
        progress = QProgressDialog("Computing file hashes...", "Cancel", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        self.worker = DuplicateHashWorker(self.db)
        self.worker.progress.connect(
            lambda c, t: progress.setValue(int(c / t * 100))
        )
        self.worker.finished.connect(lambda: self._show_results(progress))
        self.worker.start()

    def _show_results(self, progress):
        progress.close()

        self.results_list.clear()
        self.duplicates = self.db.find_duplicates()

        if not self.duplicates:
            QMessageBox.information(self, "Done", "No duplicates found!")
            return

        for i, group in enumerate(self.duplicates):
            item = QListWidgetItem(f"Group {i + 1}: {len(group)} files")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.results_list.addItem(item)

    def _on_group_selected(self, item):
        group_idx = item.data(Qt.ItemDataRole.UserRole)
        group = self.duplicates[group_idx]

        self.details_list.clear()
        for video in group:
            v_item = QListWidgetItem(
                f"{video.filename}\n  {video.path}\n  Size: {format_file_size(video.file_size)}"
            )
            v_item.setData(Qt.ItemDataRole.UserRole, video.id)
            self.details_list.addItem(v_item)

    def _keep_first(self):
        item = self.results_list.currentItem()
        if not item:
            return

        group_idx = item.data(Qt.ItemDataRole.UserRole)
        group = self.duplicates[group_idx]

        if len(group) < 2:
            return

        reply = QMessageBox.question(
            self, "Remove Duplicates",
            f"Keep '{group[0].filename}' and remove {len(group) - 1} duplicate(s) from library?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for video in group[1:]:
                self.db.remove_video(video.id)
            self._show_results_internal()

    def _show_results_internal(self):
        self.results_list.clear()
        self.details_list.clear()
        self.duplicates = self.db.find_duplicates()

        for i, group in enumerate(self.duplicates):
            item = QListWidgetItem(f"Group {i + 1}: {len(group)} files")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.results_list.addItem(item)

    def _apply_style(self):
        """Styling is inherited from the global app theme."""
        pass


class ExportImportDialog(QDialog):
    """Dialog for exporting and importing library data."""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Export / Import")
        self.setMinimumSize(450, 300)

        self._setup_ui()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Export section
        export_group = QGroupBox("Export")
        export_layout = QVBoxLayout(export_group)

        export_layout.addWidget(QLabel("Export library data to a JSON file for backup."))

        self.export_tags = QCheckBox("Include tags")
        self.export_tags.setChecked(True)
        export_layout.addWidget(self.export_tags)

        self.export_playlists = QCheckBox("Include playlists")
        self.export_playlists.setChecked(True)
        export_layout.addWidget(self.export_playlists)

        export_btn = QPushButton("Export...")
        export_btn.clicked.connect(self._do_export)
        export_layout.addWidget(export_btn)

        layout.addWidget(export_group)

        # Import section
        import_group = QGroupBox("Import")
        import_layout = QVBoxLayout(import_group)

        import_layout.addWidget(QLabel("Import library data from a JSON backup file."))

        import_btn = QPushButton("Import...")
        import_btn.clicked.connect(self._do_import)
        import_layout.addWidget(import_btn)

        layout.addWidget(import_group)

        layout.addStretch()

    def _do_export(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Library", "video_manager_backup.json",
            "JSON Files (*.json)"
        )
        if not file_path:
            return

        data = {
            "export_date": datetime.now().isoformat(),
            "version": "1.0",
            "folders": [],
            "videos": [],
            "tags": [],
            "video_tags": [],
            "playlists": [],
            "playlist_items": []
        }

        # Export folders
        for folder in self.db.get_folders():
            data["folders"].append({"id": folder.id, "path": folder.path, "name": folder.name})

        # Export videos
        for video in self.db.get_videos():
            data["videos"].append({
                "id": video.id, "path": video.path, "filename": video.filename,
                "duration": video.duration, "folder_id": video.folder_id,
                "favorite": video.favorite, "play_count": video.play_count
            })

        if self.export_tags.isChecked():
            for tag in self.db.get_tags():
                data["tags"].append({"id": tag.id, "name": tag.name})

            # Export video-tag associations
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT video_id, tag_id FROM video_tags")
            for row in cursor.fetchall():
                data["video_tags"].append({"video_id": row[0], "tag_id": row[1]})

        if self.export_playlists.isChecked():
            for playlist in self.db.get_playlists():
                data["playlists"].append({"id": playlist.id, "name": playlist.name})
                for video in self.db.get_playlist_videos(playlist.id):
                    data["playlist_items"].append({
                        "playlist_id": playlist.id, "video_id": video.id
                    })

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        QMessageBox.information(self, "Done", f"Library exported to:\n{file_path}")

    def _do_import(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Library", "", "JSON Files (*.json)"
        )
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            imported = {"tags": 0, "playlists": 0}

            # Import tags
            if "tags" in data:
                for tag_data in data["tags"]:
                    self.db.add_tag(tag_data["name"])
                    imported["tags"] += 1

            # Import playlists
            if "playlists" in data:
                for pl_data in data["playlists"]:
                    self.db.create_playlist(pl_data["name"])
                    imported["playlists"] += 1

            QMessageBox.information(
                self, "Done",
                f"Import complete!\nTags: {imported['tags']}\nPlaylists: {imported['playlists']}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Import failed:\n{str(e)}")

    def _apply_style(self):
        """Styling is inherited from the global app theme."""
        pass


class MissingFilesDialog(QDialog):
    """Dialog for checking and managing missing video files."""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Missing Files")
        self.setMinimumSize(550, 400)

        self._setup_ui()
        self._check_files()
        self._apply_style()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Videos with missing files:"))

        self.missing_list = QListWidget()
        layout.addWidget(self.missing_list)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._check_files)
        btn_layout.addWidget(refresh_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(remove_btn)

        remove_all_btn = QPushButton("Remove All Missing")
        remove_all_btn.clicked.connect(self._remove_all)
        btn_layout.addWidget(remove_all_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _check_files(self):
        self.missing_list.clear()
        self.missing_videos = self.db.find_missing_files()

        for video in self.missing_videos:
            item = QListWidgetItem(f"{video.filename}\n  {video.path}")
            item.setData(Qt.ItemDataRole.UserRole, video.id)
            self.missing_list.addItem(item)

        self.status_label.setText(f"Found {len(self.missing_videos)} missing file(s)")

    def _remove_selected(self):
        item = self.missing_list.currentItem()
        if item:
            self.db.remove_video(item.data(Qt.ItemDataRole.UserRole))
            self._check_files()

    def _remove_all(self):
        if not self.missing_videos:
            return

        reply = QMessageBox.question(
            self, "Remove All",
            f"Remove {len(self.missing_videos)} video(s) with missing files from library?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            for video in self.missing_videos:
                self.db.remove_video(video.id)
            self._check_files()

    def _apply_style(self):
        """Styling is inherited from the global app theme."""
        pass
