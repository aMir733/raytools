import jdatetime # pip3 install jdatetime
from subprocess import run as subrun
from uuid import uuid4, UUID
from re import compile as recompile

def issystemd():
    if subrun(['command', '-v', 'systemctl']).returncode != 0:
        return None
    return True

def issystemd_remote(servers): # ['root@1.1.1.1', 'root@2.2.2.2']
    codes = []
    for server in servers:
        codes.append(subrun(['ssh', server, '--', 'command', '-v', 'systemctl']).returncode)
    return codes

def cp(*args):
    if len(args) < 2:
        raise Exception("Not enough arguments")
    subrun(('cp', '--') + args, check=True)

def cp_remote(
        path, # Path to the local file
        servers, # ["root@1.1.1.1:/tmp/boo", "root@2.2.2.2:/tmp/foo"]
        ):
    codes = []
    for server in servers:
        codes.append(subrun(['scp', '--', path, server]).returncode)
    return codes

def restart(service="v2ray@raytools"):
    subrun(['systemctl', 'restart', '--', service], check=True)

def restart_remote(
        servers, # ["root@1.1.1.1", "root@2.2.2.2"] OR [("root@1.1.1.1", "xray@bridge"), "root@2.2.2.2"]
        service=None,
        ):
    sc = None
    codes = []
    for server in servers:
        if type(server) != str:
            name = server[0]
            sc = server[1]
        else:
            name = server
            sc = service if service else "v2ray@raytools"
        codes.append(subrun(['ssh', name, '--', 'systemctl', 'restart', '--', sc]).returncode)
    return codes

def make_uuid():
    return str(uuid4())

def isuuid(uuid):
    try:
        UUID(uuid)
    except ValueError:
        return False
    return True

def timenow():
    return jdatetime.datetime.now(tz=ZoneInfo("Asia/Tehran")).replace(microsecond=0)

def timemake(date):
    return jdatetime.datetime(*[int(i) for i in date])

def timedelta(date, days): # Increment/Decrement days in timestamp
    return date + days * 86400

def strtotime(date): # Converts standard ISO8601 string to datetime object
    if not isinstance(date, str):
        raise TypeError("Invalid type")
    if "T" in date:
        date= date.split("T")[0]
    if not recompile(r"(\d{4})-(\d{2})-(\d{2})").match(date):
        raise ValueError(f"Invalid isoformat string: {date}")
    y, m, d = list(map(int, date.split('-')))
    return jdatetime.date(y, m, d)

def timetostr(date): # Converts datetime object to standard ISO8601 string ("YYYY-MM-DD HH:MM:SS.SSS")
    if not isinstance(date, jdatetime.datetime):
        raise TypeError("Invalid type")
    return date.isoformat().split("T")[0]

def stamptotime(date): # Converts timestamp to a datetime object
    return jdatetime.datetime.fromtimestamp(date)

def timetostamp(date): # Converts datetime object to timestamp
    return int(date.timestamp())
