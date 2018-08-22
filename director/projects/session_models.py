import enum

import django.db.models as models
from django.urls import reverse
from django.utils import timezone


class SessionStatus(enum.Enum):
    UNKNOWN = 'Unknown'
    NOT_STARTED = 'Not Started'
    RUNNING = 'Running'
    STOPPED = 'Stopped'


class Session(models.Model):
    """
    An execution Session
    """
    project = models.ForeignKey(
        'Project',
        null=False,
        on_delete=models.PROTECT,  # Don't want to delete references if the container is running and we need control still
        related_name='sessions',
        help_text='The Project that this Session belongs to.'
    )

    url = models.URLField(
        help_text='URL for API access to administrate this Session'
    )

    started = models.DateTimeField(
        null=True,
        help_text='DateTime this Session was started'
    )

    stopped = models.DateTimeField(
        null=True,
        help_text='DateTime this Session was stopped (or that we detected it had stopped)'
    )

    last_check = models.DateTimeField(
        null=True,
        help_text='The last time the status of this Session was checked'
    )

    @property
    def status(self) -> SessionStatus:
        if self.last_check is None:
            return SessionStatus.UNKNOWN

        if self.stopped is not None and self.stopped <= timezone.now():
            return SessionStatus.STOPPED

        if self.started is not None and self.started <= timezone.now():
            return SessionStatus.RUNNING

        return SessionStatus.NOT_STARTED


class SessionParameters(models.Model):
    """
    Defines the parameters for new Sessions created in a Project
    """
    owner = models.ForeignKey(
        'auth.User',
        null=True,  # Should only be null if the creator is deleted
        on_delete=models.SET_NULL,
        related_name='session_templates',
        help_text='User who owns the SessionParameters'
    )

    is_system = models.BooleanField(
        default=False,
        help_text='If True, this SessionParameters can be used by any user'
    )

    display_order = models.IntegerField(
        null=False,
        blank=True,
        default=0,
        help_text="The order this SessionParameter should be displayed in list/tables"
    )

    name = models.TextField(
        null=False,
        blank=False
    )

    description = models.TextField(
        null=True,
        blank=True,
        help_text='Optional long description about the SessionParameters'
    )

    memory = models.FloatField(
        default=1,
        null=False,
        blank=False,
        help_text='Gigabytes (GB) of memory allocated'
    )

    cpu = models.FloatField(
        default=1,
        null=False,
        blank=False,
        help_text='CPU shares (out of 100 per CPU) allocated'
    )

    network = models.FloatField(
        null=True,
        blank=True,
        help_text='Gigabytes (GB) of network transfer allocated. null = unlimited'
    )

    lifetime = models.IntegerField(
        null=True,
        blank=True,
        help_text='Minutes before the session is terminated. null = unlimited'
    )

    timeout = models.IntegerField(
        default=60,
        null=False,
        blank=False,
        help_text='Minutes of inactivity before the session is terminated'
    )

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse('sessionparameters_update', args=[self.pk])
