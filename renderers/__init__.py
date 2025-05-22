# renderers/__init__.py
from .polymarket_renderer import display_event as polymarket_display
from .default_renderer import display_event as default_display

__all__ = ['polymarket_display', 'default_display']