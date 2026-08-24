LIGHT = {
    'background': '#F6F6F8',
    'surface': '#FFFFFF',
    'surface_alt': '#FAFAFC',
    'text': '#191922',
    'text_secondary': '#71717D',
    'text_tertiary': '#9C9CA6',
    'border': '#E7E7EE',
    'border_hover': '#C9C9F0',
    'primary': '#4F46E5',
    'primary_hover': '#4338CA',
    'primary_pressed': '#3730A3',
    'primary_soft': '#EEEEFC',
    'success': '#15803D',
    'success_bg': '#E9F7EE',
    'error': '#DC2626',
    'error_bg': '#FDEEEE',
    'progress_bg': '#EBEBF1',
    'scroll_handle': '#CDCDD6',
}

DARK = {
    'background': '#16161B',
    'surface': '#232329',
    'surface_alt': '#2A2A32',
    'text': '#F0F0F4',
    'text_secondary': '#A5A5B0',
    'text_tertiary': '#6E6E7A',
    'border': '#31313A',
    'border_hover': '#5252A8',
    'primary': '#818CF8',
    'primary_hover': '#6D78F2',
    'primary_pressed': '#5A64EC',
    'primary_soft': '#2C2C4A',
    'success': '#4ADE80',
    'success_bg': '#1D3328',
    'error': '#F87171',
    'error_bg': '#3A2326',
    'progress_bg': '#2C2C34',
    'scroll_handle': '#4A4A55',
}


def system_palette():
    # follow the os app theme, fallback to light if we can't tell
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication

    hints = QGuiApplication.styleHints()
    try:
        if hints.colorScheme() == Qt.ColorScheme.Dark:
            return DARK
    except (AttributeError, RuntimeError):
        pass
    return LIGHT
