#!/usr/bin/env python3

import os, sys, errno, getpass, random, string

BASEPATH = os.path.dirname(os.path.abspath(__file__))
SECRET_KEY_FILENAME = 'secretkey.txt'
SESSION_DIRNAME = 'tmp'
SETTINGS_FILENAME = 'iws/settings.py'

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
        dirname = settings.SESSION_FILE_PATH

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
        password = getpass.getpass()
        # Create superuser in backend
        management.call_command('createsuperuser', username=username, email=emailaddr)
        # Set password and save
        user = User.objects.get(username=username)
        user.set_password(password)
        user.save()
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

if __name__ == "__main__":
    # TODO: cmdline args
    # TODO: command-line option for username
    # parser = argparse.ArgumentParser(description='Initial setup of iws-demo application')
    # args = parser.parse_args()

    # Django environment setup
    # sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iws.settings')
    import django
    django.setup()

    initdatabase()
    appendallowedhosts()
    makesuperuser()
    makesessiondir()
    makesecretkey()
    initstatic()

    sys.stdout.write('Setup complete.\n')
