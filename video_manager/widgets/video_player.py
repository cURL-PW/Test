"""Built-in video player widget using PyQt6 multimedia."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QStyle, QSizePolicy, QFrame
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut

try:
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    MULTIMEDIA_AVAILABLE = True
except ImportError:
    MULTIMEDIA_AVAILABLE = False


def format_time(ms: int) -> str:
    """Format milliseconds to HH:MM:SS or MM:SS."""
    seconds = ms // 1000
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class VideoPlayerWidget(QWidget):
    """Built-in video player widget."""

    playback_started = pyqtSignal(int)  # video_id
    playback_stopped = pyqtSignal(int, float)  # video_id, position
    player_closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_id = None
        self.video_path = None
        self._is_seeking = False

        if not MULTIMEDIA_AVAILABLE:
            self._setup_fallback_ui()
            return

        self._setup_ui()
        self._setup_player()
        self._setup_shortcuts()
        self._apply_style()

    def _setup_fallback_ui(self):
        """Setup UI when multimedia is not available."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        label = QLabel("PyQt6 Multimedia module not available.\n"
                      "Install with: pip install PyQt6-Multimedia")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #888; font-size: 14px;")
        layout.addWidget(label)

    def _setup_ui(self):
        """Setup the player UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video display area
        self.video_widget = QVideoWidget()
        self.video_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self.video_widget)

        # Control bar
        control_bar = QFrame()
        control_bar.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border-top: 1px solid #3d3d3d;
            }
        """)
        control_layout = QVBoxLayout(control_bar)
        control_layout.setContentsMargins(8, 4, 8, 8)
        control_layout.setSpacing(4)

        # Progress bar
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(8)

        self.time_label = QLabel("00:00")
        self.time_label.setStyleSheet("color: #e0e0e0; font-size: 11px;")
        self.time_label.setFixedWidth(60)
        progress_layout.addWidget(self.time_label)

        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 1000)
        self.progress_slider.sliderPressed.connect(self._on_slider_pressed)
        self.progress_slider.sliderReleased.connect(self._on_slider_released)
        self.progress_slider.sliderMoved.connect(self._on_slider_moved)
        progress_layout.addWidget(self.progress_slider)

        self.duration_label = QLabel("00:00")
        self.duration_label.setStyleSheet("color: #e0e0e0; font-size: 11px;")
        self.duration_label.setFixedWidth(60)
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        progress_layout.addWidget(self.duration_label)

        control_layout.addLayout(progress_layout)

        # Button bar
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        self.play_btn = QPushButton("Play")
        self.play_btn.setFixedWidth(70)
        self.play_btn.clicked.connect(self.toggle_play)
        button_layout.addWidget(self.play_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.clicked.connect(self.stop)
        button_layout.addWidget(self.stop_btn)

        button_layout.addSpacing(20)

        # Skip buttons
        skip_back_btn = QPushButton("-10s")
        skip_back_btn.setFixedWidth(50)
        skip_back_btn.clicked.connect(lambda: self.skip(-10000))
        button_layout.addWidget(skip_back_btn)

        skip_forward_btn = QPushButton("+10s")
        skip_forward_btn.setFixedWidth(50)
        skip_forward_btn.clicked.connect(lambda: self.skip(10000))
        button_layout.addWidget(skip_forward_btn)

        button_layout.addStretch()

        # Volume control
        volume_label = QLabel("Volume:")
        volume_label.setStyleSheet("color: #e0e0e0;")
        button_layout.addWidget(volume_label)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        button_layout.addWidget(self.volume_slider)

        self.mute_btn = QPushButton("Mute")
        self.mute_btn.setFixedWidth(60)
        self.mute_btn.setCheckable(True)
        self.mute_btn.clicked.connect(self._toggle_mute)
        button_layout.addWidget(self.mute_btn)

        button_layout.addSpacing(20)

        # Close button
        close_btn = QPushButton("Close Player")
        close_btn.clicked.connect(self._close_player)
        button_layout.addWidget(close_btn)

        control_layout.addLayout(button_layout)

        layout.addWidget(control_bar)

        # Title bar
        self.title_label = QLabel()
        self.title_label.setStyleSheet("""
            background-color: #2d2d2d;
            color: #e0e0e0;
            padding: 8px;
            font-weight: bold;
        """)
        layout.insertWidget(0, self.title_label)

    def _setup_player(self):
        """Setup the media player."""
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        # Connect signals
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.player.errorOccurred.connect(self._on_error)

        # Position save timer
        self.save_timer = QTimer()
        self.save_timer.setInterval(5000)  # Save every 5 seconds
        self.save_timer.timeout.connect(self._save_position)

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        QShortcut(QKeySequence("Space"), self, self.toggle_play)
        QShortcut(QKeySequence("Left"), self, lambda: self.skip(-5000))
        QShortcut(QKeySequence("Right"), self, lambda: self.skip(5000))
        QShortcut(QKeySequence("Up"), self, lambda: self._adjust_volume(10))
        QShortcut(QKeySequence("Down"), self, lambda: self._adjust_volume(-10))
        QShortcut(QKeySequence("M"), self, self._toggle_mute)
        QShortcut(QKeySequence("Escape"), self, self._close_player)

    def _apply_style(self):
        """Apply styles to the widget."""
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #3d3d3d;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #5dade2;
            }
            QSlider::sub-page:horizontal {
                background: #3498db;
                border-radius: 3px;
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
                background-color: #e74c3c;
            }
        """)

    def load_video(self, video_id: int, path: str, title: str = "",
                   start_position: float = 0.0):
        """Load a video file."""
        if not MULTIMEDIA_AVAILABLE:
            return False

        self.video_id = video_id
        self.video_path = path
        self.title_label.setText(title or path)

        self.player.setSource(QUrl.fromLocalFile(path))

        if start_position > 0:
            # Wait for media to be loaded before seeking
            QTimer.singleShot(500, lambda: self._seek_to_position(start_position))

        return True

    def _seek_to_position(self, position: float):
        """Seek to a position in seconds."""
        if self.player.duration() > 0:
            self.player.setPosition(int(position * 1000))

    def play(self):
        """Start playback."""
        if not MULTIMEDIA_AVAILABLE:
            return

        self.player.play()
        self.save_timer.start()
        if self.video_id:
            self.playback_started.emit(self.video_id)

    def pause(self):
        """Pause playback."""
        if not MULTIMEDIA_AVAILABLE:
            return

        self.player.pause()
        self.save_timer.stop()

    def stop(self):
        """Stop playback."""
        if not MULTIMEDIA_AVAILABLE:
            return

        position = self.player.position() / 1000.0
        self.player.stop()
        self.save_timer.stop()

        if self.video_id:
            self.playback_stopped.emit(self.video_id, position)

    def toggle_play(self):
        """Toggle between play and pause."""
        if not MULTIMEDIA_AVAILABLE:
            return

        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.pause()
        else:
            self.play()

    def skip(self, ms: int):
        """Skip forward or backward by milliseconds."""
        if not MULTIMEDIA_AVAILABLE:
            return

        new_pos = max(0, min(self.player.position() + ms, self.player.duration()))
        self.player.setPosition(new_pos)

    def _on_position_changed(self, position: int):
        """Handle position change."""
        if not self._is_seeking:
            if self.player.duration() > 0:
                slider_pos = int((position / self.player.duration()) * 1000)
                self.progress_slider.setValue(slider_pos)
            self.time_label.setText(format_time(position))

    def _on_duration_changed(self, duration: int):
        """Handle duration change."""
        self.duration_label.setText(format_time(duration))

    def _on_state_changed(self, state):
        """Handle playback state change."""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("Pause")
        else:
            self.play_btn.setText("Play")

        # Check if playback finished
        if state == QMediaPlayer.PlaybackState.StoppedState:
            if self.player.position() >= self.player.duration() - 100:
                # Video finished - clear position
                if self.video_id:
                    self.playback_stopped.emit(self.video_id, 0.0)

    def _on_error(self, error, error_string):
        """Handle player error."""
        print(f"Player error: {error_string}")

    def _on_slider_pressed(self):
        """Handle slider press."""
        self._is_seeking = True

    def _on_slider_released(self):
        """Handle slider release."""
        self._is_seeking = False
        if self.player.duration() > 0:
            position = int((self.progress_slider.value() / 1000) * self.player.duration())
            self.player.setPosition(position)

    def _on_slider_moved(self, value: int):
        """Handle slider move during drag."""
        if self.player.duration() > 0:
            position = int((value / 1000) * self.player.duration())
            self.time_label.setText(format_time(position))

    def _on_volume_changed(self, value: int):
        """Handle volume change."""
        self.audio_output.setVolume(value / 100.0)

    def _adjust_volume(self, delta: int):
        """Adjust volume by delta."""
        new_value = max(0, min(100, self.volume_slider.value() + delta))
        self.volume_slider.setValue(new_value)

    def _toggle_mute(self):
        """Toggle mute state."""
        if not MULTIMEDIA_AVAILABLE:
            return

        is_muted = self.mute_btn.isChecked()
        self.audio_output.setMuted(is_muted)

    def _save_position(self):
        """Save current playback position."""
        if self.video_id and self.player.duration() > 0:
            position = self.player.position() / 1000.0
            self.playback_stopped.emit(self.video_id, position)

    def _close_player(self):
        """Close the player and return to library."""
        self.stop()
        self.player.setSource(QUrl())
        self.video_id = None
        self.video_path = None
        self.player_closed.emit()

    def get_current_position(self) -> float:
        """Get current position in seconds."""
        if MULTIMEDIA_AVAILABLE:
            return self.player.position() / 1000.0
        return 0.0

    def closeEvent(self, event):
        """Handle close event."""
        if MULTIMEDIA_AVAILABLE:
            self.stop()
            self.player.setSource(QUrl())
        super().closeEvent(event)
