import datetime, uuid
from collections import OrderedDict
from django.db import models, transaction
from django.core.exceptions import ObjectDoesNotExist
from .utils import *

## Module-level functions

# Product area types
AREA_CHOICES = (
    ('', 'Select area'),
    ('PO', 'Policies'),
    ('BI', 'Billing'),
    ('CL', 'Claims'),
    ('RE', 'Reports'),
)
AREA_BY_TEXT = { v:k for k,v in AREA_CHOICES if k }
AREA_BY_SHORT = { k:v for k,v in AREA_CHOICES if k }

def areabyshort(prod_area):
    '''Get full name of short product area identifier'''
    return AREA_BY_SHORT[prod_area]

def prodareas():
    '''List allowed product areas'''
    return AREA_BY_TEXT

# Closed status types
STATUS_CHOICES = (
    ('', 'Select status'),
    ('C', 'Complete'),
    ('R', 'Rejected'),
    ('D', 'Deferred')
)
STATUS_BY_SHORT = { k:v for k,v in STATUS_CHOICES if k }
STATUS_BY_TEXT = { v:k for k,v in STATUS_CHOICES if k }

def statusbyshort(status):
    '''Get full name of short closed status identifier'''
    return STATUS_BY_SHORT[status]


## Model and manager classes

# Feature request manager
class FeatReqManager(models.Manager):
    """Model manager for FeatureReq"""

    def newreq(self, user, title, desc, ref_url='', prod_area='Policies', id=None):
        '''Create new request'''
        # Check for required fields
        if not user:
            raise ValueError('User field required')
        if not title:
            raise ValueError('Title field required')
        if not desc:
            raise ValueError('Description field required')
        if prodarea not in AREA_BY_TEXT and prodarea not in AREA_BY_SHORT:
            raise ValueError('Invalid product area: {0}'.format(prodarea))

        # Gather args
        prod_area = prodarea if prodarea in AREA_BY_SHORT else AREA_BY_TEXT[prodarea]
        newargs = {
            'title': title,
            'desc': desc.strip(),
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
        dt = approxnow()
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
    date_cr = models.DateTimeField('Created at', default=approxnow, editable=False, blank=True, db_index=True)
    # Date/time last updated
    # TODO: change back to auto_now=True, or let the view(s) force it?
    date_up = models.DateTimeField('Updated at', default=approxnow, editable=False, blank=True)

    # User relations
    # Stores username as string instead of foreign key
    # This means deleted users don't affect db integrity (and keeps joins down)

    # Username of request creator
    user_cr = models.CharField('Created by', max_length=30, blank=False, editable=False)
    # Username of latest updater
    user_up = models.CharField('Updated by', max_length=30, blank=False, editable=False)

    objects = FeatReqManager()

    # Fields to serialize, in order, with callable JSON translators if required
    # fieldlist = ('id', 'title', 'desc', 'ref_url', 'prod_area', 'date_cr', 'user_cr', 'date_up', 'user_up')
    fields = OrderedDict([
        ('id', str), ('title', None), ('desc', None), ('ref_url', None), ('prod_area', areabyshort),
        ('date_cr', approxdatefmt), ('user_cr', None), ('date_up', approxdatefmt), ('user_up', None)
    ])

    # Will call tojsondict() with self
    jsondict = tojsondict

    def __str__(self):
        return str(self.title)

    def updatereq(self, user, addtodesc='', newtitle='', newprodarea=''):
        # Check for required fields
        if not user:
            raise ValueError('User field required')
        # Ensure we're actually updating something
        # If not, return unchanged
        if not addtodesc and not newtitle and not newprodarea:
            return self

        # Get current datetime
        padstr = '\n\n'
        dt = approxnow()
        dtstr = dt.strftime('%Y-%m-%d %H:%M:%S')
        upstr = ""

        # First append new product area change, if present
        if newprodarea:
            # Convert to short form if req'd
            if newprodarea in AREA_BY_TEXT:
                newprodarea = AREA_BY_TEXT[newprodarea]
            if newprodarea in AREA_BY_SHORT:
                # Change product area and append change
                self.prod_area = newprodarea
                upstr = upstr + padstr + '{0}, {1}:\n[Changed product area to "{2}"]'.format(
                    dtstr, user, newprodarea)
            else:
                raise ValueError('Invalid product area: {0}'.format(newprodarea))

        # Next append title change, if present
        if newtitle:
            # Force string (just in case...)
            if not isinstance(newtitle, str):
                raise TypeError('Invalid title type: {0}'.format(type(newtitle)))
            # Change title and append change
            self.title = newtitle
            upstr = upstr + padstr + '{0}, {1}:\n[Changed title to "{2}"]'.format(
                dtstr, user, newtitle)

        # Now description addendum, if requested
        if addtodesc:
            # Force string (just in case...)
            if not isinstance(addtodesc, str):
                raise TypeError('Invalid description type: {0}'.format(type(addtodesc)))
            # Add addendum [sic]
            # No padding, since we'd strip it anyways later
            upstr = upstr + padstr + '{0}, {1}:\n'.format(dtstr, user) + addtodesc

        # Update description
        self.desc = self.desc.rstrip() + upstr

        # Change update user/time
        self.date_up = dt
        self.user_up = user

        # Finally, update, validate, save, return
        self.full_clean()
        self.save()
        return self


# Client manager
class ClientManager(models.Manager):
    """Model manager for ClientInfo"""

    def newclient(self, name, con_name='', con_mail='', id=None):
        '''Create new client'''
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

        # Get datetime (without microseconds)
        newargs['date_add'] = approxnow()

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
    date_add = models.DateTimeField('Date added', default=approxnow, editable=False, blank=True)

    # Open/closed request lists
    openreqs = models.ManyToManyField(FeatureReq, related_name='openclients', through='OpenReq')
    closedreqs = models.ManyToManyField(FeatureReq, related_name='closedclients', through='ClosedReq')

    objects = ClientManager()

    # Fields to serialize, in order, with callable JSON translators if required
    # fieldlist = ('id', 'name', 'con_name', 'con_mail', 'date_add')
    fields = OrderedDict([
        ('id', str), ('name', None), ('con_name', None), ('con_mail', None), ('date_add', approxdatefmt)
    ])

    # Will call tojsondict() with self
    jsondict = tojsondict

    def __str__(self):
        return str(self.name)


## Request relations
# Normally we'd use an abstract base class here, and subclass for open/closed,
# but Django doesn't let us (easily) override constraints on inherited fields
# (in this case, we'd like a uniqueness constraint on priority while open, but
# remove it when closing), so instead we repeat ourselves (sadly).

# Open request manager
class OpenReqManager(models.Manager):
    """Model manager for OpenReq"""

    def attachreq(self, user, request, client, priority=None, date_tgt=None):
        '''Attach feature request to client.

        Both request and client must already exist, and can either be given 
        directly as instance or fetched by id.
        Any ObjectDoesNotExist exceptions will be allowed to pass uncaught.

        priority must be None (default) or integer in range 1 < x < 32767 (inclusive).

        date_tgt can be a specific datetime object, a timedelta object, or 
        a datetime string in the format '%Y-%m-%dT%H:%M:%S'. Invalid datetimes
        will raise ValueError.
        '''
        # Ensure username supplied
        if not user:
            raise ValueError('User required')

        # Get current datetime, shave off subseconds
        dnow = approxnow()

        # Gather args
        # date_tgt defaults to None (possibly overridden in later section)
        newargs = {
            'opened_at': dnow,
            'opened_by': user
        }

        # Check if client is already ClientInfo instance, use as id if not
        if isinstance(client, ClientInfo):
            newargs['client'] = client
        elif isinstance(client, uuid.UUID):
            newargs['client_id'] = client
        elif isinstance(client, str):
            uid = validuuid(client)
            if uid:
                newargs['client_id'] = uid
            else:
                raise ValueError('Invalid client_id: {0}'.format(client))
        else:
            raise TypeError('Invalid client_id type: {0}'.format(type(client)))

        # Check if request is already FeatureReq instance, use as id if not
        if isinstance(request, FeatureReq):
            newargs['req'] = request
        elif isinstance(request, uuid.UUID):
            newargs['req_id'] = request
        elif isinstance(request, str):
            uid = validuuid(request)
            if uid:
                newargs['req_id'] = uid
            else:
                raise ValueError('Invalid req_id: {0}'.format(request))
        else:
            raise TypeError('Invalid req_id type: {0}'.format(type(request)))

        # Check priority (TypeError during int coercion will pass uncaught)
        if priority is not None:
            pr = int(priority)
            if pr <= 0 or pr > 32767:
                raise ValueError('Invalid priority: {0}'.format(pr))
            newargs['priority'] = pr

        # Check date_tgt if given
        if date_tgt:
            newargs['date_tgt'] = checkdatetgt(date_tgt)

        # Create instance, validate fields, and save
        oreq = OpenReq(**newargs)
        oreq.full_clean()
        oreq.save()
        return oreq

# Open requests
class OpenReq(models.Model):
    """Open requests"""

    class Meta:
        verbose_name = 'open request'
        verbose_name_plural = 'open requests'
        db_table = 'openreqs'
        unique_together = ['req', 'client']
        # ordering = ['priority', 'clientid']

    # Client attached
    client = models.ForeignKey(ClientInfo, on_delete=models.CASCADE, verbose_name='Client', related_name='openlist')
    # Feature request in question
    req = models.ForeignKey(FeatureReq, on_delete=models.CASCADE, verbose_name='Request', related_name='openlist')
    # Client's priority (must be unique or null)
    priority = models.SmallIntegerField('Priority', unique=True, blank=True, null=True, default=None)
    # Target date (not strictly required)
    date_tgt = models.DateTimeField('Target date', blank=True, null=True, default=None)
    # Open date/time
    opened_at = models.DateTimeField('Opened at', default=approxnow, editable=False, blank=True, db_index=True)
    # Opened by user (stored as username string instead of foreign key (for archival purposes))
    opened_by = models.CharField('Opened by', max_length=30, blank=False, editable=False)

    objects = OpenReqManager()

    fields = OrderedDict([
        ('client_id', str), ('req_id', str), ('priority', None),
        ('date_tgt', approxdatefmt), ('opened_at', approxdatefmt), ('opened_by', None)
    ])

    # Will call tojsondict() with self
    jsondict = tojsondict

    def __str__(self):
        return str(self.client) + ": " + str(self.req)

# Closed request manager
class ClosedReqManager(models.Manager):
    """Model manager for ClosedReq"""

    def closereq(self, user, request, status='C', reason='Request completed', client=None):
        '''Creates ClosedReq entry (or entries) from existing OpenReq(s) and 
        removes said OpenReq(s).'''

        # Ensure username supplied
        if not user:
            raise ValueError('User required')

        # Normalize status to short form
        if status in STATUS_BY_SHORT:
            use_status = status
        else:
            use_status = STATUS_BY_TEXT.get(status, None)
            if not use_status:
                raise ValueError('Invalid status: {0}'.format(status))

        # Ensure reason is non-empty string
        if not reason or not isinstance(reason, str):
            raise ValueError('Invalid reason: {0}'.format(reason))

        # Get current datetime, shave off subseconds
        dnow = approxnow()

        # Gather args
        newargs = {
            'closed_at': dnow,
            'closed_by': user,
            'status': use_status,
            'reason': reason,
        }

        # Get request id (we only need the id, really)
        if isinstance(request, FeatureReq):
            req_id = request.id
        elif isinstance(request, uuid.UUID):
            req_id = request
        elif isinstance(request, str):
            uid = validuuid(request)
            if uid:
                req_id = uid
            else:
                raise ValueError('Invalid req_id: {0}'.format(request))
        else:
            raise TypeError('Invalid req_id type: {0}'.format(type(request)))

        # Get QuerySet matching req_id
        openreqs = OpenReq.objects.filter(req_id=req_id)

        # Check if client given, get id
        if client:
            if isinstance(client, ClientInfo):
                client_id = client.id
            elif isinstance(client, uuid.UUID):
                client_id = client
            elif isinstance(client, str):
                uid = validuuid(client)
                if uid:
                    client_id = uid
                else:
                    raise ValueError('Invalid client_id: {0}'.format(client))
            else:
                raise TypeError('Invalid client_id type: {0}'.format(type(client)))
            # Now further filter query
            openreqs = openreqs.filter(client_id=client_id)

        # We use values() since we're just going to be populating (a copy of)
        # the newargs dict later anyways.
        # We raise an exception if query is empty, since you can't close
        # something that isn't open...
        oreqlist = openreqs.values()
        if len(oreqlist) == 0:
            if client_id:
                raise ObjectDoesNotExist('No open req_id {0} for client_id {1}'.format(
                    req_id, client_id))
            else:
                raise ObjectDoesNotExist('No open req_id {0}'.format(req_id))

        # Now the big loop: we create closed versions of each open request, 
        # then delete the open versions.
        # Everything gets wrapped in a transaction, since we're doing a whole
        # bunch of changes at once, and we want them to succeed or fail 
        # together.
        with transaction.atomic():
            tocreate = []
            # Build new ClosedReq(s)
            for oreq in oreqlist:
                # Copy of newargs
                closeargs = newargs.copy()
                # Add in OpenReq values (this will add req_id and client_id)
                closeargs.update(oreq)
                # Strip out primary key
                del closeargs['id']
                # Create new ClosedReq instance and validate (will bulk create)
                creq = ClosedReq(**closeargs)
                creq.full_clean()
                tocreate.append(creq)
            # Insert them all at once
            ClosedReq.objects.bulk_create(tocreate)
            # Now delete the OpenReq(s)
            openreqs.delete()

        # And we're done!
        return True

# Closed requests
class ClosedReq(models.Model):
    """Closed requests"""

    class Meta:
        verbose_name = 'closed request'
        verbose_name_plural = 'closed requests'
        db_table = 'closedreqs'
        unique_together = ['req', 'client']
        # ordering = ['closed_at']

    # Client attached
    client = models.ForeignKey(ClientInfo, on_delete=models.CASCADE, verbose_name='Client', related_name='closedlist')
    # Feature request in question
    req = models.ForeignKey(FeatureReq, on_delete=models.CASCADE, verbose_name='Request', related_name='closedlist')
    # Priority and target date at the point of closing (not unique, can be blank)
    priority = models.SmallIntegerField('Priority', blank=True, null=True, default=None)
    date_tgt = models.DateTimeField('Target date', blank=True, null=True, default=None)
    # Open details (taken from open request)
    opened_at = models.DateTimeField('Opened at', blank=False, editable=False)
    opened_by = models.CharField('Opened by', max_length=30, blank=False, editable=False)
    # Closed by user (stored as username string instead of foreign key (for archival purposes))
    closed_at = models.DateTimeField('Closed at', default=approxnow, editable=False, blank=True, db_index=True)
    closed_by = models.CharField('Closed by', max_length=30, blank=False, editable=False)
    # Closed status
    status = models.CharField('Closed as', max_length=1, default='C', choices=STATUS_CHOICES)
    reason = models.CharField('Details', max_length=128, blank=True, default='')

    objects = ClosedReqManager()

    fields = OrderedDict([
        ('client_id', str), ('req_id', str), ('priority', None),
        ('date_tgt', approxdatefmt), ('opened_at', approxdatefmt), ('opened_by', None),
        ('closed_at', approxdatefmt), ('closed_by', None),
        ('status', statusbyshort), ('reason', None)
    ])

    # Will call tojsondict() with self
    jsondict = tojsondict

    def __str__(self):
        return str(self.client) + ": " + str(self.req)

