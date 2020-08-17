import os

DEBUG = True

try:
    from django.db.models import JSONField  # noqa: F401

    DATABASES = {
        "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": "test.db",}
    }
except ImportError:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("TEST_DB_NAME", "appmail"),
            "USER": os.getenv("TEST_DB_USER", "postgres"),
            "PASSWORD": os.getenv("TEST_DB_PASSWORD", "postgres"),
            "HOST": os.getenv("TEST_DB_HOST", "localhost"),
            "PORT": os.getenv("TEST_DB_PORT", "5432"),
        }
    }

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "appmail",
    "tests",
)

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            # insert your TEMPLATE_DIRS here
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                # Insert your TEMPLATE_CONTEXT_PROCESSORS here or use this
                # list if you haven't customized them:
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# NB - this is good for local testing only
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
STATIC_URL = "/static/"
STATIC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))

SECRET_KEY = "top secret"

ROOT_URLCONF = "tests.urls"

APPEND_SLASH = True

STATIC_URL = "/static/"

assert DEBUG is True, "This project is only intended to be used for testing."

APPMAIL_DEFAULT_SENDER = "test@example.com"
