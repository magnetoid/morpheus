"""
Morpheus CMS — MorpheusTheme Base Class
Every theme subclasses this.
"""
import logging

logger = logging.getLogger('morpheus.themes')


class MorpheusTheme:
    """
    Base class for all Morph themes.

    Subclass in themes/library/{name}/theme.py:

        class AuroraTheme(MorpheusTheme):
            name = "aurora"
            label = "Aurora"
            version = "1.0.0"

            def get_config_schema(self):
                return {
                    "properties": {
                        "primary_color": {"type": "string", "default": "#7C3AED"},
                    }
                }
    """

    name: str = ''
    label: str = ''
    version: str = '1.0.0'
    description: str = ''
    author: str = 'Morph Team'
    preview_image: str = ''         # relative path inside theme's static dir
    supports_plugins: list[str] = []  # plugin names this theme provides templates for

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.name:
            raise TypeError(f"{cls.__name__} must define a 'name' attribute")

    def get_config_schema(self) -> dict:
        """JSON Schema for theme customisation — rendered as live editor in admin."""
        return {}

    def get_config(self) -> dict:
        """Read current config from DB."""
        from themes.models import ThemeConfig
        try:
            row = ThemeConfig.objects.get(theme_name=self.name)
            return row.config
        except Exception:
            return {}

    def get_config_value(self, key: str, default=None):
        config = self.get_config()
        if key in config:
            return config[key]
        schema = self.get_config_schema()
        return schema.get('properties', {}).get(key, {}).get('default', default)

    @property
    def templates_dir(self) -> str:
        """Absolute path to this theme's templates directory."""
        from django.conf import settings
        return str(settings.MORPHEUS_THEMES_DIR / self.name / 'templates')

    @property
    def static_dir(self) -> str:
        from django.conf import settings
        return str(settings.MORPHEUS_THEMES_DIR / self.name / 'static')

    def __repr__(self):
        return f"<MorpheusTheme: {self.name} v{self.version}>"
