import typing

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpRequest

from lib.forms import FormWithSubmit, ModelFormWithSubmit
from .models import FilesSource, SessionParameters, Source, Project, generate_project_key


def get_initial_form_data_from_project(project: typing.Optional[Project]) -> dict:
    if not project:
        return {}

    initial = {
        key: getattr(project, key) for key in
        ('token', 'key', 'max_concurrent', 'max_sessions', 'session_parameters', 'public')
    }

    initial['source'] = project.sources.first()

    return initial


def update_general_project_data(project: Project, general_data: dict, save: bool = False) -> None:
    project.name = general_data['name']
    project.public = general_data['public']
    # at this stage assume a 1:1 mapping Project:Source even though the DB support multiple sources
    # update this when allowing for 1:n mapping in the UI
    project.sources.clear()
    if general_data['source']:
        project.sources.add(general_data['source'])

    if save:
        project.save()


def update_session_parameters_project_data(project: Project, request: HttpRequest, parameters_data: dict,
                                           session_data: dict, save: bool = False) -> None:
    project.max_concurrent = session_data['max_concurrent']
    project.max_sessions = session_data['max_sessions']

    if save:
        project.save()

    session_parameters = project.session_parameters or SessionParameters(owner=request.user)
    session_parameters.memory = parameters_data['memory']
    session_parameters.cpu = parameters_data['cpu']
    session_parameters.network = parameters_data['network']
    session_parameters.lifetime = parameters_data['lifetime']
    session_parameters.timeout = parameters_data['timeout']
    session_parameters.save()

    if project.session_parameters != session_parameters:
        project.session_parameters = session_parameters
        project.save()


def update_access_project_data(project: Project, access_data: dict, save: bool = False) -> None:
    if access_data['generate_key']:
        project.key = generate_project_key()
    else:
        project.key = access_data['key']

    if save:
        project.save()


def update_project_from_form_data(request: HttpRequest, project: Project, general_data: dict, session_data: dict,
                                  parameters_data: dict, access_data: dict) -> None:
    update_general_project_data(project, general_data)
    update_access_project_data(project, access_data)
    update_session_parameters_project_data(project, request, parameters_data, session_data)


class SaveButtonMixin:
    submit_button_label = "Save"


class CreateButtonMixin:
    submit_button_label = "Create"


class ProjectForm(FormWithSubmit):
    """
    Form for creating a Project
    """

    public = forms.BooleanField(
        required=False,
        help_text="Make this project available to anyone."
    )

    token = forms.CharField(
        required=False,
        disabled=True,
        help_text='Unique token identifying this group. This will be generated when first saved.',
        widget=forms.TextInput(attrs={"v-model": "token"})
    )

    key = forms.CharField(
        label="Access Key",
        required=False,
        max_length=128,
        help_text="This key needs to be used when creating a Session. Leave blank to not require a key.",
        widget=forms.TextInput(attrs={"v-model": "key"})
    )

    generate_key = forms.BooleanField(
        required=False,
        help_text="Automatically generate an access key when saved.",
        widget=forms.CheckboxInput(attrs={"v-model": "generateKey", "@change": "generateKeyChange()"})
    )

    max_concurrent = forms.IntegerField(
        required=False,
        min_value=1,
        help_text='The maximum number of sessions to run at one time. Leave blank for unlimited.'
    )

    max_sessions = forms.IntegerField(
        required=False,
        min_value=1,
        help_text='The total maximum number of sessions allowed to create. Leave blank for unlimited.'
    )

    session_parameters = forms.ModelChoiceField(
        required=True,
        queryset=SessionParameters.objects.none(),  # this needs to be set at runtime
        help_text='The Session Parameters to use to define resources when creating new Sessions in this project.'
    )

    source = forms.ModelChoiceField(
        required=False,
        queryset=Source.objects.none(),  # this needs to be set at runtime,
        help_text='The data for this Project'
    )

    def populate_choice_fields(self, user: User):
        self.fields['session_parameters'].queryset = SessionParameters.objects.filter(owner=user)

        source_query = Q(creator=user)

        if 'source' in self.initial:
            source_query = source_query | Q(pk=self.initial['source'].id)

        self.fields['source'].queryset = Source.objects.filter(source_query)

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data['max_sessions'] is not None and (
                cleaned_data['max_concurrent'] is None
                or cleaned_data['max_concurrent'] > cleaned_data['max_sessions']):
            self.add_error('max_concurrent',
                           "The maximum number of concurrent sessions must be less than the maximum number of total "
                           "sessions.")

        return cleaned_data


