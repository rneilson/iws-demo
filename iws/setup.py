#!/usr/bin/env python3

import os, sys, errno, random, string, argparse

BASEPATH = os.path.dirname(os.path.abspath(__file__))
SECRET_KEY_FILENAME = 'secretkey.txt'
SESSION_DIRNAME = 'tmp'
SETTINGS_FILENAME = 'iws/settings.py'

ROOTPATH = os.path.dirname(BASEPATH)
UWSGI_SAMPLE_FILENAME = 'uwsgi/example_uwsgi.ini'
UWSGI_DEST_FILENAME = 'iws_uwsgi.ini'
UWSGI_LOG_FILENAME = 'log/iws.log'

def makesecretkey(filename=None):
    # Default to current dir
    if not filename:
        filename = os.path.join(BASEPATH, SECRET_KEY_FILENAME)

    # Attempt exclusive open of file for writing
    # Do nothing if file exists
    try:
        f = open(filename, 'x')
    except FileExistsError as e:
        sys.stdout.write('Secret key file {0} already exists, skipping creation\n'.format(filename))
    except Exception as e:
        # Something else happened, re-raise
        raise
    else:
        sys.stdout.write('Generating secret key and writing to {0}...'.format(filename))

        # Generate secret
        charset = '{}{}{}'.format(string.ascii_letters, string.digits, string.punctuation)
        secretkey = ''.join([random.SystemRandom().choice(charset) for x in range(64)])

        # Write to file and close
        f.write(secretkey)
        f.close()

        sys.stdout.write('done!\n')
    finally:
        sys.stdout.flush()

def makesessiondir(dirname=None):
    from django.conf import settings

    # Default to current dir
    if not dirname:
        dirname = os.path.join(BASEPATH, SESSION_DIRNAME)

    # Attempt mkdir, do nothing if already exists
    try:
        os.mkdir(dirname)
    except OSError:
        sys.stdout.write('Session dir {0} already exists, skipping creation\n'.format(dirname))
    except Exception as e:
        # Something else happened, re-raise
        raise
    else:
        sys.stdout.write('Created session dir {0}\n'.format(dirname))
    finally:
        sys.stdout.flush()

def makesuperuser(username='iws-admin'):
    from django.contrib.auth.models import User
    from django.core.exceptions import ObjectDoesNotExist
    from django.core import management

    # Check if user exists
    try:
        user = User.objects.get(username=username)
    except ObjectDoesNotExist:
        sys.stdout.write('Creating superuser {0}...\n'.format(username))
        # Get email and password
        sys.stdout.write('Email address: ')
        sys.stdout.flush()
        emailaddr = sys.stdin.readline().strip()
        # Create superuser in backend
        management.call_command('createsuperuser', username=username, email=emailaddr)
        sys.stdout.write('Created superuser {0}\n'.format(username))
    else:
        if not user.is_superuser:
            sys.stdout.write('Converting user {0} to superuser...\n'.format(username))
            user.is_staff = True
            user.is_superuser = True
            user.save()
        else:
            sys.stdout.write('Superuser {0} already exists, skipping creation\n'.format(username))
    finally:
        sys.stdout.flush()

def appendallowedhosts(filename=None):
    from django.conf import settings

    # Default
    if not filename:
        filename = os.path.join(BASEPATH, SETTINGS_FILENAME)

    # Check environment for ALLOWED_HOSTS
    if settings.ALLOWED_HOSTS:
        sys.stdout.write('Allowed hosts: {0}\n'.format(', '.join(settings.ALLOWED_HOSTS)))
    else:
        sys.stdout.write('No allowed hosts found\n')
        fqdnstr = ''
        # Get fqdns
        while not fqdnstr:
            sys.stdout.write('Please enter fully-qualifed domain names, separated by commas:\n')
            sys.stdout.flush()
            fqdnstr = sys.stdin.readline().strip()

        # Parse fqdn list and write to settings.py
        fqdnlist = [ "'{0}'".format(dn.strip()) for dn in fqdnstr.split(',') ]
        with open(filename, 'a') as f:
            f.write('\nALLOWED_HOSTS = [ {0} ]\n'.format(', '.join(fqdnlist)))

        sys.stdout.write('Appended new ALLOWED_HOSTS to {0}\n'.format(filename))
    
    sys.stdout.flush()

def initdatabase():
    from django.core import management

    # Just run migrate command straight-up
    management.call_command('migrate')

def initstatic():
    from django.core import management

    sys.stdout.write('Collecting static files...\n')
    sys.stdout.flush()

    # Just run collectstatic command straight-up
    management.call_command('collectstatic', verbosity=0, noinput=True)

def uwsgiconfig():
    # Copy example config into actual config
    samplefilename = os.path.join(ROOTPATH, UWSGI_SAMPLE_FILENAME)
    try:
        f = open(samplefilename, 'r')
    except OSError as e:
        sys.stdout.write("Couldn't open uWSGI example file at {0}, error: {1}\n".format(samplefilename, str(e)))
    else:
        # Get sample config and pad string
        sampleconfig = f.read()
        f.close()
        sampleconfig += '\n\n'

        # Open actual config
        destfilename = os.path.join(ROOTPATH, UWSGI_DEST_FILENAME)
        try:
            f = open(destfilename, 'w')
        except OSError as e:
            sys.stdout.write("Couldn't write uWSGI config file at {0}, error: {1}\n".format(destfilename, str(e)))
        else:
            f.write(sampleconfig)

            # Detect currently-used virtualenv
            try:
                venvpath = os.environ['VIRTUAL_ENV']
            except KeyError:
                venvpath = None

            sys.stdout.write('Python virtualenv path (leave blank for {0}): '.format(str(venvpath)))
            sys.stdout.flush()
            usepath = sys.stdin.readline().strip()
            if not usepath:
                usepath = venvpath

            if usepath:
                f.write('home = {0}\n'.format(usepath))

            # Close config file
            f.close()

            # Create empty log dir and file
            logfilename = os.path.join(ROOTPATH, UWSGI_LOG_FILENAME)
            logdir = os.path.dirname(logfilename)
            os.makedirs(logdir, exist_ok=True)
            try:
                f = open(logfilename, 'x')
            except FileExistsError:
                sys.stdout.write("Log file at {0} already exists, skipping creation\n".format(logfilename))
            except OSError as e:
                sys.stdout.write("Couldn't create uWSGI log file at {0}, error: {1}\n".format(logfilename, str(e)))
            else:
                f.close()
                sys.stdout.write("Created log file at {0}\n".format(logfilename))
            finally:
                sys.stdout.flush()

if __name__ == "__main__":
    # Command line args
    # TODO: command-line option for username
    parser = argparse.ArgumentParser(description='Initial setup of iws-demo application')
    parser.add_argument('-u', '--uwsgi-config', action='store_true', dest='uwsgi',
        help='create uwsgi log file and virtualenv pointer')
    args = parser.parse_args()

    # First create session/secret locations
    makesessiondir()
    makesecretkey()

    # Django environment setup
    # sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iws.settings')
    import django
    django.setup()

    initdatabase()
    appendallowedhosts()
    makesuperuser()
    initstatic()

    # Optional uWSGI config helpers
    if args.uwsgi:
        uwsgiconfig()

    sys.stdout.write('Setup complete.\n')
