"""Design-token based theme system for Video Manager.

All colors live in Theme dataclasses; build_stylesheet() turns the active
theme into one application-wide QSS sheet so every window and dialog stays
consistent. Custom-painted widgets (delegates) read tokens via current().
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    # base surfaces
    bg: str              # window background
    surface: str         # panels / cards
    surface2: str        # hover / inputs
    surface3: str        # pressed / raised
    border: str
    border_strong: str
    # text
    text: str
    text_muted: str
    text_faint: str
    # accent
    accent: str
    accent_hover: str
    accent_soft: str     # soft selection background
    on_accent: str
    # semantic
    warning: str         # favorites / A-B markers
    danger: str
    success: str
    # media
    thumb_bg: str
    scrim: str           # translucent badge background


DARK = Theme(
    name="dark",
    bg="#0f1216",
    surface="#161a21",
    surface2="#1e242d",
    surface3="#272e39",
    border="#262d37",
    border_strong="#3a4453",
    text="#e8ecf1",
    text_muted="#98a2b3",
    text_faint="#64707f",
    accent="#4f8cff",
    accent_hover="#74a5ff",
    accent_soft="#1b2a44",
    on_accent="#ffffff",
    warning="#f2b34c",
    danger="#e5645f",
    success="#46c08b",
    thumb_bg="#0a0c0f",
    scrim="rgba(8, 10, 14, 0.75)",
)

LIGHT = Theme(
    name="light",
    bg="#f4f6f9",
    surface="#ffffff",
    surface2="#eef1f5",
    surface3="#e4e9ef",
    border="#dde3ea",
    border_strong="#c3ccd8",
    text="#1c2430",
    text_muted="#5b6675",
    text_faint="#8c96a5",
    accent="#2f6fed",
    accent_hover="#4d85f2",
    accent_soft="#dce8fd",
    on_accent="#ffffff",
    warning="#d99a26",
    danger="#d64550",
    success="#1f9e6a",
    thumb_bg="#dfe4ea",
    scrim="rgba(20, 26, 34, 0.66)",
)

_current: Theme = DARK


def current() -> Theme:
    """Return the active theme."""
    return _current


def set_current(theme: Theme) -> None:
    """Set the active theme (delegates read tokens through current())."""
    global _current
    _current = theme


def by_name(name: str) -> Theme:
    return LIGHT if name == "light" else DARK


def build_stylesheet(t: Theme) -> str:
    """Build the application-wide QSS for a theme."""
    return f"""
    /* ── base ─────────────────────────────────────────────── */
    QWidget {{
        background-color: {t.bg};
        color: {t.text};
        font-size: 13px;
    }}
    QLabel {{ background: transparent; }}
    QLabel#mutedLabel {{ color: {t.text_muted}; }}
    QToolTip {{
        background-color: {t.surface3};
        color: {t.text};
        border: 1px solid {t.border_strong};
        padding: 5px 8px;
        border-radius: 6px;
    }}

    /* ── menus ────────────────────────────────────────────── */
    QMenuBar {{
        background-color: {t.bg};
        border-bottom: 1px solid {t.border};
        padding: 2px 6px;
    }}
    QMenuBar::item {{
        background: transparent;
        padding: 6px 10px;
        border-radius: 6px;
    }}
    QMenuBar::item:selected {{ background-color: {t.surface2}; }}
    QMenu {{
        background-color: {t.surface};
        border: 1px solid {t.border_strong};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{
        background: transparent;
        padding: 7px 24px 7px 14px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background-color: {t.accent};
        color: {t.on_accent};
    }}
    QMenu::separator {{
        height: 1px;
        background: {t.border};
        margin: 6px 10px;
    }}

    /* ── buttons ──────────────────────────────────────────── */
    QPushButton {{
        background-color: {t.surface2};
        border: 1px solid {t.border};
        padding: 7px 14px;
        border-radius: 8px;
        color: {t.text};
    }}
    QPushButton:hover {{
        background-color: {t.surface3};
        border-color: {t.border_strong};
    }}
    QPushButton:pressed {{ background-color: {t.surface}; }}
    QPushButton:checked {{
        background-color: {t.accent};
        border-color: {t.accent};
        color: {t.on_accent};
    }}
    QPushButton:disabled {{ color: {t.text_faint}; }}
    QPushButton#accentBtn {{
        background-color: {t.accent};
        border-color: {t.accent};
        color: {t.on_accent};
        font-weight: 600;
    }}
    QPushButton#accentBtn:hover {{ background-color: {t.accent_hover}; }}
    QPushButton#iconBtn {{
        padding: 5px;
        font-size: 15px;
    }}
    QPushButton#segLeft {{
        border-top-right-radius: 0;
        border-bottom-right-radius: 0;
        font-size: 15px;
        padding: 5px;
    }}
    QPushButton#segRight {{
        border-top-left-radius: 0;
        border-bottom-left-radius: 0;
        margin-left: -1px;
        font-size: 15px;
        padding: 5px;
    }}

    /* ── inputs ───────────────────────────────────────────── */
    QLineEdit {{
        background-color: {t.surface2};
        border: 1px solid {t.border};
        border-radius: 8px;
        padding: 7px 12px;
        selection-background-color: {t.accent};
        selection-color: {t.on_accent};
    }}
    QLineEdit:focus {{
        border-color: {t.accent};
        background-color: {t.surface};
    }}
    QLineEdit#searchInput {{
        border-radius: 16px;
        padding: 7px 16px;
    }}
    QComboBox {{
        background-color: {t.surface2};
        border: 1px solid {t.border};
        padding: 6px 12px;
        border-radius: 8px;
    }}
    QComboBox:hover {{ border-color: {t.border_strong}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background-color: {t.surface};
        border: 1px solid {t.border_strong};
        border-radius: 8px;
        padding: 4px;
        selection-background-color: {t.accent};
        selection-color: {t.on_accent};
        outline: none;
    }}
    QSpinBox, QDoubleSpinBox {{
        background-color: {t.surface2};
        border: 1px solid {t.border};
        padding: 6px 8px;
        border-radius: 8px;
    }}
    QCheckBox {{ spacing: 8px; }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {t.border_strong};
        background: {t.surface2};
    }}
    QCheckBox::indicator:hover {{ border-color: {t.accent}; }}
    QCheckBox::indicator:checked {{
        background-color: {t.accent};
        border-color: {t.accent};
    }}

    /* ── lists ────────────────────────────────────────────── */
    QListWidget {{
        background-color: {t.surface};
        border: 1px solid {t.border};
        border-radius: 10px;
        padding: 4px;
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px 10px;
        border-radius: 6px;
        margin: 1px 2px;
    }}
    QListWidget::item:selected {{
        background-color: {t.accent_soft};
        color: {t.text};
    }}
    QListWidget::item:hover {{ background-color: {t.surface2}; }}
    QListWidget#sidebar {{
        background: transparent;
        border: none;
    }}
    QListView#videoView {{
        background-color: {t.bg};
        border: none;
    }}
    QListView#videoView::item {{ background: transparent; }}
    QListView#videoView::item:selected {{ background: transparent; }}
    QListView#videoView::item:hover {{ background: transparent; }}

    /* ── panels ───────────────────────────────────────────── */
    QWidget#sidePanel {{
        background-color: {t.surface};
        border-right: 1px solid {t.border};
    }}
    QWidget#sidePanel QListWidget {{ background: transparent; border: none; }}
    QWidget#headerBar {{
        background-color: {t.surface};
        border-bottom: 1px solid {t.border};
    }}
    QFrame#detailPanel {{
        background-color: {t.surface};
        border-top: 1px solid {t.border};
    }}
    QSplitter::handle {{ background-color: {t.border}; width: 1px; }}
    QStatusBar {{
        background-color: {t.surface};
        border-top: 1px solid {t.border};
        color: {t.text_muted};
    }}
    QGroupBox {{
        border: 1px solid {t.border};
        border-radius: 10px;
        margin-top: 14px;
        padding: 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {t.text_muted};
    }}

    /* ── scrollbars ───────────────────────────────────────── */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {t.border_strong};
        border-radius: 4px;
        min-height: 40px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {t.text_faint}; }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {t.border_strong};
        border-radius: 4px;
        min-width: 40px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: {t.text_faint}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    QScrollArea {{ border: none; background: transparent; }}
    /* keep scroll viewports/containers transparent so panels show through */
    QScrollArea > QWidget {{ background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QWidget#flowContainer {{ background: transparent; }}

    /* ── sliders / progress ───────────────────────────────── */
    QSlider::groove:horizontal {{
        background: {t.surface3};
        height: 5px;
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {t.accent};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {t.text};
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{ background: {t.accent_hover}; }}
    QProgressBar {{
        background-color: {t.surface3};
        border: none;
        border-radius: 4px;
        text-align: center;
        color: {t.text_muted};
    }}
    QProgressBar::chunk {{
        background-color: {t.accent};
        border-radius: 4px;
    }}
    """
