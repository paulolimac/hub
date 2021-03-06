import datetime
import hashlib
import secrets
import typing
from io import BytesIO

from django.db import models

from accounts.models import Account
from projects.source_models import Source, FileSource

TOKEN_HASH_FUNCTION = hashlib.sha256
PROJECT_KEY_LENGTH = 32
TRUNCATED_TOKEN_SHOW_CHARACTERS = 8


def generate_project_key() -> str:
    """Generate a random key for a SessionGroup."""
    return secrets.token_hex(PROJECT_KEY_LENGTH)


def generate_project_token(project: 'Project') -> str:
    """Generate a unique token for a Project based on its creator, creation date and a random string."""
    user_id = project.creator.id if project.creator else None
    created = project.created or datetime.datetime.now()
    return TOKEN_HASH_FUNCTION("{}{}{}".format(user_id, created, secrets.token_hex()).encode("utf8")).hexdigest()


class Project(models.Model):
    """A project."""

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name='projects',
        null=False,
        blank=False
    )

    name = models.TextField(
        null=True,
        blank=True,
        help_text="The name of the project"
    )

    creator = models.ForeignKey(
        'auth.User',
        null=True,  # Should only be null if the creator is deleted
        on_delete=models.SET_NULL,
        related_name='projects_created',
        help_text='User who created project'
    )

    created = models.DateTimeField(
        auto_now_add=True,
        help_text='When this project was created'
    )

    public = models.BooleanField(
        default=False,
        help_text='Should this project be publicly visible?'
    )

    description = models.TextField(
        null=True,
        blank=True,
        help_text="Brief description of the project"
    )

    token = models.TextField(
        null=True,
        blank=True,
        unique=True,
        help_text='A token to identify this project (in URLs etc)'
    )

    key = models.TextField(
        null=True,
        blank=True,
        help_text='Key required to create sessions for this project'
    )

    sessions_total = models.IntegerField(
        null=True,
        blank=True,
        help_text='Maximum total number of sessions that can be created for this project (null = unlimited)'
    )

    sessions_concurrent = models.IntegerField(
        null=True,
        blank=True,
        help_text='Maximum number of sessions allowed to run at one time for this project (null = unlimited)',
    )

    sessions_queued = models.IntegerField(
        null=True,
        blank=True,
        help_text='Maximum number of queued requests for a session for this project (null = unlimited)'
    )

    session_parameters = models.ForeignKey(
        'SessionParameters',
        related_name='projects',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text='The parameters that defines sessions created for this project'
    )

    def __str__(self):
        return 'Project #{}'.format(self.id)

    @staticmethod
    def create(project_type, creator):
        """
        Create a new editor of the given project_type.

        TODO: is this, and the following few methods, necessary?
        """
        raise NotImplementedError()

    @staticmethod
    def get_or_create(project_type, address, creator):
        """Get, or create, a project."""
        return Project.objects.get_or_create(
            address=address,
            creator=creator
        )

    @staticmethod
    def get_or_create_from_address(address, creator):
        """Get, or create, a project from an address."""
        # TODO Transform the address into type etc
        return Project.get_or_create(
            type=None,
            address=address,
            creator=creator
        )

    @staticmethod
    def get_or_create_from_url(url, creator):
        """
        Get, or create, a project from a URL.

        This method enables users to specify a project
        by copying a third party URL from the browser address bar.
        Converts the URL into an address. For example,

        https://github.com/stencila/examples/tree/master/mtcars

        is converted to,

        github://stencila/examples/mtcars
        """
        # TODO Transform the URL into an address
        address = url
        return Project.get_or_create_from_address(address, creator)

    def get_name(self):
        """A temporary implementation of a name property which is likely to be replaced by a db field in future."""
        return self.name or 'Unnamed'

    def get_first_source(self) -> Source:
        source = self.sources.first()  # TODO: Update this when UI supports multiple sources
        if not source:
            raise ValueError("This project has no sources")

        return source

    def pull(self) -> BytesIO:
        """Pull files from the project source."""
        return self.get_first_source().pull()

    def push(self, archive: typing.IO) -> None:
        """Push files to the project source."""
        self.get_first_source().push(archive)

    def save(self, *args, **kwargs) -> None:
        if not self.token:
            self.token = generate_project_token(self)

        if not self.session_parameters:
            from projects.session_models import SessionParameters
            self.session_parameters = SessionParameters.objects.create()

        super().save(*args, **kwargs)

    @property
    def truncated_token(self) -> str:
        """Chop out the middle of the token for short display."""
        return "{}...{}".format(self.token[:TRUNCATED_TOKEN_SHOW_CHARACTERS],
                                self.token[-TRUNCATED_TOKEN_SHOW_CHARACTERS:])

    # TODO: the `_pull` and `_push` methods below are just saved from a previous
    # iteration of FilesSource, not sure we'll want to keep them.

    def _pull(self) -> BytesIO:
        """Pull files from the Django storage into an archive."""
        from zipfile import ZipFile

        # Write all the files into a zip archive
        archive = BytesIO()
        with ZipFile(archive, 'w') as zipfile:
            for file in self.files.all():
                # For remote storages (e.g. Google Cloud Storage buckets)
                # `file.file.path` is not available, so use `file.file.read()`
                zipfile.writestr(file.name, file.file.read())
        return archive

    def _push(self, archive: typing.Union[str, typing.IO]) -> None:
        """Push files in the archive to the Django storage."""
        import timezone
        from zipfile import ZipFile

        # Unzip all the files and add to this project
        zipfile = ZipFile(archive, 'r')
        for name in zipfile.namelist():
            # Replace existing file or create a new one
            instance = FileSource.objects.get_or_create(project=self, name=name)

            # Read the file from the zipfile
            content = BytesIO()
            content.write(zipfile.read(name))
            content.seek(0)
            # Create a new file with contents and name
            instance.file.save(name, content, save=False)
            instance.modified = datetime.datetime.now(tz=timezone.utc)
            instance.save()
