"""
Django settings for director project.

Generated by 'django-admin startproject' using Django 1.9b1.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

import os
import sys
import socket

# Set host and IP address
try:
    HOSTNAME = socket.gethostname()
except:
    HOSTNAME = None
try:
    IP = socket.gethostbyname(HOSTNAME)
except:
    IP = None

# Set deployment mode
if len(sys.argv) > 1 and sys.argv[1] in ('runserver', 'runsslserver'):
    MODE = 'local'
elif HOSTNAME == 'stencila-director-vagrant':
    MODE = 'vagrant'
elif HOSTNAME == 'stencila-director-prod':
    MODE = 'prod'
else:
    MODE = 'local'  # Fallback for when running "./manage.py makemigrations" etc

# Set Django settings accordingly
DEBUG = MODE != 'prod'


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Secrets

def secret(name):
    '''
    Get a secret from the filesystem
    '''
    return file(os.path.join(BASE_DIR, '..', '..', 'secrets')).read()


# Django's secret key
if MODE in ('local', 'vagrant'):
    SECRET_KEY = 'an-insecure-key-only-used-in-development'
else:
    SECRET_KEY = secret('director-secret-key')

# Keys for UserTokens
if MODE in ('local', 'vagrant'):
    # Use an insecure version during development
    USER_TOKEN_01_PASSWORD, USER_TOKEN_01_SECRET = ''.join(['P']*32), ''.join(['S']*32)
else:
    USER_TOKEN_01_PASSWORD, USER_TOKEN_01_SECRET = secret('director-usertoken').split()

# Token for communication between roles
if MODE in ('local', 'vagrant'):
    COMMS_TOKEN = 'an-insecure-token-only-used-in-development'
else:
    COMMS_TOKEN = secret('comms-token')

# AWS keys for launching session hosts and for email
if MODE in ('prod',):
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY = secret('aws-access-key').split()


# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.9/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    'stenci.la',
    'www.stenci.la',
    'localhost',
    '127.0.0.1'
]

# A tuple that lists people who get code error notifications.
# When DEBUG=False and a view raises an exception,
# Django will email these people with the full exception
# information.
ADMINS = (
    ('Nokome Bentley', 'nokome@stenci.la'),
)

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django.contrib.sites',  # Required by allauth

    # Third party apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    # Social account providers. See
    #    http://django-allauth.readthedocs.org/en/latest/providers.html
    # When you add an item here you must:
    #   - add an entry in SOCIALACCOUNT_PROVIDERS below
    #   - register Stencila as an API client or app with the provider
    #   - add a SocialApp instance (/admin/socialaccount/socialapp/add/) adding the credentials provided by the provider
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.linkedin',
    'allauth.socialaccount.providers.twitter',

    'debug_toolbar',
    'django_user_agents',
    'reversion',

    # Stencila apps
    'accounts',
    'components',
    'sessions_',
    'users',
    'visits'
]

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Third party middleware
    'django_user_agents.middleware.UserAgentMiddleware',

    # Stencila custom middleware
    'general.authentication.AuthenticationMiddleware',
    'general.errors.ErrorMiddleware',
]

ROOT_URLCONF = 'urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'general', 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                # This project's custom context variables
                'general.context_processors.custom'
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

if MODE in ('local', 'vagrant'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
elif MODE in ('prod',):
    user, password = secret('director-postgres').split()
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            # This AWS RDS instance is not publically accessible.
            # It is in a private subnet of the `stencila-vpc` AWS VPC.
            'HOST': 'stencila-hub-db.cjmf4xvritk9.us-west-2.rds.amazonaws.com',
            'PORT': '5432',
            'NAME': 'stencilahubdb',
            'USER': user,
            'PASSWORD': password,
        }
    }
else:
    raise EnvironmentError('Database not configured for MODE %s' % MODE)


# Password validation
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators

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


# Migrations
# Disable when testing. See:
#   http://stackoverflow.com/questions/25161425/disable-migrations-when-running-unit-tests-in-django-1-7
#   https://gist.github.com/NotSqrt/5f3c76cd15e40ef62d09
if len(sys.argv) > 1 and sys.argv[1] == 'test':

    class DisableMigrations(object):
        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            return "notmigrations"

    MIGRATION_MODULES = DisableMigrations()


# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = (
    # General static files, not tied to a particular app
    os.path.join(BASE_DIR, 'general', 'static'),
)

###############################################################################
# Installed apps settings

# django.contrib.sites
SITE_ID = 1

# django.contrib.auth
AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',

    # Stencila custom auth backends
    'general.authentication.BasicAuthBackend',
    'general.authentication.TokenAuthBackend',
)
LOGIN_URL = '/me/login'
LOGIN_REDIRECT_URL = '/'

# django-allauth
#
# For a full list of configuration options see
#   http://django-allauth.readthedocs.org/en/latest/configuration.html
#
# Specifies the adapter class to use, allowing you to override certain default behaviour.
SOCIALACCOUNT_ADAPTER = 'general.allauth_adapter.SocialAccountAdapter'
# Is the user required to provide an e-mail address when signing up?
ACCOUNT_EMAIL_REQUIRED = True
# Request e-mail address from 3rd party account provider?
SOCIALACCOUNT_QUERY_EMAIL = True
# Settings for each provider
SOCIALACCOUNT_PROVIDERS = {
    'facebook': {
        # See https://github.com/pennersr/django-allauth#facebook
        # Manage the app at http://developers.facebook.com logged in as user `stencila`
        'SCOPE': ['email'],
        'METHOD': 'oauth2',
    },
    'github': {
        # See http://developer.github.com/v3/oauth/#scopes for list of scopes available
        # At the time of writing it was not clear if scopes are implemented in allauth for Github
        # see https://github.com/pennersr/django-allauth/issues/369
        # Manage the app at https://github.com/organizations/stencila/settings/applications/74505
        'SCOPE': ['user:email']
    },
    'google': {
        # Manage the app at
        #   https://code.google.com/apis/console/
        #   https://cloud.google.com/console/project/582496091484/apiui/credential
        #   https://cloud.google.com/console/project/582496091484/apiui/consent
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'}
    },
    'linkedin': {
        # Manage the app at
        #  https://www.linkedin.com/secure/developer?showinfo=&app_id=3129843&acc_id=1654593&compnay_name=Stencila&app_name=Stencila
        # logged in as a user with access rights to the app
        # The scopes are listed on the above page
        'SCOPE': ['r_fullprofile', 'r_emailaddress'],
        'PROFILE_FIELDS': [
            'id',
            'first-name',
            'last-name',
            'email-address',
            'picture-url',
            'public-profile-url'
        ]
    },
    'twitter': {
        # Manage the app at https://dev.twitter.com/apps/5640979/show logged in as user `stencila`
    },
}

###########################################################################################
# Localizable settings
#
# Stuff which developers might wan't to override in their own settings_local.py

# Should a stub be used so that code can be tested during development\
# without a running curator
CURATOR_STUB = False

try:
    from local_settings import *
except ImportError:
    pass
