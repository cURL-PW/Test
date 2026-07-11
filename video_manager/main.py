#!/usr/bin/env python3
"""Video Manager - A Qt-based video management application.

Features:
- Multiple folder support
- Thumbnail display
- Grid and list view modes
- Video duration display
- Tag management per video
- Tag-based filtering
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from .main_window import MainWindow


def main():
    """Main entry point."""
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    app = QApplication(sys.argv)
    app.setApplicationName("Video Manager")
    app.setOrganizationName("VideoManager")
    # Fusion renders QSS most consistently across platforms
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
