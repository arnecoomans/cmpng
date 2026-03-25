from django.conf import settings
from django.core.checks import register, Warning


@register()
def check_cmnsd_config(app_configs, **kwargs):
  """
  Central cmnsd system check:
  - Ensure required settings are present.
  - Ensure local apps are ordered before django.contrib.admin.
  - Ensure middleware is in the correct order.
  - Ensure cmnsd templatetags are added to builtins.
  - Ensure required context processors are present.
  - Ensure USE_I18N is enabled.
  - Ensure LOGIN_URL is defined.
  """
  warnings = []

  # --- 1. Required settings ---
  required_settings = [
    "GOOGLE_API_KEY",
    "DEPARTURE_CENTER",
    "NEARBY_RANGE",
    "GUEST_NEARBY_RANGE",
  ]
  for setting in required_settings:
    if not hasattr(settings, setting):
      warnings.append(Warning(
        f"Missing setting: {setting}",
        hint=f"Define {setting} in settings.py to configure cmpng.locations properly.",
        id="cmpng.locations.W001",
      ))

  # --- 2. LOGIN_URL ---
  if not hasattr(settings, 'LOGIN_URL'):
    warnings.append(Warning(
      "LOGIN_URL is not defined in settings.",
      hint="Set LOGIN_URL in settings.py. LocationDetailView redirects unauthenticated users to it.",
      id="cmpng.locations.W002",
    ))

  # --- 3. USE_I18N ---
  if not getattr(settings, 'USE_I18N', False):
    warnings.append(Warning(
      "USE_I18N is False or not set.",
      hint="Set USE_I18N = True in settings.py. Views use gettext/_ for translations.",
      id="cmpng.locations.W003",
    ))

  # --- 4. App order: local apps before django.contrib.admin ---
  installed = list(getattr(settings, 'INSTALLED_APPS', []))
  local_apps = ['cmnsd', 'locations']
  try:
    admin_index = installed.index('django.contrib.admin')
    for app in local_apps:
      if app in installed and installed.index(app) > admin_index:
        warnings.append(Warning(
          f"'{app}' appears after 'django.contrib.admin' in INSTALLED_APPS.",
          hint=f"Move '{app}' before 'django.contrib.admin' so its templates take precedence.",
          id="cmpng.locations.W004",
        ))
  except ValueError:
    pass  # django.contrib.admin not installed — skip

  # --- 5. Middleware order ---
  middleware = list(getattr(settings, 'MIDDLEWARE', []))
  ordered_middleware = [
    ('django.contrib.sessions.middleware.SessionMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware'),
    ('django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware'),
  ]
  for before, after in ordered_middleware:
    if before in middleware and after in middleware:
      if middleware.index(before) > middleware.index(after):
        warnings.append(Warning(
          f"'{before}' must come before '{after}' in MIDDLEWARE.",
          hint="Incorrect middleware order can silently break authentication and messages.",
          id="cmpng.locations.W005",
        ))

  # --- 6. Template builtins ---
  required_builtins = [
    'django.templatetags.i18n',
    'cmnsd.templatetags.cmnsd',
    'cmnsd.templatetags.query_filters',
    'locations.templatetags.maps_tags',
    'locations.templatetags.distance_tags',
  ]
  builtins = []
  for tpl in getattr(settings, 'TEMPLATES', []):
    builtins.extend(tpl.get('OPTIONS', {}).get('builtins', []))

  for tag in required_builtins:
    if tag not in builtins:
      warnings.append(Warning(
        f"Template builtin '{tag}' is not registered.",
        hint=f"Add '{tag}' to TEMPLATES[0]['OPTIONS']['builtins'] in settings.py.",
        id="cmpng.locations.W006",
      ))

  # --- 7. Context processors ---
  required_processors = [
    'django.template.context_processors.request',
    'django.contrib.messages.context_processors.messages',
  ]
  processors = []
  for tpl in getattr(settings, 'TEMPLATES', []):
    processors.extend(tpl.get('OPTIONS', {}).get('context_processors', []))

  for proc in required_processors:
    if proc not in processors:
      warnings.append(Warning(
        f"Context processor '{proc}' is missing from TEMPLATES.",
        hint=f"Add '{proc}' to TEMPLATES[0]['OPTIONS']['context_processors'] in settings.py.",
        id="cmpng.locations.W007",
      ))

  return warnings
