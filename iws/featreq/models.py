import datetime, json, uuid
from collections import OrderedDict
from django.db import models


# UUID v4 validation
def validuuid(uid, version=4):
    '''Ensures given uid argument is a valid UUID (default version 4)
    Returns UUID instance if valid, None if not.
    Can be a UUID instance, or any type which uuid.UUID() accepts as input.
    '''

    if isinstance(uid, uuid.UUID):
        # Easiest case, uid is already UUID
        # (UUID constructor chokes on UUID instances,
        # so we have to explicitly check)
        return uid
    else:
        # Attempt conversion, return if successful
        try:
            # Insist on version
            retuid = uuid.UUID(uid, version=version)
        except ValueError as e:
            # Invalid, return None instead of raising exception
            retuid = None

        return retuid

# Datetime string conversion
# Uses same format as Django internal, except without subsecond resolution
DATEFORMAT = '%Y-%m-%d %H:%M:%S'


# Product areas
AREA_CHOICES = (
    ('PO', 'Policies'),
    ('BI', 'Billing'),
    ('CL', 'Claims'),
    ('RE', 'Reports'),
    ('', 'Select area')
)
AREA_BY_TEXT = { v:k for k,v in AREA_CHOICES if k }
AREA_BY_SHORT = { k:v for k,v in AREA_CHOICES if k }


# Feature request manager
class FeatReqManager(models.Manager):
    """Model manager for FeatureReq"""

    def newrequest(self, user, title, desc, ref_url='', prod_area='Policies', id=None):
        # Check for required fields
        if not title:
            raise ValueError('Title field required')
        if not desc:
            raise ValueError('Description field required')
        if not user:
            raise ValueError('User field required')
        if prodarea not in AREA_BY_TEXT and prodarea not in AREA_BY_SHORT:
            raise ValueError('Invalid product area: {0}'.format(prodarea))

        # Gather args
        prod_area = prodarea if prodarea in AREA_BY_SHORT else AREA_BY_TEXT[prodarea]
        newargs = {
            'title': title,
            'desc': desc,
            'ref_url': refurl,
            'prod_area': prod_area,
            'user_cr': user,
            'user_up': user
        }

        # Check if uuid supplied, validate, and pass as arg
        if id:
            uid = validuuid(id)
            if uid:
                newargs['id'] = uid

        # Get datetime (will override auto) and shave off subseconds
        dt = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        newargs['date_cr'] = dt
        newargs['date_up'] = dt

        # Create new instance, validate fields, and save
        fr = FeatureReq(**newargs)
        fr.full_clean()
        fr.save()
        return fr


# Feature request details
class FeatureReq(models.Model):
    """Feature request details"""

    class Meta:
        verbose_name = 'request'
        verbose_name_plural = 'requests'
        db_table = 'featreqs'
        # ordering = ['date_cr']

    # Fields
    # TODO: add help_text for some/all?

    # Fields to serialize, in order
    fieldlist = ('id', 'title', 'desc', 'ref_url', 'prod_area', 'date_cr', 'user_cr', 'date_up', 'user_up')

    # UUIDv4 for long-term sanity
    id = models.UUIDField('Request ID', primary_key=True, default=uuid.uuid4, editable=False)
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
    # Stores username as string instead of foreign key
    # This means deleted users don't affect db integrity (and keeps joins down)

    # Username of request creator
    user_cr = models.CharField('Created by', max_length=30, blank=False, editable=False)
    # Username of latest updater
    user_up = models.CharField('Updated by', max_length=30, blank=False, editable=False)

    objects = FeatReqManager()

    @staticmethod
    def getprodareas():
        '''List allowed product areas'''
        return AREA_BY_TEXT

    @staticmethod
    def strtoid(idstr):
        '''Convert string to feature id'''
        return uuid.UUID(idstr)

    def __str__(self):
        return str(self.title)

    def jsondict(self):
        '''Returns JSON-compatible dict of model values.
        Uses OrderedDict to ensure values in model-specified order.
        '''
        # Can't do naive for loop due to req'd conversions
        fieldvals = [
            str(self.id),
            self.title,
            self.desc,
            self.ref_url,
            AREA_BY_SHORT[self.prod_area],
            self.date_cr.strftime(DATEFORMAT),
            self.user_cr,
            self.date_up.strftime(DATEFORMAT),
            self.user_up
        ]
        # Zip with fieldlist, and return OrderedDict
        return OrderedDict(zip(self.fieldlist, fieldvals))


# Client manager
class ClientManager(models.Manager):
    """Model manager for ClientInfo"""

    def newclient(self, name, con_name='', con_mail='', id=None):
        # Check arguments
        if not name:
            raise ValueError('Name field required')

        # Gather args
        newargs = {
            'name': name,
            'con_name': con_name,
            'con_mail': con_mail
        }

        # Check if id supplied and valid
        if id:
            uid = validuuid(id)
            if uid:
                newargs['id'] = uid

        # Create instance, validate fields, and save
        cl = ClientInfo(**newargs)
        cl.full_clean()
        cl.save()
        return cl


# Client details
class ClientInfo(models.Model):
    """Client information"""

    class Meta:
        verbose_name = 'client'
        verbose_name_plural = 'clients'
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

    objects = ClientManager()

    @staticmethod
    def strtoid(idstr):
        return uuid.UUID(idstr)

    def __str__(self):
        return str(self.name)


## Request relations
# Normally we'd use an abstract base class here, and subclass for open/closed,
# but Django doesn't let us (easily) override constraints on inherited fields
# (in this case, we'd like a uniqueness constraint on priority while open, but
# remove it when closing), so instead we repeat ourselves (sadly).

# Open requests
class OpenReq(models.Model):
    """Open requests"""

    class Meta:
        verbose_name = 'open request'
        verbose_name_plural = 'open requests'
        db_table = 'openreqs'
        unique_together = ['req', 'client']
        # ordering = ['priority', 'clientid']

    # Feature request in question
    req = models.ForeignKey(FeatureReq, on_delete=models.CASCADE, verbose_name='Request', related_name='open_reqs')
    # Client attached
    client = models.ForeignKey(ClientInfo, on_delete=models.CASCADE, verbose_name='Client', related_name='open_reqs')
    # Client's priority (must be unique or null)
    priority = models.SmallIntegerField('Priority', unique=True, blank=True, null=True, default=None)
    # Target date (not strictly required)
    date_tgt = models.DateField('Target date', blank=True, null=True, default=None)
    # Open date/time
    opened_at = models.DateTimeField('Opened at', auto_now_add=True, db_index=True)
    # Opened by user (stored as username string instead of foreign key (for archival purposes))
    opened_by = models.CharField('Opened by', max_length=30, blank=False, editable=False)

    def __str__(self):
        return str(self.client) + ": " + str(self.req)


# Closed requests
class ClosedReq(models.Model):
    """Closed requests"""

    class Meta:
        verbose_name = 'closed request'
        verbose_name_plural = 'closed requests'
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
    req = models.ForeignKey(FeatureReq, on_delete=models.CASCADE, verbose_name='Request', related_name='closed_reqs')
    # Client attached
    client = models.ForeignKey(ClientInfo, on_delete=models.CASCADE, verbose_name='Client', related_name='closed_reqs')
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

    def __str__(self):
        return str(self.client) + ": " + str(self.req)


