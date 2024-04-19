"""
Django settings for lelantos project.

Generated by 'django-admin startproject' using Django 4.2.7.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-#f_)rvdq4a*u64hkz=j#ydg&i&kwj^6pgrco_-sl=o17%)m8!('

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["192.168.0.76", "127.0.0.1"]


# Application definition

INSTALLED_APPS = [
    'portal_auth.apps.PortalAuthConfig',
    'lelantos_base.apps.Wp3BasicConfig',
    'analysis.apps.AnalysisConfig',
    'aircrack_ng_broker.apps.AircrackNgBrokerConfig',
    'wifiphisher_broker.apps.WifiphisherBrokerConfig',
    'django_extensions',
    'django.contrib.gis',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lelantos.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'lelantos.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'NAME': os.path.join(BASE_DIR, 'dbWithGeo.sqlite3'),
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ]
}

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIR = [os.path.join(BASE_DIR,"static")]

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_EXPIRE_AT_BROWSER_CLOSE=True

# wp3 api settings - deprecated
# from wp3_broker.wp3_api_config import *

# Default location settings (default N.I belfast area)
DEFAULT_LOCATION_SETTINGS = {'default_lat': 54.5966, 'default_lon': -5.9301}
CONVERT_COORDS_FOR_MAP=True

# can be generated with folium_colours=list(folium.Icon.color_options) but this ordering is prettier
folium_colours = ["red", 
                  "blue",
                  "green",
                  "purple",
                  "orange",
                  "darkred",
                  "lightred",
                  "beige",
                  "darkblue",
                  "darkgreen",
                  "cadetblue",
                  "darkpurple",
                  "white",
                  "pink",
                  "lightblue",
                  "lightgreen",
                  "gray",
                  "black",
                  "lightgray"]

# aircrack settings - TODO - move to urls pattern
from aircrack_ng_broker.aircrack_ng_config import *
AIRCRACK_SCAN_RESULTS_PATH=os.path.join(BASE_DIR, AIRCRACK_REL_SCAN_DIR)

# Make dir if not present
if not os.path.isdir(AIRCRACK_SCAN_RESULTS_PATH):
    # TODO - logger
    print(f'Creating temp directory at {AIRCRACK_SCAN_RESULTS_PATH} for scan result files')
    os.makedirs(AIRCRACK_SCAN_RESULTS_PATH)
else:
    print(f'Saving temp scan results to {AIRCRACK_SCAN_RESULTS_PATH}')