class ProjectCreateForm(CreateButtonMixin, ProjectForm):
    pass


class ProjectUpdateForm(SaveButtonMixin, ProjectForm):
    pass


class SessionParametersForm(ModelFormWithSubmit):
    submit_button_label = None

    class Meta:
        model = SessionParameters
        fields = ['name', 'description', 'memory', 'cpu', 'network', 'lifetime', 'timeout']

        widgets = {
            'name': forms.TextInput
        }

        labels = {
            'cpu': 'CPU'
        }

        help_texts = {
            'network': 'Gigabytes (GB) of network transfer allocated. Leave blank for unlimited.',
            'lifetime': 'Minutes before the session is terminated (even if active). Leave blank for unlimited.',
            'timeout': 'Minutes of inactivity before the session is terminated. Leave blank for unlimited.'
        }

    def clean(self) -> dict:
        cleaned_data = super().clean()

        if cleaned_data['lifetime'] is not None and (
                cleaned_data['timeout'] is None
                or cleaned_data['timeout'] > cleaned_data['lifetime']):
            self.add_error('timeout', 'The idle timeout must be less that the maximum lifetime of the Session.')

        return cleaned_data


class SessionParametersUpdateForm(SaveButtonMixin, SessionParametersForm):
    pass


class SessionParametersCreateForm(CreateButtonMixin, SessionParametersForm):
    pass


class FilesSourceForm(ModelFormWithSubmit):
    class Meta:
        model = FilesSource
        fields = ["project"]


class FilesSourceUpdateForm(SaveButtonMixin, FilesSourceForm):
    pass


class FilesSourceCreateForm(CreateButtonMixin, FilesSourceForm):
    pass


class ProjectGeneralForm(forms.Form):
    helper = FormHelper()

    name = forms.CharField(
        required=False,
        widget=forms.TextInput
    )

    public = forms.BooleanField(
        required=False,
        help_text="Make this project available to anyone."
    )

    source = forms.ModelChoiceField(
        required=False,
        queryset=Source.objects.none(),  # this needs to be set at runtime,
        help_text="The data for this Project"
    )

    @staticmethod
    def initial_data_from_project(project: typing.Optional[Project]) -> dict:
        if project is None:
            return {}

        initial = {
            key: getattr(project, key) for key in
            ('name', 'max_concurrent', 'max_sessions', 'session_parameters', 'public')
        }

        initial['source'] = project.sources.first()

        return initial

    def populate_source_choices(self, request: HttpRequest) -> None:
        self.fields['source'].queryset = Source.objects.filter(creator=request.user)


class ProjectSessionsForm(forms.Form):
    helper = FormHelper()

    max_concurrent = forms.IntegerField(
        required=False,
        min_value=1,
        help_text='The maximum number of sessions to run at one time. Leave blank for unlimited.'
    )

    max_sessions = forms.IntegerField(
        required=False,
        min_value=1,
        help_text='The total maximum number of sessions allowed to create. Leave blank for unlimited.'
    )

    @staticmethod
    def initial_data_from_project(project: typing.Optional[Project]) -> dict:
        return {} if project is None else {
            "max_concurrent": project.max_concurrent,
            "max_sessions": project.max_sessions
        }

    def clean(self) -> dict:
        cleaned_data = super().clean()

        if cleaned_data['max_sessions'] is not None and (
                cleaned_data['max_concurrent'] is None
                or cleaned_data['max_concurrent'] > cleaned_data['max_sessions']):
            self.add_error('max_concurrent',
                           'The maximum number of concurrent Sessions must be less than the maximum total Sessions.')
        return cleaned_data


