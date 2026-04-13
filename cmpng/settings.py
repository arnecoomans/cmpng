from pathlib import Path
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialise environ
env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# HTTPS / secure cookies — set HTTPS=True in .env on any environment behind SSL
HTTPS = env.bool('HTTPS', default=False)
if HTTPS:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# Application definition
INSTALLED_APPS = [
    # Local apps first so their templates take precedence over django.contrib.admin
    'cmnsd',
    'locations',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'cmnsd.middleware.user_language.UserLanguageMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'cmnsd.middleware.html_output.HtmlOutputMiddleware',
]
if env.bool('WHITENOISE', default=False):
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

ROOT_URLCONF = 'cmpng.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'cmnsd.context_processors.setting_data',
                'locations.context_processors.setting_data',
            ],
            'builtins': [
                'django.templatetags.i18n',
                'django.templatetags.l10n',
                'django.templatetags.static',
                'cmnsd.templatetags.markdown',
                'cmnsd.templatetags.query_filters',
                'cmnsd.templatetags.queryset_filters',
                'cmnsd.templatetags.text_filters',
                'cmnsd.templatetags.humanize_date',
                'cmnsd.templatetags.cmnsd',
                'cmnsd.templatetags.math_filters',
                'cmnsd.templatetags.visibility_choices',
                'locations.templatetags.maps_tags',
                'locations.templatetags.distance_tags',
            ],
        },
    },
]

WSGI_APPLICATION = 'cmpng.wsgi.application'


# Database
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}


# Authentication
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization
LANGUAGE_CODE = 'en-us'
LANGUAGES = [
  ('en', 'English'),
  ('nl', 'Nederlands'),
  ('fr', 'Français'),
]
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / 'locale']


# Static & media files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CMPNG LOCATIONS SETTINGS
GOOGLE_API_KEY = env('GOOGLE_API_KEY', default=None)
GOOGLE_MAPS_API_KEY = env('GOOGLE_MAPS_API_KEY', default=None)
DEPARTURE_CENTER = env('DEPARTURE_CENTER', default='Domkerk, Achter de Dom 1, 3512 JN Utrecht, Netherlands')
NEARBY_RANGE = 75
GUEST_NEARBY_RANGE = 35
LAZY_LOAD_MEDIA = True
LAZY_LOAD_NEARBY = True

# CMNSD SETTINGS
SITE_NAME = env('SITE_NAME', default='Vakantieplanner DEVELOPMENT')
META_DESCRIPTION = env('META_DESCRIPTION', default='A Django app for managing and sharing travel plans, locations and experiences.')
AJAX_BLOCKED_MODELS = []
AJAX_DEFAULT_DATA_SOURCES = ['kwargs', 'GET', 'POST', 'json', 'headers']
AJAX_PROTECTED_FIELDS = []
AJAX_RESTRICTED_FIELDS = []
AJAX_RENDER_REMOVE_NEWLINES = True
AJAX_ALLOW_FK_CREATION_MODELS = ['comment', 'list', 'chain'] # List of model names (lowercase) for which creation of new related objects is allowed in ForeignKey fields
AJAX_ALLOW_RELATED_CREATION_MODELS = ['tag', 'visits', 'description', 'link', 'category',] # List of model names (lowercase) for witch creation of new related objects is allowed in Related fields (ManyToMany, OneToOne)
AJAX_MAX_DEPTH_RECURSION = 3 # Maximum depth for recursion in nested objects (ForeignKey, ManyToMany, OneToOne) creation, updates and lookups
AJAX_IGNORE_CHANGE_FIELDS = [] # List of field names to ignore changes on, e.g. for auto-updated fields like 'last_modified'
AJAX_MODES = ['editable', 'add']
DEFAULT_MODEL_STATUS = 'p' # Default status for new objects: draft (d), published (p), revoked (r) or deleted (x)
DEFAULT_MODEL_VISIBILITY = 'p' # Default visibility for new objects: private (q), family (f), community (c) or public (p)
SEARCH_EXCLUDE_CHARACTER = 'exclude'
SEARCH_MIN_LENGTH = 2
SEARCH_QUERY_CHARACTER = 'q'
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='noreply@localhost')
REGISTRATION_NOTIFY_EMAIL = env('REGISTRATION_NOTIFY_EMAIL', default=None)

# Logging
_log_handlers = {
  'console': {
    'class': 'logging.StreamHandler',
    'formatter': 'simple',
  },
}
if not DEBUG:
  _log_handlers['geocoding_file'] = {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': '/var/log/cmpng/geocoding.log',
    'maxBytes': 10 * 1024 * 1024,  # 10 MB
    'backupCount': 5,
    'formatter': 'simple',
  }
  _log_handlers['auth_file'] = {
    'class': 'logging.handlers.RotatingFileHandler',
    'filename': '/var/log/cmpng/auth.log',
    'maxBytes': 10 * 1024 * 1024,  # 10 MB
    'backupCount': 5,
    'formatter': 'simple',
  }

LOGGING = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {
    'simple': {
      'format': '{asctime} {levelname} {name} {message}',
      'style': '{',
    },
  },
  'handlers': _log_handlers,
  'loggers': {
    'locations': {
      'handlers': ['console'] if DEBUG else ['geocoding_file'],
      'level': 'DEBUG' if DEBUG else 'INFO',
      'propagate': False,
    },
    'cmnsd.views.auth': {
      'handlers': ['console'] if DEBUG else ['auth_file'],
      'level': 'DEBUG' if DEBUG else 'INFO',
      'propagate': False,
    },
  },
}


# Django Debug Toolbar (dev only)
if DEBUG:
  INSTALLED_APPS += ['debug_toolbar']
  MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
  INTERNAL_IPS = ['127.0.0.1']