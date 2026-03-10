"""
teams/apps.py
App configuration for the `teams` application.
Handles board membership, roles, and team management.
"""
from django.apps import AppConfig


class TeamsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'teams'
    verbose_name = 'Teams'
