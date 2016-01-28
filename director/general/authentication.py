'''
Module for custom authentication backends, middleware and decorators.
'''
import base64
from importlib import import_module
import random
import string

from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout, get_user
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, load_backend
from django.contrib.sessions.models import Session
from django.conf import settings

SessionStore = import_module(settings.SESSION_ENGINE).SessionStore

from users.models import UserToken


def unauthenticated_response(content='Unauthenticated'):
    '''
    Create a response for a 401 error with additional required header WWW-Authenticate
    Similar to 403 Forbidden, but specifically for use when authentication is required and
    has failed or has not yet been provided.
    The response must include a WWW-Authenticate header field containing a
    challenge applicable to the requested resource.
    Some client will fail Basic Auth if it is not provided.
    '''
    response = HttpResponse(
        status=401,
        content=content
    )
    response['WWW-Authenticate'] = 'Basic realm="Restricted"'
    return response


def require_authenticated(view):
    '''
    A decorator to be used instead of @login_required when a view
    is intended for a program like git instead of a user.
    Returns a 401 (authentication required) response instead of
    redirecting to a login page.
    '''
    def wrapper(request, *args, **kwargs):
        if request.user.is_anonymous():
            return unauthenticated_response()
        else:
            return view(request, *args, **kwargs)
    return wrapper


# Authentication backends.
#
# These are trivial but necessary so that all the auth/session machinery works.
# Distinctive keyword arguments are used for backends so that django selects the correct backend
# when doing django.contrib.auth.authenticate().


class BasicAuthBackend(ModelBackend):

    def authenticate(self, stencila_basic_auth, username, password):
        if(username == 'Token' or username == ''):
            return UserToken.authenticate(password)
        return authenticate(username=username, password=password)


class TokenAuthBackend(ModelBackend):

    def authenticate(self, stencila_token_auth, **kwargs):
        return UserToken.authenticate(stencila_token_auth)


class AutoAuthBackend(ModelBackend):

    def authenticate(self, stencila_auto_auth, **kwargs):
        rand = ''.join(random.sample(string.lowercase+string.digits, 12))
        user = User.objects.create_user('user-'+rand)
        user.details.auto = True
        user.details.save()
        print user.username
        return user


class AuthenticationMiddleware:
    '''
    Custom authentication for API clients to use username/password,
    or token and then permit
    '''

    def process_request(self, request):
        # If the user is trying to signin/up then automatically log them out
        # This is logical and prevents them from not be able to get "out"
        # of an auto-user login
        if request.path=='/me/signin' or request.path=='/me/signup':
            logout(request)
            return

        # Get the authorization header
        auth = request.META.get('HTTP_AUTHORIZATION')
        if auth:
            # Split it into parts
            parts = auth.split()
            if len(parts) == 2:
                type = parts[0].lower()
                value = parts[1]
            else:
                raise Exception('Invalid authorization header')

            if request.user.is_anonymous():
                # If user not yet authenticated...
                try:
                    # Handle different types of authentication
                    if type == 'basic':
                        username, password = base64.b64decode(value).split(':')
                        user = authenticate(
                            stencila_basic_auth=True,
                            username=username,
                            password=password
                        )
                    elif type == 'token':
                        user = authenticate(
                            stencila_token_auth=value
                        )
                    else:
                        raise Exception('Invalid authorization type: '+type)
                except:
                    # If anything failed in the authentication then set the user to None
                    user = None

                # If user authentication failed (e.g. wrong credentials)
                # the user None. So return a response to let them know
                if user is None:
                    return unauthenticated_response('Authentication failed')

                # Need to login user so that session is associated
                # with user.
                if type == 'basic' or type == 'token':
                    login(request, user)
        else:
            if request.user.is_anonymous() and not request.user_agent.is_bot:
                # Fallback to  AuthAuth
                user = authenticate(
                    stencila_auto_auth=True,
                    username='',
                    password=''
                )
                if user:
                    login(request, user)
