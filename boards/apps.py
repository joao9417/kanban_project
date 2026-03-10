"""
boards/apps.py
App configuration for the `boards` application.
Handles board, column, card, and analytics logic.
"""
from django.apps import AppConfig


class BoardsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'boards'
    verbose_name = 'Boards'

    def ready(self):
        """Connect signal handlers when the app is fully loaded."""
        import boards.signals  # noqa: F401
