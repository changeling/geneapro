"""
Django settings for backend project.

Generated by 'django-admin startproject' using Django 1.10.6.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
import appdirs
import sys
from traceback import format_stack

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '%xg3dwf1s$pp=(%@)46)vxz0ti9$na=x%5s_f0qm!ced0n!0q0'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False  # in case of exception, prints local variables, which results
               # in a lot of queries
SHOW_SQL = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'geneaprove',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'backend.middleware.simple_exception.AJAXSimpleExceptionResponse',
    'backend.middleware.profile.ProfileMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

GENEAPROVE_STATIC_ROOT = os.path.realpath(
    os.path.join(BASE_DIR, "../dist"))

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [GENEAPROVE_STATIC_ROOT,
                 os.path.realpath(os.path.join(BASE_DIR, 'geneaprove', 'views'))],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(
            appdirs.user_data_dir(
                appname='geneaprove',
                appauthor='geneaprove',
                version='1.0',
                roaming=True),
            'geneaprove.sqlite'),
        'CHUNK_SIZE': 996
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Paris'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    GENEAPROVE_STATIC_ROOT
]

class WithStacktrace(object):
    "https://blog.ionelmc.ro/2013/12/10/adding-stacktraces-to-log-messages/"
    def __init__(self, skip=(), limit=5):
        self.skip = [__name__, 'logging']
        self.skip.extend(skip)
        self.limit = limit

    def filter(self, record):
        if not hasattr(record, 'stack_patched'):
            frame = sys._getframe(1)
            if self.skip:
                while frame.f_back and [
                    skip for skip in self.skip
                    if frame.f_globals.get('__name__', '').startswith(skip)
                ]:
                    frame = frame.f_back

            bt = ''.join(format_stack(f=frame, limit=self.limit)).rstrip()
            record.msg += f" -- Stack: \n{bt}"
            record.stack_patched = True
        return True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'add_stack': {
            '()': WithStacktrace,
            'skip': ("django.db", "south.", "__main__"),
            'limit': 1   # just one frame
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(asctime)s %(funcName)s %(message)s'
        },
        'simplegray': {
            'format': '\033[2m%(asctime)s %(message)s\033[0m'
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'geneaprove.log',
            'formatter': 'simple'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'consolegray': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simplegray',
        },
    },
    'loggers': {
        'geneaprove': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },

        # Those are disabled in gedcomimport.py
        'django.db.backends': {   # Logging SQL queries
            'handlers': ['console'],
            'level': 'DEBUG' if SHOW_SQL else 'ERROR',
            'filters': ['add_stack'],
            'propagate': False,
        }
    }
}

