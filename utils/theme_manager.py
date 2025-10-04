from config.constants import COLORS
from config.styles import ENHANCED_STYLE

class ThemeManager:
    def __init__(self):
        self.is_dark = False
        self._update_colors()

    def _update_colors(self):
        self.current_colors = {
            'background': COLORS['background'],
            'text': COLORS['text'],
            'border': COLORS['border'],
            'input_bg': COLORS['input_bg'],
            'primary': COLORS['primary'],
            'primary_hover': COLORS['primary_hover'],
            'primary_pressed': COLORS['primary_pressed'],
            'progress_bg': COLORS['progress_bg'],
            'scroll_bg': COLORS['scroll_bg'],
            'scroll_handle': COLORS['scroll_handle'],
            'surface': COLORS['surface'],
            'text_secondary': COLORS['text_secondary']
        }

    def toggle_theme(self):
        self.is_dark = not self.is_dark
        self._update_colors()
        return self.get_stylesheet()

    def get_stylesheet(self):
        return ENHANCED_STYLE % self.current_colors
