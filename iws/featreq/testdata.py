from featreq.models import *
import random, datetime, time

def buildtestdata():
    # Templates
    titlestr = 'Test {0}{1}'
    descstr = 'Test feature request, number {0}{1}'
    urlstr = 'http://test{0}{1}.com'
    areas = [ v for v in prodareas().keys() ]
    basedt = datetime.datetime.now(datetime.timezone.utc).replace(
        hour=12, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)

    # Create test requests
    for x in 'AB':
        cl = ClientInfo.objects.get(name='Client {0}'.format(x))
        for y in range(1, 7):
            dtgt = basedt + datetime.timedelta(days=y)
            reqargs = {}
            reqargs['title'] = titlestr.format(x, y)
            reqargs['desc'] = descstr.format(x, y)
            reqargs['ref_url'] = urlstr.format(x.lower(), y)
            reqargs['prod_area'] = areas[random.randint(0, len(areas)-1)]
            OpenReq.objects.newreq('rn', cl, 1, dtgt, **reqargs)
            time.sleep(1.0)

