"""Statistics dashboard dialog."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGridLayout, QPushButton, QWidget, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt

from ..database import Database, Statistics
from ..video_utils import format_duration, format_file_size


class StatCard(QFrame):
    """Statistics card widget."""

    def __init__(self, title: str, value: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            StatCard {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
        """)
        self.setMinimumSize(140, 90)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet("color: #e0e0e0; font-size: 24px; font-weight: bold;")
        layout.addWidget(value_label)

        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setStyleSheet("color: #666; font-size: 10px;")
            layout.addWidget(sub_label)

        layout.addStretch()


class HistoryItemWidget(QFrame):
    """Play history item widget."""

    def __init__(self, video_name: str, played_at: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            HistoryItemWidget {
                background-color: #2d2d2d;
                border-radius: 4px;
            }
            HistoryItemWidget:hover {
                background-color: #3d3d3d;
            }
        """)
        self.setMinimumHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)

        name_label = QLabel(video_name)
        name_label.setStyleSheet("color: #e0e0e0; font-size: 12px;")
        name_label.setToolTip(video_name)
        layout.addWidget(name_label, 1)

        # Format the played_at date
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(played_at)
            time_str = dt.strftime("%m/%d %H:%M")
        except Exception:
            time_str = played_at[:16] if len(played_at) > 16 else played_at

        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(time_label)


class StatisticsDialog(QDialog):
    """Statistics dashboard dialog."""

    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Library Statistics")
        self.setMinimumSize(600, 500)

        self._setup_ui()
        self._load_statistics()
        self._apply_style()

    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Title
        title = QLabel("Library Statistics")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(title)

        # Stats cards
        cards_widget = QWidget()
        cards_layout = QGridLayout(cards_widget)
        cards_layout.setSpacing(12)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setColumnStretch(0, 1)
        cards_layout.setColumnStretch(1, 1)
        cards_layout.setColumnStretch(2, 1)

        self.total_videos_card = StatCard("Total Videos", "0")
        cards_layout.addWidget(self.total_videos_card, 0, 0)

        self.total_duration_card = StatCard("Total Duration", "00:00:00")
        cards_layout.addWidget(self.total_duration_card, 0, 1)

        self.total_size_card = StatCard("Total Size", "0 B")
        cards_layout.addWidget(self.total_size_card, 0, 2)

        self.favorites_card = StatCard("Favorites", "0")
        cards_layout.addWidget(self.favorites_card, 1, 0)

        self.tags_card = StatCard("Tags", "0")
        cards_layout.addWidget(self.tags_card, 1, 1)

        self.folders_card = StatCard("Folders", "0")
        cards_layout.addWidget(self.folders_card, 1, 2)

        layout.addWidget(cards_widget)

        # Recent activity section
        recent_label = QLabel("Recent Activity (Last 7 Days)")
        recent_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e0e0e0; margin-top: 8px;")
        layout.addWidget(recent_label)

        self.recently_played_label = QLabel("0 videos played")
        self.recently_played_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.recently_played_label)

        # Play history section
        history_label = QLabel("Recent Play History")
        history_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e0e0e0; margin-top: 8px;")
        layout.addWidget(history_label)

        # History list in scroll area
        history_scroll = QScrollArea()
        history_scroll.setWidgetResizable(True)
        history_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                background-color: #1e1e1e;
            }
        """)
        history_scroll.setMinimumHeight(150)

        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.setContentsMargins(4, 4, 4, 4)
        self.history_layout.setSpacing(4)
        self.history_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        history_scroll.setWidget(self.history_container)
        layout.addWidget(history_scroll)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        clear_history_btn = QPushButton("Clear History")
        clear_history_btn.clicked.connect(self._clear_history)
        button_layout.addWidget(clear_history_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _load_statistics(self):
        """Load and display statistics."""
        stats = self.db.get_statistics()

        # Update cards
        self.total_videos_card.findChildren(QLabel)[1].setText(str(stats.total_videos))
        self.total_duration_card.findChildren(QLabel)[1].setText(format_duration(stats.total_duration))
        self.total_size_card.findChildren(QLabel)[1].setText(format_file_size(stats.total_size))
        self.favorites_card.findChildren(QLabel)[1].setText(str(stats.favorites_count))
        self.tags_card.findChildren(QLabel)[1].setText(str(stats.tags_count))
        self.folders_card.findChildren(QLabel)[1].setText(str(stats.folders_count))

        self.recently_played_label.setText(f"{stats.recently_played} videos played")

        # Load play history
        self._load_history()

    def _load_history(self):
        """Load play history."""
        # Clear existing items
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        history = self.db.get_play_history(limit=20)

        if not history:
            no_history = QLabel("No play history yet")
            no_history.setStyleSheet("color: #666; padding: 20px;")
            no_history.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.history_layout.addWidget(no_history)
        else:
            for entry in history:
                if entry.video:
                    item = HistoryItemWidget(entry.video.filename, entry.played_at)
                    self.history_layout.addWidget(item)

    def _clear_history(self):
        """Clear play history."""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Clear History",
            "Are you sure you want to clear all play history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.clear_play_history()
            self._load_history()

    def _apply_style(self):
        """Apply dialog styles."""
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
                padding: 8px 16px;
                border-radius: 4px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QLabel {
                color: #e0e0e0;
            }
        """)
