from django.apps import AppConfig


class TasksConfig(AppConfig):
    name = 'tasks'

    def ready(self):
        # Register signal handlers when the app is fully loaded
        import tasks.signals  # noqa: F401
