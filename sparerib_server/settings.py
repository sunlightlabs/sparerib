import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG


TIME_ZONE = 'America/New_York'
LANGUAGE_CODE = 'en-us'

USE_TZ = True

STATIC_ROOT = ''
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
)

ROOT_URLCONF = 'sparerib_server.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'sparerib_server.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
)

INSTALLED_APPS = (
    'django.contrib.staticfiles',
    'djangorestframework',
    'sparerib_api',
    'sparerib_public'
)

try:
    from local_settings import *
except:
    pass