"""
Views that implement some of the Stencila Host API endpoints
for a project
"""
import typing

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from projects.cloud_session_controller import CloudClient, CloudSessionFacade, ActiveSessionsExceededException
from projects.models import Project
from projects.session_models import Session, SessionRequest

SESSION_URL_SESSION_KEY_FORMAT = 'CLOUD_SESSION_URL_{}_{}'
SESSION_REQUEST_SESSION_KEY_FORMAT = 'SESSION_REQUEST_ID_{}'
SESSION_REQUEST_IS_NEXT_KEY_FORMAT = 'SESSION_REQUEST_NEXT_{}'


class ProjectHostBaseView(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        response = super().dispatch(*args, **kwargs)
        origin = self.request.META.get('HTTP_ORIGIN')
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Credentials'] = 'true'
        return response


class ProjectHostManifestView(ProjectHostBaseView):

    def get(self, request, token, version=1):
        project = get_object_or_404(Project, token=token)

        manifest = {
            'id': 'hub-project-host-{}'.format(project.id),
            'stencila': {
                'package': 'hub',
                'version': '0.1'
            },
            'environs': [
                # TODO: this should come from the list of environments
                # available for this project.
                {
                    'id': 'stencila/core',
                    'name': 'stencila/core',
                    'version': '0.1'
                }
            ],
            'services': []
        }

        # Modifications to manifest depending upon API version
        if version == 0:
            manifest['types'] = manifest['services']
            del manifest['services']

        return JsonResponse(manifest)


class CloudClientMixin(object):
    session_facade: CloudSessionFacade

    def setup_cloud_client(self, project: Project) -> None:
        # TODO: This will eventually come from the `SessionParameters` for this project
        host_url = settings.NATIVE_HOST_URL
        jwt_secret = settings.JWT_SECRET  # TODO: This will eventually come from the settings for the remote host

        cloud_client = CloudClient(host_url, jwt_secret)
        self.session_facade = CloudSessionFacade(project, cloud_client)


class ProjectSessionRequestView(CloudClientMixin, ProjectHostBaseView):
    api_version: int = 0

    @staticmethod
    def get_session_request(request: HttpRequest, token: str) -> typing.Optional[SessionRequest]:
        session_request_key = SESSION_REQUEST_SESSION_KEY_FORMAT.format(token)

        if session_request_key not in request.session:
            return None

        session_request_pk = request.session[session_request_key]

        try:
            return SessionRequest.objects.get(pk=session_request_pk)
        except SessionRequest.DoesNotExist:
            del request.session[session_request_key]

        return None

    @staticmethod
    def get_first_session_request(project: Project) -> typing.Optional[SessionRequest]:
        return SessionRequest.objects.filter(project=project).order_by('created').first()

    def project_has_sessions_available(self, project: Project) -> bool:
        if project.sessions_concurrent is None:
            return True

        return project.sessions_concurrent > self.session_facade.get_active_session_count()

    def session_can_start(self, request: HttpRequest, project: Project, token: str,
                          session_request: SessionRequest) -> bool:
        if not self.project_has_sessions_available(project):
            return False

        # there are available session spots, but is this request first in the queue?
        if self.get_first_session_request(project) != session_request:
            return False

        request.session[SESSION_REQUEST_IS_NEXT_KEY_FORMAT.format(token)] = True  # semaphore to shortcut checks
        # client should attempt the session start POST again and we let them through
        return True

    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        project = get_object_or_404(Project, token=token)

        session_request = self.get_session_request(request, token)

        if not session_request:
            # client should stop checking if they receive this
            return JsonResponse({'invalid_session': True})  # TODO: work out what a sensible response is

        self.setup_cloud_client(project)

        return JsonResponse({
            'start_session': self.session_can_start(request, project, token, session_request)
        })  # TODO: work out what a sensible response is


class ProjectHostSessionsView(CloudClientMixin, ProjectHostBaseView):
    api_version: int = 0

    def get_session_url_from_request_session(self, request: HttpRequest, session_key: str) -> typing.Optional[str]:
        if session_key not in request.session:
            return None

        session_url = request.session[session_key]
        try:
            session = Session.objects.get(url=session_url)
        except Session.DoesNotExist:
            return None

        if session.stopped is None:
            self.session_facade.update_session_info(session)

        if session.stopped is not None and session.stopped <= timezone.now():
            return None

        return session_url

    @staticmethod
    def get_session_request_to_use(request: HttpRequest, token: str) -> typing.Optional[SessionRequest]:
        is_next_key = SESSION_REQUEST_IS_NEXT_KEY_FORMAT.format(token)

        if request.session.get(is_next_key) is not True:
            return None

        session_request_key = SESSION_REQUEST_SESSION_KEY_FORMAT.format(token)
        session_request_to_use = SessionRequest.objects.get(pk=request.session[session_request_key])
        del request.session[is_next_key]
        del request.session[session_request_key]

        return session_request_to_use

    def create_session_request(self, request: HttpRequest, token: str, environ: str) -> HttpResponse:
        session_request = self.session_facade.create_session_request(environ)
        request.session[SESSION_REQUEST_SESSION_KEY_FORMAT.format(token)] = session_request.pk
        return redirect(reverse('session_queue_v{}'.format(self.api_version), args=(token,)))

    def create_session(self, request: HttpRequest, environ: str, session_key: str,
                       session_request_to_use: typing.Optional[SessionRequest]) -> str:
        session = self.session_facade.create_session(environ, session_request_to_use)
        session_url = session.url
        request.session[session_key] = session_url
        return session_url

    def generate_response(self, request: HttpRequest, environ: str, session_key: str, token: str,
                          session_url: typing.Optional[str]) -> HttpResponse:
        if not session_url:
            session_request_to_use = self.get_session_request_to_use(request, token)

            try:
                session_url = self.create_session(request, environ, session_key, session_request_to_use)
            except ActiveSessionsExceededException:
                return self.create_session_request(request, token, environ)

        return JsonResponse({
            'url': session_url
        })

    def post(self, request: HttpRequest, token: str, environ: str) -> HttpResponse:
        project = get_object_or_404(Project, token=token)

        if project.key and request.POST.get("key") != project.key:
            raise PermissionDenied("The key in the POST request does not match that of the Project")

        self.setup_cloud_client(project)

        session_key = SESSION_URL_SESSION_KEY_FORMAT.format(token, environ)
        session_url = self.get_session_url_from_request_session(request, session_key)

        return self.generate_response(request, environ, session_key, token, session_url)
