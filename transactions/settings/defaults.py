"""
Django settings for config project.

Generated by 'django-admin startproject' using Django 3.1.12.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from pathlib import Path
import io
import os
import environ
from google.cloud import secretmanager
import logging
import google.cloud.logging
from urllib.parse import urlparse


client = google.cloud.logging.Client()
client.setup_logging()
# Initialise environment variables
env = environ.Env()
environ.Env.read_env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(DEBUG=(bool, False))
env_file = os.path.join(BASE_DIR, "transactions", "settings",".env")


if os.path.isfile(env_file):
    # Use a local secret file, if provided
    env.read_env(env_file)
# [START_EXCLUDE]
elif os.getenv("TRAMPOLINE_CI", None):
    # Create local settings if running with CI, for unit testing

    placeholder = (
        f"SECRET_KEY=a\n"
        f"DATABASE_URL=sqlite://{os.path.join(BASE_DIR, 'db.sqlite3')}"
    )
    env.read_env(io.StringIO(placeholder))
# [END_EXCLUDE]
elif os.environ.get("GOOGLE_CLOUD_PROJECT", None):
    # Pull secrets from Secret Manager
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    client = secretmanager.SecretManagerServiceClient()
    settings_name = os.environ.get("SETTINGS_NAME", "django_settings")
    name = f"projects/{project_id}/secrets/{settings_name}/versions/latest"
    payload = client.access_secret_version(name=name).payload.data.decode("UTF-8")

    env.read_env(io.StringIO(payload))
else:
    raise Exception("No local .env or GOOGLE_CLOUD_PROJECT detected. No secrets found.")
# [END gaestd_py_django_secret_config]

SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
SHELL_PLUS_PRINT_SQL = True

# [START cloudrun_django_csrf]
# SECURITY WARNING: It's recommended that you use this when
# running in production. The URL will be known once you first deploy
# to Cloud Run. This code takes the URL and converts it to both these settings formats.

CLOUDRUN_SERVICE_URL = env("CLOUDRUN_SERVICE_URL", default=None)
if CLOUDRUN_SERVICE_URL:
    ALLOWED_HOSTS = [urlparse(CLOUDRUN_SERVICE_URL).netloc]
    CSRF_TRUSTED_ORIGINS = [CLOUDRUN_SERVICE_URL]
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
else:
    ALLOWED_HOSTS = ["*"]
# [END cloudrun_django_csrf]



# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    #3rd_party
    'django_extensions', #new
    'rest_framework', #new
    'transactions', #new
    'accounts', #new
    'widget_tweaks', #new


    
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

DEFAULT_AUTO_FIELD='django.db.models.AutoField'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [str(BASE_DIR.joinpath('templates'))], #new
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'transactions.context_processors.count_unfiled_invoices',
                'transactions.context_processors.count_review_invoices',
                'transactions.context_processors.count_transactions',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

def access_secret_version(secret_version_id):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Access the secret version.
    response = client.access_secret_version(name=secret_version_id)

    # Return the decoded payload.
    return response.payload.data.decode('UTF-8')

db_username = access_secret_version("projects/334572487877/secrets/db_username/versions/1")
db_password = access_secret_version("projects/334572487877/secrets/db_password/versions/2")

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

# [START db_setup]
logging.info("**********Setting up database************")
logging.info("**********Current environment is {}************".format(os.getenv('CLOUDRUN_SERVICE_URL', None)))
logging.info("**********All environment vars are {}************".format(os.environ))
logging.info("**********Trying env K_REVISION {}************".format(os.environ.get('K_REVISION', 'None')))

if os.environ.get('K_REVISION', None):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': '/cloudsql/tbi-finance:us-central1:tbi-postgres',
            'USER': db_username,
            'PASSWORD': db_password,
            'NAME': 'postgres',
        }
    }
else:
    # Running locally so connect to either a local MySQL instance or connect 
    # to Cloud SQL via the proxy.  To start the proxy via command line: 
    #    $ cloud_sql_proxy -instances=[INSTANCE_CONNECTION_NAME]=tcp:3306 
    # See https://cloud.google.com/sql/docs/mysql-connect-proxy
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': '127.0.0.1',
            'PORT': '5432',
            'NAME': 'postgres',
            'USER': db_username,
            'PASSWORD': db_password,
        },
        'dev' : {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': '127.0.0.1',
            'PORT': '5432',
            'NAME': 'test_db',
            'USER': db_username,
            'PASSWORD': db_password,
        }
    }
# [END db_setup]


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

AUTH_USER_MODEL = 'accounts.CustomUser'

LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

MEDIA_ROOT = '/tmp'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated', # nnew
    ]
}

STATIC_URL = 'static/'
STATICFILES_DIRS = [str(BASE_DIR.joinpath('static'))] # new
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage' # new