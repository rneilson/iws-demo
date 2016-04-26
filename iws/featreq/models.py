import datetime, uuid
from collections import OrderedDict
from django.db import models, transaction
from django.db.models import F
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
        if prod_area not in AREA_BY_TEXT and prod_area not in AREA_BY_SHORT:
            raise ValueError('Invalid product area: {0}'.format(prod_area))

        # Gather args
        prodarea = prod_area if prod_area in AREA_BY_SHORT else AREA_BY_TEXT[prod_area]
        newargs = {
            'title': title,
            'desc': desc.strip(),
            'ref_url': ref_url,
            'prod_area': prodarea,
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

    def updatereq(self, user, desc='', title='', ref_url='', prod_area=''):
        # Check for required fields
        if not user:
            raise ValueError('User field required')
        # Ensure we're actually updating something
        # If not, return unchanged
        if not desc and not title and not ref_url and not prod_area:
            return self

        # Get current datetime
        dt = approxnow()
        dtstr = dt.strftime('%Y-%m-%d %H:%M:%S')
        padstr = '\n\n'
        upstr = ""

        # First append new product area change, if present
        if prod_area:
            # Convert to short form if req'd
            if prod_area in AREA_BY_TEXT:
                prod_area = AREA_BY_TEXT[prod_area]
            if prod_area in AREA_BY_SHORT:
                # Change product area and append change
                self.prod_area = prod_area
                upstr = upstr + padstr + '{0}, {1}:\n[Changed product area to "{2}"]'.format(
                    dtstr, user, AREA_BY_SHORT[prod_area])
            else:
                raise ValueError('Invalid product area: {0}'.format(prod_area))

        # Next append ref URL change, if present
        if ref_url:
            # Force string (just in case...)
            # TODO: validate URL format?
            if not isinstance(ref_url, str):
                raise TypeError('Invalid URL type: {0}'.format(type(ref_url)))
            # Change URL and append change
            self.ref_url = ref_url
            upstr = upstr + padstr + '{0}, {1}:\n[Changed reference URL to "{2}"]'.format(
                dtstr, user, ref_url)


        # Next append title change, if present
        if title:
            # Force string (just in case...)
            if not isinstance(title, str):
                raise TypeError('Invalid title type: {0}'.format(type(title)))
            # Change title and append change
            self.title = title
            upstr = upstr + padstr + '{0}, {1}:\n[Changed title to "{2}"]'.format(
                dtstr, user, title)

        # Now description addendum, if requested
        if desc:
            # Force string (just in case...)
            if not isinstance(desc, str):
                raise TypeError('Invalid description type: {0}'.format(type(desc)))
            # Add addendum [sic]
            # No padding, since we'd strip it anyways later
            upstr = upstr + padstr + '{0}, {1}:\n'.format(dtstr, user) + desc

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

    def updateclient(self, name='', con_name='', con_mail=''):
        '''Update existing ClientInfo.
        If con_name and/or con_mail are given as None, they will be cleared
        and replaced with the empty string.
        '''

        # Ensure we're actually updating something
        # If not, return unchanged
        if not name and not con_name and not con_mail:
            return self

        # Update fields with new info
        if name:
            # Force string (just in case...)
            if not isinstance(name, str):
                raise TypeError('Invalid name type: {0}'.format(type(name)))
            self.name = name

        if con_name:
            # Force string (just in case...)
            if not isinstance(con_name, str):
                raise TypeError('Invalid con_name type: {0}'.format(type(con_name)))
            self.con_name = con_name
        elif con_name is None:
            self.con_name = ''

        # Now description addendum, if requested
        if con_mail:
            # Force string (just in case...)
            if not isinstance(con_mail, str):
                raise TypeError('Invalid con_mail type: {0}'.format(type(con_mail)))
            self.con_mail = con_mail
        elif con_mail is None:
            self.con_mail = ''

        # Finally, update, validate, save, return
        self.full_clean()
        self.save()
        return self


## Request relations
# Normally we'd use an abstract base class here, and subclass for open/closed,
# but Django doesn't let us (easily) override constraints on inherited fields
# (in this case, we'd like a uniqueness constraint on priority while open, but
# remove it when closing), so instead we repeat ourselves (sadly).

# Open request manager
class OpenReqManager(models.Manager):
    """Model manager for OpenReq"""

    def shiftpri(self, client, priority):
        '''Checks if client has open requests >= priority, and shifts them
        up by one if so. New priority must be an integer in range 1 < x < 32766
        (inclusive). Existing entries with priority value 32767 will be changed
        to None/null.

        Returns True if records were shifted, False otherwise.
        '''
        # If priority is None (or 0), we don't have to do anything (null != null)
        if not priority:
            return False
        # If priority is not int or cannot be coerced to int, exception will
        # pass uncaught. If priority is out of range, ValueError will be raised.
        pr = int(priority)
        if pr <= 0 or pr > 32767:
            raise ValueError('Invalid priority: {0}'.format(priority))

        # Check if client valid (type, anyways), and get id
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

        # Start transaction, so all of this is (or should be) atomic
        with transaction.atomic():
            # Get everything matching client_id
            toshift = self.filter(client_id=client_id)
            # Check if any openreqs match client_id and priority
            if not toshift.filter(priority=pr).exists():
                # Nothing matches, good to go
                return False
            # Anything at SmallIntegerField max goes to None(/null)
            toshift.filter(priority=32767).update(priority=None)
            # Get everything >= priority and shift it up by one
            toshift.filter(priority__gte=pr).update(priority=F('priority')+1)

        # Aaand that should do it
        return True

    def updatereq(self, openreq, priority=False, date_tgt=False):
        '''Change priority and/or target date of given openreq.

        Param openreq can be an OpenReq instance, a primary key, or a dict with
        keys 'req_id' and 'client_id'.

        If priority is None or an integer in range 1 < x < 32766 (inclusive),
        it will be updated. If False (default), no update will be applied.

        If date_tgt is a datetime object or a string in the form
        '%Y-%m-%dT%H:%M:%S', and in the future, it will be updated. If False
        (default), no update will be applied.
        '''
        # Wrap it all in a transaction -- too many parts to be safe from race
        # conditions otherwise
        with transaction.atomic():
            # Check type of openreq and fetch if necessary
            if not isinstance(openreq, OpenReq):
                # Try int (primary key)
                if isinstance(openreq, int):
                    # Try getting OpenReq by id
                    openreq = self.get(id=openreq)
                # Try dict with req_id and client_id
                elif isinstance(openreq, dict) and 'req_id' in openreq and 'client_id' in openreq:
                    # Try getting OpenReq by ids (explicitly pulled from dict
                    # just in case something else weird is in there)
                    openreq = self.get(req_id=openreq['req_id'], client_id=openreq['client_id'])
                # Nope, nothing doing
                else:
                    raise ValueError('Invalid OpenReq identifier {0}'.format(openreq))

            # If we're not doing anything, return openreq unmodified
            if priority is False and date_tgt is False:
                return openreq

            # Only update priority if not False
            if priority is not False:
                # If priority is None or 0, we don't have to check/shift
                if priority is None or priority == 0:
                    openreq.priority = None
                # Otherwise, check/shift other priorities for this client, and *then* save
                elif priority != openreq.priority:
                    self.shiftpri(openreq.client_id, priority)
                    openreq.priority = priority

            # Only update date_tgt if not False
            if date_tgt is not False:
                # Ensure date_tgt is in the future
                openreq.date_tgt = checkdatetgt(date_tgt)

            # Now do the validate/save/return dance
            openreq.full_clean()
            openreq.save()
            return openreq

    def attachreq(self, user, client, request, priority=None, date_tgt=None):
        '''Attach feature request to client.

        Both client and request must already exist, and can either be given 
        directly as instance or fetched by id.
        Any ObjectDoesNotExist exceptions will be allowed to pass uncaught.

        priority must be None (default) or integer in range 1 < x < 32766 (inclusive).

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
        if priority:
            pr = int(priority)
            if pr < 0 or pr > 32766:
                raise ValueError('Priority out of range: {0}'.format(pr))
            elif pr == 0:
                pr = None
            newargs['priority'] = pr
            # Shift priorities if req'd
            self.shiftpri(client, pr)

        # Check date_tgt if given
        if date_tgt:
            newargs['date_tgt'] = checkdatetgt(date_tgt)

        # Create instance, validate fields, and save
        oreq = OpenReq(**newargs)
        oreq.full_clean()
        oreq.save()
        return oreq

    def newreq(self, user, client, priority=None, date_tgt=None, **newreq_args):
        '''Creates new feature request and attaches to given client, which
        can be given as ClientInfo object, UUID object, or UUID string.

        Params **newreq_args will be passed to FeatureReq.newreq(). Allowed
        fields are: title, desc, ref_url, prod_area, and id.

        Params priority and date_tgt will be passed to OpenReq.attachreq().

        Exceptions during any creation step will be passed uncaught.
        '''
        # First, make request
        fr = FeatureReq.objects.newreq(user, **newreq_args)
        # Next, attach to client
        oreq = self.attachreq(user, client, fr, priority, date_tgt)
        # Assume successful at this point (any exceptions will have already 
        # been raised by the above funcs)
        return oreq

# Open requests
class OpenReq(models.Model):
    """Open requests"""

    class Meta:
        verbose_name = 'open request'
        verbose_name_plural = 'open requests'
        db_table = 'openreqs'
        unique_together = ['client', 'req']
        index_together = ['client', 'priority']
        # ordering = ['priority', 'clientid']

    # Client attached
    client = models.ForeignKey(ClientInfo, on_delete=models.CASCADE, verbose_name='Client', related_name='open_list')
    # Feature request in question
    req = models.ForeignKey(FeatureReq, on_delete=models.CASCADE, verbose_name='Request', related_name='open_list')
    # Client's priority (must be unique or null (uniqueness not db constraint))
    priority = models.SmallIntegerField('Priority', blank=True, null=True, default=None)
    # Target date (not strictly required)
    date_tgt = models.DateTimeField('Target date', blank=True, null=True, default=None)
    # Open date/time
    opened_at = models.DateTimeField('Opened at', default=approxnow, editable=False, blank=True)
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

        # If request is already an OpenReq instance, things are simpler
        if isinstance(request, OpenReq):
            # Labelled plural, but all the transaction for loop will do
            # is call delete(), so we won't worry about it
            openreqs = request
            # Get values dict and save into list, as we would below with a QuerySet
            # when calling values()
            oreqlist = [ { k:getattr(request, k) for k in request.fields.keys() } ]
        # Otherwise, there are more hoops to jump through
        else:
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
                # Strip out primary key if present
                try:
                    del closeargs['id']
                except KeyError:
                    pass
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
        # unique_together = ['client', 'req']
        # ordering = ['closed_at']

    # Client attached
    client = models.ForeignKey(ClientInfo, on_delete=models.CASCADE, verbose_name='Client', related_name='closed_list')
    # Feature request in question
    req = models.ForeignKey(FeatureReq, on_delete=models.CASCADE, verbose_name='Request', related_name='closed_list')
    # Priority and target date at the point of closing (not unique, can be blank)
    priority = models.SmallIntegerField('Priority', blank=True, null=True, default=None)
    date_tgt = models.DateTimeField('Target date', blank=True, null=True, default=None)
    # Open details (taken from open request)
    opened_at = models.DateTimeField('Opened at', blank=False, editable=False)
    opened_by = models.CharField('Opened by', max_length=30, blank=False, editable=False)
    # Closed by user (stored as username string instead of foreign key (for archival purposes))
    closed_at = models.DateTimeField('Closed at', default=approxnow, editable=False, blank=True)
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