class ProjectSessionParametersForm(forms.Form):
    helper = FormHelper()

    max_concurrent = forms.IntegerField(
        required=False,
        min_value=1,
        help_text='The maximum number of sessions to run at one time. Leave blank for unlimited.'
    )

    max_sessions = forms.IntegerField(
        required=False,
        min_value=1,
        help_text='The total maximum number of sessions allowed to create. Leave blank for unlimited.'
    )

    memory = forms.FloatField(
        # default=1,
        min_value=0,
        required=True,
        help_text='Gigabytes (GB) of memory allocated.',
        widget=forms.NumberInput(attrs={"v-model": "spMemory"})
    )

    cpu = forms.FloatField(
        label="CPU",
        required=True,
        min_value=1,
        max_value=100,
        # default=1,
        help_text='CPU shares (out of 100 per CPU) allocated.',
        widget=forms.NumberInput(attrs={"v-model": "spCpu"})
    )

    network = forms.FloatField(
        min_value=0,
        required=False,
        help_text='Gigabytes (GB) of network transfer allocated. Leave blank for unlimited.',
        widget=forms.NumberInput(attrs={"v-model": "spNetwork"})
    )

    lifetime = forms.IntegerField(
        min_value=0,
        required=False,
        help_text='Minutes before the session is terminated (even if active). Leave blank for unlimited.',
        widget=forms.NumberInput(attrs={"v-model": "spLifetime"})
    )

    timeout = forms.IntegerField(
        # default=60,
        min_value=0,
        required=True,
        help_text='Minutes of inactivity before the session is terminated. Leave blank for unlimited.',
        widget=forms.NumberInput(attrs={"v-model": "spTimeout"})
    )

    def clean(self) -> dict:
        cleaned_data = super().clean()

        if cleaned_data['lifetime'] is not None and (
                cleaned_data['timeout'] is None
                or cleaned_data['timeout'] > cleaned_data['lifetime']):
            self.add_error('timeout', 'The idle timeout must be less that the maximum lifetime of the Session.')

        if cleaned_data['max_sessions'] is not None and (
                cleaned_data['max_concurrent'] is None
                or cleaned_data['max_concurrent'] > cleaned_data['max_sessions']):
            self.add_error('max_concurrent',
                           'The maximum number of concurrent Sessions must be less than the maximum total Sessions.')
        return cleaned_data

    @staticmethod
    def initial_data_from_project(project: typing.Optional[Project]) -> dict:
        initial = {}

        if project is None:
            return {}

        initial['max_sessions'] = project.max_sessions
        initial['max_concurrent'] = project.max_concurrent

        if project.session_parameters:
            initial['memory'] = project.session_parameters.memory
            initial['cpu'] = project.session_parameters.cpu
            initial['network'] = project.session_parameters.network
            initial['lifetime'] = project.session_parameters.lifetime
            initial['timeout'] = project.session_parameters.timeout

        return initial


class ProjectAccessForm(forms.Form):
    helper = FormHelper()

    token = forms.CharField(
        required=False,
        disabled=True,
        help_text='Unique token identifying this group. This will be generated when first saved.',
        widget=forms.TextInput(attrs={"v-model": "token", ":disabled": "generateKey"})
    )

    key = forms.CharField(
        label="Access Key",
        required=False,
        max_length=128,
        help_text="This key needs to be used when creating a Session. Leave blank to not require a key.",
        widget=forms.TextInput(attrs={"v-model": "key", ":disabled": "generateKey"})
    )

    generate_key = forms.BooleanField(
        required=False,
        help_text="Automatically generate an access key on save.",
        widget=forms.CheckboxInput(attrs={"v-model": "generateKey", "@change": "generateKeyChange()"})
    )

    @staticmethod
    def initial_data_from_project(project: Project) -> dict:
        return {} if project is None else {
            'token': project.token,
            'key': project.key
        }
