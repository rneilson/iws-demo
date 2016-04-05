import datetime, uuid
from collections import OrderedDict

## Utility functions used in various places

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
DATETIMEFMT = '%Y-%m-%dT%H:%M:%S'
DATEONLYFMT = '%Y-%m-%d'

def approxnow():
    '''Returns present datetime without microseconds'''
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)

def approxnowfmt():
    '''Returns present datetime without microseconds as string,
    formatted as '%Y-%m-%dT%H:%M:%S''
    '''
    return approxnow().strftime(DATETIMEFMT)

def approxdatefmt(date_val):
    '''Returns date_val without microseconds as string,
    formatted as '%Y-%m-%dT%H:%M:%S'.
    Returns None if date_val is not a datetime instance.
    '''
    if isinstance(date_val, datetime.datetime):
        return date_val.strftime(DATETIMEFMT)
    else:
        return None

def checkdatetgt(date_tgt):
    '''Checks if date_tgt is in the future.

    Returns datetime object if date_tgt is given and valid, or None if 
    date_tgt is None (or any other value evaluating to False).

    date_tgt can be a specific datetime object, a timedelta object, or 
    a datetime string in the format '%Y-%m-%dT%H:%M:%S' or '%Y-%m-%d'.
    Invalid datetimes will raise ValueError. Types other than the above
    will raise TypeError.
    '''
    # Get current datetime, shave off subseconds
    dnow = approxnow()

    # We handle by type (ugly-ish, yes) because there isn't really
    # another good, clean way to do it
    if date_tgt:
        if isinstance(date_tgt, datetime.datetime):
            # Ensure target in future
            if date_tgt < dnow:
                raise ValueError('Target date {0} earlier than present'.format(date_tgt.strftime(DATETIMEFMT)))
            else:
                return date_tgt
        elif isinstance(date_tgt, datetime.timedelta):
            # Add to current datetime
            return dnow + date_tgt
        elif isinstance(date_tgt, str):
            # Create datetime from string and make UTC
            # First try full date/time
            try:
                dt = datetime.datetime.strptime(date_tgt, DATETIMEFMT).replace(tzinfo=datetime.timezone.utc)
            except ValueError:
                # Next try short date-only format
                try:
                    dt = datetime.datetime.strptime(date_tgt, DATEONLYFMT).replace(tzinfo=datetime.timezone.utc)
                except ValueError:
                    raise ValueError('Invalid date string: {0}'.format(date_tgt))
            return dt
        else:
            raise TypeError('Invalid date_tgt type: {0}'.format(type(date_tgt)))
    else:
        return None

# JSON-compatible OrderedDict creation
def tojsondict(model, fields=None, fcalls=None):
    '''Returns JSON-compatible dict of model values.
    Uses OrderedDict to ensure values in model-specified order.

    If neither of fields or fcalls are specified, the model 
    class must have a fields attribute as an OrderedDict
    of field names and callables for JSON compatibility.

    If fields is specified, it must be an iterable of valid field
    names of the model.

    If fcalls is specified, it must be an iterable matching
    fields, with each item a callable object or None.
    '''

    retvals = OrderedDict()

    # Get fields dict if necessary
    # (Checked because there might be times when model is 
    # something weird, without the proper fields attribute, 
    # and we don't want AttributeError when we don't need it)
    if not fields or not fcalls:
        fielddict = model.fields
        if not fields:
            fields = fielddict.keys()
        if not fcalls:
            fcalls = tuple(fielddict[k] for k in fields)

    # Iterate over selected fields in given order, and translate
    for fname, fcall in zip(fields, fcalls):
        fval = getattr(model, fname)
        if fcall is not None:
            retvals[fname] = fcall(fval)
        else:
            retvals[fname] = fval

    return retvals

def qset_vals_tojsonlist(qset, fields=None, fcalls=None):
    '''Takes a QuerySet qset and an optional list of fields to
    convert to a JSON-compatible list of OrderedDicts. Avoids
    overhead of model instantiation by using values_list() as
    an intermediate reprsentation.

    If neither of fields or fcalls are specified, the base model 
    class of qset must have a fields attribute as an OrderedDict
    of field names and callables for JSON compatibility.

    If fields is specified, it must be an iterable of valid field
    names of the QuerySet (which can include aggregates).

    If fcalls is specified, it must be an iterable matching
    fields, with each item a callable object or None.
    '''
    # Get fields dict if necessary
    # (Checked because there might be times when qset is something
    # weird, not linked to the proper model)
    if not fields or not fcalls:
        fielddict = qset.model.fields
        # Use field list if provided, otherwise get from fielddict
        # (as we want to ensure field order) and make tuple of 
        # matching callables (instead of repeated dict lookups) if
        # not passed in
        if not fields:
            fields = tuple(fielddict)
        if not fcalls:
            fcalls = tuple(fielddict[k] for k in fields)
    # BIG LIST COMPREHENSION ONE-LINER
    # (For each values_list() item, we make an OrderedDict of the 
    # field names and field values, using the callable translator
    # if it exists)
    return [ OrderedDict([ (fn, fc(fv)) if fc is not None else (fn, fv) 
        for fn, fc, fv in zip(fields, fcalls, fvals)]) 
            for fvals in qset.values_list(*fields) ]


