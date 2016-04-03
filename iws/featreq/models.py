import uuid
from collections import OrderedDict
from django.db import models

# Feature request details
class FeatureReq(models.Model):
    """Feature request details"""

    class Meta:
        verbose_name = 'Feature request'
        verbose_name_plural = 'Feature requests'
        db_table = 'featreqs'
        # ordering = ['date_cr']

    # Product areas
    POLICIES = 'PO'
    BILLING = 'BI'
    CLAIMS = 'CL'
    REPORTS = 'RE'
    AREA_CHOICES = (
        (POLICIES, 'Policies'),
        (BILLING, 'Billing'),
        (CLAIMS, 'Claims'),
        (REPORTS, 'Reports'),
        ('', 'Select area')
    )

    # Fields
    # TODO: add help_text for some/all?

    # UUIDv4 for long-term sanity
    id = models.UUIDField('Feature ID', primary_key=True, default=uuid.uuid4, editable=False)
    # Title, summary, subject line, whatever you want to call it
    title = models.CharField('Summary', max_length=128)
    # Full description
    desc = models.TextField('Description')
    # URL for reference in ticket
    # TODO: possibly make many-to-many?
    ref_url = models.URLField('Reference URL', max_length=254, blank=True, default='')
    # Product area
    # (Defined as choices instead of on separate table to keep model simpler)
    prod_area = models.CharField('Product area', max_length=2, blank=False, choices=AREA_CHOICES)
    # Date/time first created (indexed)
    date_cr = models.DateTimeField('Created at', auto_now_add=True, db_index=True)
    # Date/time last updated
    date_up = models.DateTimeField('Updated at', auto_now=True)

    # User relations
    # Stores username as string, to keep the joins down

    # Username of request creator
    user_cr = models.CharField('Created by', max_length=30, blank=False, editable=False)
    # Username of latest updater
    user_up = models.CharField('Updated by', max_length=30, blank=False, editable=False)

    @staticmethod
    def strtoid(idstr):
        return uuid.UUID(idstr)

    def __str__(self):
        return str(self.id)


# Client details
class ClientInfo(models.Model):
    """Client information"""

    class Meta:
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        db_table = 'clients'
        # ordering = ['name']

    # UUIDv4 for long-term sanity
    id = models.UUIDField('Client ID', primary_key=True, default=uuid.uuid4, editable=False)
    # Basic details
    name = models.CharField('Client name', max_length=64, db_index=True)
    con_name = models.CharField('Contact name', max_length=64, blank=True, default='')
    con_mail = models.EmailField('Contact email', blank=True, default='')
    date_add = models.DateTimeField('Date added', auto_now_add=True)

    # Open/closed request lists
    openreqs = models.ManyToManyField(FeatureReq, related_name='open_clients', through='OpenReq')
    closedreqs = models.ManyToManyField(FeatureReq, related_name='closed_clients', through='ClosedReq')

    @staticmethod
    def strtoid(idstr):
        return uuid.UUID(idstr)

    def __str__(self):
        return str(self.id)


## Request relations
# Normally we'd use an abstract base class here, and subclass for open/closed,
# but Django doesn't let us (easily) override constraints on inherited fields
# (in this case, we'd like a uniqueness constraint on priority while open, but
# remove it when closing), so instead we repeat ourselves (sadly).

# Open requests
class OpenReq(models.Model):
    """Open requests"""

    class Meta:
        db_table = 'openreqs'
        unique_together = ['req', 'client']
        # ordering = ['priority', 'clientid']

    # Feature request in question
    req = models.ForeignKey(FeatureReq, on_delete=models.CASCADE, related_name='open_reqs')
    # Client attached
    client = models.ForeignKey(ClientInfo, on_delete=models.CASCADE, related_name='open_reqs')
    # Client's priority (must be unique or null)
    priority = models.SmallIntegerField('Priority', unique=True, blank=True, null=True, default=None)
    # Target date (not strictly required)
    date_tgt = models.DateField('Target date', blank=True, null=True, default=None)
    # Open date/time
    opened_at = models.DateTimeField('Opened at', auto_now_add=True, db_index=True)
    # Opened by user (stored as username string instead of foreign key (for archival purposes))
    opened_by = models.CharField('Opened by', max_length=30, blank=False, editable=False)


# Closed requests
class ClosedReq(models.Model):
    """Closed requests"""

    class Meta:
        db_table = 'closedreqs'
        unique_together = ['req', 'client']
        # ordering = ['closed_at']

    COMPLETE = 'C'
    REJECTED = 'R'
    DEFERRED = 'D'

    STATUS_CHOICES = (
        (COMPLETE, 'Complete'),
        (REJECTED, 'Rejected'),
        (DEFERRED, 'Deferred')
    )

    # Feature request in question
    req = models.ForeignKey(FeatureReq, on_delete=models.CASCADE, related_name='closed_reqs')
    # Client attached
    client = models.ForeignKey(ClientInfo, on_delete=models.CASCADE, related_name='closed_reqs')
    # Priority and target date at the point of closing (not unique, can be blank)
    priority = models.SmallIntegerField('Priority', blank=True, null=True, default=None)
    date_tgt = models.DateField('Target date', blank=True, null=True, default=None)
    # Open details (taken from open request)
    opened_at = models.DateTimeField('Opened at', blank=False, editable=False)
    opened_by = models.CharField('Opened by', max_length=30, blank=False, editable=False)
    # Closed by user (stored as username string instead of foreign key (for archival purposes))
    closed_at = models.DateTimeField('Closed at', auto_now_add=True, db_index=True)
    closed_by = models.CharField('Closed by', max_length=30, blank=False, editable=False)
    # Closed status
    status = models.CharField('Closed as', max_length=1, default=COMPLETE, choices=STATUS_CHOICES)
    reason = models.CharField('Details', max_length=128, blank=True, default='')


