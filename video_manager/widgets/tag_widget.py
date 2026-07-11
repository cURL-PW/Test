"""Tag widgets for video manager."""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QDialog, QScrollArea, QFrame,
    QGridLayout, QSizePolicy, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal

from .. import theme


class TagLabel(QWidget):
    """A single tag label widget with optional remove button."""

    clicked = pyqtSignal(int)
    removed = pyqtSignal(int)

    def __init__(self, tag_id: int, name: str,
                 removable: bool = False, selected: bool = False, parent=None):
        super().__init__(parent)
        self.tag_id = tag_id
        self.tag_name = name
        self.selected = selected

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(6)

        self.label = QLabel(name)
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.label)

        if removable:
            remove_btn = QPushButton("x")
            remove_btn.setFixedSize(18, 18)
            remove_btn.clicked.connect(lambda: self.removed.emit(self.tag_id))
            remove_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: rgba(255,255,255,0.2);
                    color: white;
                    font-weight: bold;
                    border-radius: 9px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.4);
                }
            """)
            layout.addWidget(remove_btn)

        self._update_style()

    def _update_style(self):
        """Update widget style from the active theme."""
        t = theme.current()
        if self.selected:
            self.setStyleSheet(f"""
                TagLabel {{
                    background-color: {t.accent};
                    border: 1px solid {t.accent};
                    border-radius: 13px;
                }}
                QLabel {{
                    color: {t.on_accent};
                    font-size: 12px;
                    font-weight: 600;
                    background: transparent;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                TagLabel {{
                    background-color: {t.surface3};
                    border: 1px solid {t.border_strong};
                    border-radius: 13px;
                }}
                TagLabel:hover {{
                    background-color: {t.accent_soft};
                    border-color: {t.accent};
                }}
                QLabel {{
                    color: {t.text};
                    font-size: 12px;
                    background: transparent;
                }}
            """)

    def set_selected(self, selected: bool):
        """Set selection state."""
        self.selected = selected
        self._update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tag_id)
        super().mousePressEvent(event)


class TagFilterWidget(QWidget):
    """Widget for filtering videos by tags."""

    filter_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_tags: set[int] = set()
        self.tags: dict[int, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.addWidget(QLabel("Filter by Tags:"))

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(60)
        self.clear_btn.clicked.connect(self.clear_filter)
        header.addWidget(self.clear_btn)
        header.addStretch()

        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(60)
        scroll.setMaximumHeight(220)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.tags_container = QWidget()
        self.tags_layout = QGridLayout(self.tags_container)
        self.tags_layout.setSpacing(6)
        self.tags_layout.setContentsMargins(0, 5, 0, 5)

        scroll.setWidget(self.tags_container)
        layout.addWidget(scroll)

    def set_tags(self, tags: list):
        """Set available tags."""
        for i in reversed(range(self.tags_layout.count())):
            widget = self.tags_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.tags.clear()
        col = 0
        row = 0
        max_cols = 3

        for tag in tags:
            self.tags[tag.id] = tag.name
            is_selected = tag.id in self.selected_tags
            tag_label = TagLabel(tag.id, tag.name, selected=is_selected)
            tag_label.clicked.connect(self._toggle_tag)
            tag_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            self.tags_layout.addWidget(tag_label, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _toggle_tag(self, tag_id: int):
        """Toggle a tag selection."""
        if tag_id in self.selected_tags:
            self.selected_tags.discard(tag_id)
        else:
            self.selected_tags.add(tag_id)

        self._update_selection_style()
        self.filter_changed.emit(list(self.selected_tags))

    def _update_selection_style(self):
        """Update visual style for selected tags."""
        for i in range(self.tags_layout.count()):
            widget = self.tags_layout.itemAt(i).widget()
            if isinstance(widget, TagLabel):
                widget.set_selected(widget.tag_id in self.selected_tags)

    def clear_filter(self):
        """Clear all tag filters."""
        self.selected_tags.clear()
        self._update_selection_style()
        self.filter_changed.emit([])


class TagSelectorDialog(QDialog):
    """Dialog for selecting tags to add to a video."""

    def __init__(self, db, current_tag_ids: list[int], parent=None):
        super().__init__(parent)
        self.db = db
        self.current_tag_ids = set(current_tag_ids)
        self.selected_tag_ids: set[int] = set()

        self.setWindowTitle("Select Tags")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self)

        info_label = QLabel("Click tags to select/deselect:")
        info_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(info_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.tags_container = QWidget()
        self.tags_layout = QGridLayout(self.tags_container)
        self.tags_layout.setSpacing(8)
        self.tags_layout.setContentsMargins(5, 5, 5, 5)
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self.tags_container)
        layout.addWidget(scroll)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("Add Selected")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setObjectName("accentBtn")
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)

        self._load_tags()

    def _load_tags(self):
        """Load available tags (excluding already assigned ones)."""
        for i in reversed(range(self.tags_layout.count())):
            widget = self.tags_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        tags = self.db.get_tags()
        available_tags = [t for t in tags if t.id not in self.current_tag_ids]

        if not available_tags:
            no_tags_label = QLabel("No more tags available.\nCreate new tags in Tag Manager.")
            no_tags_label.setStyleSheet("color: #888; padding: 20px;")
            no_tags_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tags_layout.addWidget(no_tags_label, 0, 0)
            return

        col = 0
        row = 0
        max_cols = 3

        for tag in available_tags:
            is_selected = tag.id in self.selected_tag_ids
            tag_label = TagLabel(tag.id, tag.name, selected=is_selected)
            tag_label.clicked.connect(self._toggle_tag)
            tag_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            self.tags_layout.addWidget(tag_label, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _toggle_tag(self, tag_id: int):
        """Toggle tag selection."""
        if tag_id in self.selected_tag_ids:
            self.selected_tag_ids.discard(tag_id)
        else:
            self.selected_tag_ids.add(tag_id)

        for i in range(self.tags_layout.count()):
            widget = self.tags_layout.itemAt(i).widget()
            if isinstance(widget, TagLabel):
                widget.set_selected(widget.tag_id in self.selected_tag_ids)

    def get_selected_tags(self) -> list[int]:
        """Get list of selected tag IDs."""
        return list(self.selected_tag_ids)


class TagWidget(QWidget):
    """Widget for displaying and editing video tags."""

    tags_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_id = None
        self.db = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(QLabel("Tags:"))
        header.addStretch()

        self.add_btn = QPushButton("+ Add Tags")
        self.add_btn.setFixedWidth(100)
        self.add_btn.clicked.connect(self._show_tag_selector)
        header.addWidget(self.add_btn)

        layout.addLayout(header)

        self.tags_container = QWidget()
        self.tags_container.setObjectName("flowContainer")
        self.tags_flow = QHBoxLayout(self.tags_container)
        self.tags_flow.setContentsMargins(0, 0, 0, 0)
        self.tags_flow.setSpacing(6)
        self.tags_flow.addStretch()
        layout.addWidget(self.tags_container)

    def set_database(self, db):
        """Set database reference."""
        self.db = db

    def set_video(self, video_id: int):
        """Set current video and load its tags."""
        self.video_id = video_id
        self._load_tags()

    def _load_tags(self):
        """Load and display tags for current video."""
        for i in reversed(range(self.tags_flow.count() - 1)):
            widget = self.tags_flow.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        if self.video_id and self.db:
            tags = self.db.get_video_tags(self.video_id)
            for tag in tags:
                tag_label = TagLabel(tag.id, tag.name, removable=True)
                tag_label.removed.connect(self._remove_tag)
                self.tags_flow.insertWidget(self.tags_flow.count() - 1, tag_label)

    def _show_tag_selector(self):
        """Show tag selector dialog."""
        if not self.video_id or not self.db:
            return

        current_tags = self.db.get_video_tags(self.video_id)
        current_tag_ids = [t.id for t in current_tags]

        dialog = TagSelectorDialog(self.db, current_tag_ids, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_ids = dialog.get_selected_tags()
            for tag_id in selected_ids:
                self.db.add_video_tag(self.video_id, tag_id)
            self._load_tags()
            self.tags_changed.emit()

    def _remove_tag(self, tag_id: int):
        """Remove a tag from the video."""
        if self.video_id and self.db:
            self.db.remove_video_tag(self.video_id, tag_id)
            self._load_tags()
            self.tags_changed.emit()


class TagManagerDialog(QDialog):
    """Dialog for managing all tags (create/delete)."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Tag Manager")
        self.setMinimumSize(450, 350)

        layout = QVBoxLayout(self)

        info_label = QLabel("Register tags here. You can then assign them to videos.")
        info_label.setStyleSheet("color: #888; font-size: 12px; margin-bottom: 10px;")
        layout.addWidget(info_label)

        add_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter new tag name...")
        self.name_input.returnPressed.connect(self._add_tag)
        add_layout.addWidget(self.name_input)

        self.add_btn = QPushButton("Add Tag")
        self.add_btn.setFixedWidth(100)
        self.add_btn.clicked.connect(self._add_tag)
        self.add_btn.setObjectName("accentBtn")
        add_layout.addWidget(self.add_btn)

        layout.addLayout(add_layout)

        layout.addSpacing(10)

        tags_header = QLabel("Registered Tags:")
        tags_header.setStyleSheet("font-weight: bold;")
        layout.addWidget(tags_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.StyledPanel)

        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.tags_layout.setSpacing(4)
        self.tags_layout.setContentsMargins(8, 8, 8, 8)

        scroll.setWidget(self.tags_container)
        layout.addWidget(scroll)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self._load_tags()

    def _load_tags(self):
        """Load all tags."""
        for i in reversed(range(self.tags_layout.count())):
            widget = self.tags_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        tags = self.db.get_tags()

        if not tags:
            empty_label = QLabel("No tags registered yet.")
            empty_label.setStyleSheet("color: #888; padding: 20px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tags_layout.addWidget(empty_label)
            return

        for tag in tags:
            row = QFrame()
            row.setStyleSheet("""
                QFrame {
                    background-color: #3d3d3d;
                    border-radius: 6px;
                    padding: 4px;
                }
                QFrame:hover {
                    background-color: #4d4d4d;
                }
            """)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 12, 8)

            name_label = QLabel(tag.name)
            name_label.setStyleSheet("font-size: 13px;")
            row_layout.addWidget(name_label)
            row_layout.addStretch()

            delete_btn = QPushButton("Delete")
            delete_btn.setFixedWidth(70)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #c0392b;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e74c3c;
                }
            """)
            delete_btn.clicked.connect(lambda checked, tid=tag.id, tname=tag.name: self._delete_tag(tid, tname))
            row_layout.addWidget(delete_btn)

            self.tags_layout.addWidget(row)

    def _add_tag(self):
        """Add a new tag."""
        name = self.name_input.text().strip()
        if not name:
            return

        existing_tags = self.db.get_tags()
        if any(t.name.lower() == name.lower() for t in existing_tags):
            QMessageBox.warning(self, "Duplicate Tag", f"Tag '{name}' already exists.")
            return

        self.db.add_tag(name)
        self.name_input.clear()
        self._load_tags()

    def _delete_tag(self, tag_id: int, tag_name: str):
        """Delete a tag with confirmation."""
        reply = QMessageBox.question(
            self, "Delete Tag",
            f"Delete tag '{tag_name}'?\n\nThis will remove the tag from all videos.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.remove_tag(tag_id)
            self._load_tags()
