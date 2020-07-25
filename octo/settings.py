"""
Django settings for octopus project.

Generated by 'django-admin startproject' using Django 1.11.6.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import sys
import logging
import socket
from octo.config_cred import cred, mails
log = logging.getLogger("octo.octologger")

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(BASE_DIR, 'octo'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# noinspection SpellCheckingInspection
SECRET_KEY = cred['SECRET_KEY']

CURR_HOSTNAME = socket.getfqdn()
ALLOWED_HOSTS = ['localhost', '127.0.0.1', CURR_HOSTNAME, socket.getfqdn(), socket.gethostbyname(socket.gethostname()), socket.gethostname()]

# SECURITY WARNING: don't run with debug turned on in production!
if cred['LOBSTER_SITE_DOMAIN'] in ALLOWED_HOSTS:
    log.info(f"Debug mode is active on Lobster host {ALLOWED_HOSTS}")
    DEBUG = True
    DEV = True
else:
    DEBUG = False
    DEV = False

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'rest_framework.authtoken',
    # 'rest_auth',
    # 'django_celery_results',
    'django_celery_beat',
    'octo',
    'octo_adm',
    'run_core',
    'octo_tku_upload',
    'octo_tku_patterns',
    'dev_site',
    'django_ftpserver',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # https://docs.djangoproject.com/en/3.0/topics/cache/#the-per-site-cache
    # 'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.cache.FetchFromCacheMiddleware',
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 60 * 60 * 5,
        'OPTIONS': {
            'server_max_value_length': 1024 * 1024 * 10,
        }
    }
}

ROOT_URLCONF = 'octo.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'static/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'octo.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
# https://stackoverflow.com/questions/26958592/django-after-upgrade-mysql-server-has-gone-away
# https://stackoverflow.com/questions/16946938/django-unknown-system-variable-transaction-on-syncdb
# noinspection SpellCheckingInspection
DATABASES = {
    'default': {
        'ENGINE': cred['ENGINE'],
        'NAME': cred['NAME'],
        'USER': cred['USER'],
        'PASSWORD': cred['PASSWORD'],
        'HOST': cred['HOST'],
        'PORT': cred['PORT'],
        'CONN_MAX_AGE': 3600,
        'OPTIONS': {
            # 'read_default_file': '/etc/my.cnf',
            'read_default_file': '/etc/my.cnf.d/win_mysql.cnf',
            # 'init_command': 'SET default_storage_engine=INNODB;'
            # 'init_command': 'SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED',
            # 'init_command': 'SET default_storage_engine=INNODB',
        },
    }
}

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

STATICFILES_DIRS = (
    os.path.join(STATIC_ROOT, 'admin'),
)

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators
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

# https://www.django-rest-framework.org/
REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 200,

}


# https://docs.djangoproject.com/en/2.0/topics/email/
EMAIL_HOST = cred['EMAIL_HOST']

# Mail addr:
if cred['LOBSTER_HOST'] in CURR_HOSTNAME:
    EMAIL_ADDR = cred['LOBSTER_EMAIL_ADDR']
elif cred['OCTOPUS_HOST'] in CURR_HOSTNAME:
    EMAIL_ADDR = cred['OCTOPUS_EMAIL_ADDR']
else:
    EMAIL_ADDR = cred['LOCAL_EMAIL_ADDR']

# Site domain:
if cred['LOBSTER_HOST'] in CURR_HOSTNAME:
    SITE_DOMAIN = cred['LOBSTER_SITE_DOMAIN']
    SITE_SHORT_NAME = cred['LOBSTER_SITE_SHORT_NAME']
elif cred['OCTOPUS_HOST'] in CURR_HOSTNAME:
    SITE_DOMAIN = cred['OCTOPUS_SITE_DOMAIN']
    SITE_SHORT_NAME = cred['OCTOPUS_SITE_SHORT_NAME']
else:
    SITE_DOMAIN = '127.0.0.1:8000'
    SITE_SHORT_NAME = 'LocalHost'

# Django registration:
ACCOUNT_ACTIVATION_DAYS = 7
REGISTRATION_OPEN = True

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/
LANGUAGE_CODE = 'en-us'

# TIME_ZONE = 'UTC'
TIME_ZONE = 'Europe/London'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# https://github.com/maxtepkeev/architect/issues/38
# https://github.com/celery/django-celery/issues/359
CONN_MAX_AGE = None

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'

ADMINS = mails['admin']
