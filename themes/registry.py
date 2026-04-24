"""
Morpheus CMS — Theme Registry
"""
import importlib
import logging
from pathlib import Path

from themes.base import MorpheusTheme

logger = logging.getLogger('morpheus.themes')


class ThemeRegistry:
    def __init__(self):
        self._themes: dict[str, MorpheusTheme] = {}
        self._active_name: str | None = None

    def discover(self, themes_dir: Path) -> None:
        """Discover all themes in the themes library directory."""
        if not themes_dir.exists():
            return
        for theme_dir in themes_dir.iterdir():
            if theme_dir.is_dir() and (theme_dir / 'theme.py').exists():
                try:
                    module_path = f"themes.library.{theme_dir.name}.theme"
                    mod = importlib.import_module(module_path)
                    for attr in dir(mod):
                        obj = getattr(mod, attr)
                        if (
                            isinstance(obj, type)
                            and issubclass(obj, MorpheusTheme)
                            and obj is not MorpheusTheme
                            and obj.name
                        ):
                            instance = obj()
                            self._themes[obj.name] = instance
                            logger.debug(f"Discovered theme: {obj.name}")
                except Exception as e:
                    logger.error(f"Failed to load theme from {theme_dir}: {e}", exc_info=True)

    def set_active(self, name: str) -> None:
        if name in self._themes:
            self._active_name = name
            logger.info(f"Active theme: {name}")
        else:
            logger.warning(f"Theme '{name}' not found. Keeping current: {self._active_name}")

    def set_active_from_db(self) -> None:
        """Read active theme from DB (ThemeConfig) or fall back to settings."""
        try:
            from themes.models import ThemeConfig
            row = ThemeConfig.objects.filter(is_active=True).first()
            if row and row.theme_name in self._themes:
                self._active_name = row.theme_name
                return
        except Exception:
            pass
        from django.conf import settings
        self._active_name = getattr(settings, 'MORPHEUS_ACTIVE_THEME', 'aurora')

    @property
    def active(self) -> MorpheusTheme | None:
        return self._themes.get(self._active_name)

    @property
    def active_templates_dir(self) -> str | None:
        theme = self.active
        return theme.templates_dir if theme else None

    def all_themes(self) -> list[MorpheusTheme]:
        return list(self._themes.values())

    def get(self, name: str) -> MorpheusTheme | None:
        return self._themes.get(name)


# Global singleton
theme_registry = ThemeRegistry()
