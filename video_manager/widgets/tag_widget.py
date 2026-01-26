"""Tag widgets for video manager."""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QDialog, QColorDialog, QScrollArea, QFrame,
    QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class TagLabel(QWidget):
    """A single tag label widget with optional remove button."""

    clicked = pyqtSignal(int)
    removed = pyqtSignal(int)

    def __init__(self, tag_id: int, name: str, color: str,
                 removable: bool = False, parent=None):
        super().__init__(parent)
        self.tag_id = tag_id
        self.tag_name = name
        self.tag_color = color

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        self.label = QLabel(name)
        self.label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.label)

        if removable:
            remove_btn = QPushButton("x")
            remove_btn.setFixedSize(16, 16)
            remove_btn.clicked.connect(lambda: self.removed.emit(self.tag_id))
            remove_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: rgba(0,0,0,0.2);
                    border-radius: 8px;
                }
            """)
            layout.addWidget(remove_btn)

        self._update_style()

    def _update_style(self):
        """Update widget style based on color."""
        qcolor = QColor(self.tag_color)
        luminance = (0.299 * qcolor.red() + 0.587 * qcolor.green() +
                     0.114 * qcolor.blue()) / 255
        text_color = "#000000" if luminance > 0.5 else "#ffffff"

        self.setStyleSheet(f"""
            TagLabel {{
                background-color: {self.tag_color};
                border-radius: 10px;
            }}
            QLabel {{
                color: {text_color};
                font-size: 12px;
            }}
        """)

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
        self.tags: dict[int, tuple[str, str]] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        header.addWidget(QLabel("Tags Filter:"))

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(60)
        self.clear_btn.clicked.connect(self.clear_filter)
        header.addWidget(self.clear_btn)
        header.addStretch()

        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(120)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.tags_container = QWidget()
        self.tags_layout = QGridLayout(self.tags_container)
        self.tags_layout.setSpacing(5)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self.tags_container)
        layout.addWidget(scroll)

    def set_tags(self, tags: list):
        """Set available tags."""
        for i in reversed(range(self.tags_layout.count())):
            self.tags_layout.itemAt(i).widget().deleteLater()

        self.tags.clear()
        col = 0
        row = 0
        max_cols = 4

        for tag in tags:
            self.tags[tag.id] = (tag.name, tag.color)
            tag_label = TagLabel(tag.id, tag.name, tag.color)
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
                if widget.tag_id in self.selected_tags:
                    widget.setStyleSheet(widget.styleSheet() + """
                        TagLabel { border: 2px solid #2196F3; }
                    """)
                else:
                    widget._update_style()

    def clear_filter(self):
        """Clear all tag filters."""
        self.selected_tags.clear()
        self._update_selection_style()
        self.filter_changed.emit([])


class TagWidget(QWidget):
    """Widget for displaying and editing video tags."""

    tags_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_id = None
        self.db = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tags_container = QWidget()
        self.tags_flow = QHBoxLayout(self.tags_container)
        self.tags_flow.setContentsMargins(0, 0, 0, 0)
        self.tags_flow.setSpacing(5)
        self.tags_flow.addStretch()
        layout.addWidget(self.tags_container)

        add_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("New tag...")
        self.tag_input.setMaximumWidth(150)
        self.tag_input.returnPressed.connect(self._add_tag)
        add_layout.addWidget(self.tag_input)

        self.color_btn = QPushButton("Color")
        self.color_btn.setFixedWidth(60)
        self.color_btn.clicked.connect(self._pick_color)
        add_layout.addWidget(self.color_btn)

        self.add_btn = QPushButton("+")
        self.add_btn.setFixedWidth(30)
        self.add_btn.clicked.connect(self._add_tag)
        add_layout.addWidget(self.add_btn)

        add_layout.addStretch()
        layout.addLayout(add_layout)

        self.current_color = "#3498db"

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
                tag_label = TagLabel(tag.id, tag.name, tag.color, removable=True)
                tag_label.removed.connect(self._remove_tag)
                self.tags_flow.insertWidget(self.tags_flow.count() - 1, tag_label)

    def _add_tag(self):
        """Add a new tag to the video."""
        name = self.tag_input.text().strip()
        if not name or not self.video_id or not self.db:
            return

        tag = self.db.add_tag(name, self.current_color)
        self.db.add_video_tag(self.video_id, tag.id)
        self.tag_input.clear()
        self._load_tags()
        self.tags_changed.emit()

    def _remove_tag(self, tag_id: int):
        """Remove a tag from the video."""
        if self.video_id and self.db:
            self.db.remove_video_tag(self.video_id, tag_id)
            self._load_tags()
            self.tags_changed.emit()

    def _pick_color(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(QColor(self.current_color), self)
        if color.isValid():
            self.current_color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {self.current_color};")


class TagManagerDialog(QDialog):
    """Dialog for managing all tags."""

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Tag Manager")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        self.tags_container = QWidget()
        self.tags_layout = QVBoxLayout(self.tags_container)
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.tags_container)
        layout.addWidget(scroll)

        add_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Tag name...")
        add_layout.addWidget(self.name_input)

        self.color_btn = QPushButton("Color")
        self.color_btn.clicked.connect(self._pick_color)
        add_layout.addWidget(self.color_btn)

        self.add_btn = QPushButton("Add Tag")
        self.add_btn.clicked.connect(self._add_tag)
        add_layout.addWidget(self.add_btn)

        layout.addLayout(add_layout)

        self.current_color = "#3498db"
        self._load_tags()

    def _load_tags(self):
        """Load all tags."""
        for i in reversed(range(self.tags_layout.count())):
            self.tags_layout.itemAt(i).widget().deleteLater()

        for tag in self.db.get_tags():
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(5, 2, 5, 2)

            color_box = QLabel()
            color_box.setFixedSize(20, 20)
            color_box.setStyleSheet(f"background-color: {tag.color}; border-radius: 3px;")
            row_layout.addWidget(color_box)

            name_label = QLabel(tag.name)
            row_layout.addWidget(name_label)
            row_layout.addStretch()

            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda checked, tid=tag.id: self._delete_tag(tid))
            row_layout.addWidget(delete_btn)

            self.tags_layout.addWidget(row)

    def _add_tag(self):
        """Add a new tag."""
        name = self.name_input.text().strip()
        if name:
            self.db.add_tag(name, self.current_color)
            self.name_input.clear()
            self._load_tags()

    def _delete_tag(self, tag_id: int):
        """Delete a tag."""
        self.db.remove_tag(tag_id)
        self._load_tags()

    def _pick_color(self):
        """Open color picker."""
        color = QColorDialog.getColor(QColor(self.current_color), self)
        if color.isValid():
            self.current_color = color.name()
            self.color_btn.setStyleSheet(f"background-color: {self.current_color};")
