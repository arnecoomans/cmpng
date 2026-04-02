from django.apps import AppConfig


class LocationsConfig(AppConfig):
  default_auto_field = 'django.db.models.BigAutoField'
  name = 'locations'

  def ready(self):
    import locations.signals  # noqa: F401
