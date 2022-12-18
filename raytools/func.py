from jdatetime import datetime, date as jdate # pip3 install jdatetime
from zoneinfo import ZoneInfo
from subprocess import run as subrun, PIPE
from uuid import uuid4, UUID
from re import compile as recompile
from json import load as jsonload, loads as jsonloads, dumps as jsondumps
import io
import os
import time
from base64 import b64encode, b64decode
import queue, threading
import logging

log = logging.getLogger(__name__)

def locks_aq(locks):
    return [lock.acquire() for lock in locks]

def locks_re(locks):
    return [lock.release() for lock in locks]

def tail(f): # http://www.dabeaz.com/generators/
    f.seek(0, 2)
    while True:
        line = f.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line
       
def tail_F(some_file): # https://stackoverflow.com/a/12523119
    first_call = True
    while True:
        try:
            with open(some_file) as infile:
                if first_call:
                    infile.seek(0, 2)
                    first_call = False
                latest_data = infile.read()
                while True:
                    if '\n' not in latest_data:
                        latest_data += infile.read()
                        if '\n' not in latest_data:
                            yield ''
                            if not os.path.isfile(some_file):
                                break
                            continue
                    latest_lines = latest_data.split('\n')
                    if latest_data[-1] != '\n':
                        latest_data = latest_lines[-1]
                    else:
                        latest_data = infile.read()
                    for line in latest_lines[:-1]:
                        yield line + '\n'
        except IOError:
            yield ''

def log_parseline(line):
    try:
        ip, mode, user = [line.strip().split(' ')[i] for i in [2, 3, 6]]
    except (KeyError, ValueError):
        return
    if ip == "127.0.0.1":
        return
    if mode != "accepted":
        return
    ip = ip.split(":")
    return (user, ip[1] if len(ip) == 3 else ip[0])

def counter(users):
    for user, ips in users.items():
        log.debug("processing {} with {}".format(user, ' '.join(ips)))
        count, id = user.split("@")
        if len(ips) <= int(count):
            continue
        yield id

def anytojson(inp):
    if isinstance(inp, bytes):
        inp = inp.decode()
    if isinstance(inp, str):
        try:
            return jsonloads(inp)
        except:
            with open(inp, "r") as f:
                return jsonload(f)
    if isopenedfile(inp):
        return jsonload(inp)
    if not isinstance(inp, dict):
        raise TypeError("Invalid Type")
    return inp

def parsecfg(cfg):
    cfg = anytojson(cfg)
    valid, reason = isvalidcfg(cfg)
    if not valid:
        raise ValueError(reason)
    return cfg

def getinbounds(
    cfg,
    clients,
    ):
    if 'inbound' in cfg:
        cfg['inbounds'] = [cfg.pop("inbound")]
    inbounds, passed = ([], None)
    for index, inbound in enumerate(cfg['inbounds']):
        if not 'tag' in inbound:
            raise KeyError(f"No tag was found in {index}th inbound. Please add a tag to all of your inbounds before continuing")
        if inbound['tag'] == 'api':
            api_port = inbound['port']
            continue
        if not 'protocol' in inbound or inbound['protocol'] != 'vmess' and inbound['protocol'] != 'vless':
            inbounds.append(inbound)
            continue
        try:
            default_client = inbound['settings']['clients'][0]
        except (IndexError, KeyError):
            inbounds.append(inbound)
            continue
        if default_client['email'] != "raytools":
            inbounds.append(inbound)
            continue
        passed = True
        if not 'level' in default_client or default_client['level'] != 0:
            raise KeyError("Please add a 'level' entry of 0 to your default user")
        inbounds.append(populateinb(inbound, clients, default_client))
    if not passed:
        raise ValueError("Could not find an appropriate inbound to use")
    return (inbounds, api_port)

def populateinb(
    inb,
    clients,
    client_defaults={},
    ):
    max_digits = len(str(max(clients)[0])) if clients else 1
    for client in clients:
        inb['settings']['clients'].append({
            **client_defaults,
            "id": client[2],
            "email": "{}@{}".format(client[1], str(client[0]).zfill(max_digits))
        })
    return inb

def writelink(
        protocol,
        link, # {} OR "{}"
        ):
    if isinstance(link, dict):
        link = jsondumps(link, separators=(',', ':'))
    if not isinstance(link, str):
        raise TypeError("Invalid Type")
    if protocol != "vmess" and protocol != "vless":
        raise ValueError("Null or Invalid Protocol")
    return "{}://{}".format(
            protocol,
            b64encode(link.encode()).decode() if protocol == "vmess" else link,
            )

def readlink(
        link,
        ):
    matched = matchlink(link)
    return (
            matched[0],
            b64decode(matched[1]).decode() if matched[0] == "vmess" else matched[1]
            )

def formatlink(
        link,
        **kwargs,
        ):
    if not isinstance(link, str):
        raise TypeError("Invalid Type")
    protocol, link = readlink(link)
    for key, value in kwargs.items():
        if not isinstance(value, str):
            value = str(value)
        if not isjsonsafe(value):
            raise Exception("Value contains an illegal character: " + value)
        link = link.replace("^{}^".format(key.upper()), value)
    return writelink(protocol, link)

def inbtolink(
        inb,
        ): # Based on the documention found in www.v2ray.com
    link = {
            "port": "",
            "net": "",
            "host": "",
            "path": "",
            "sni": "",
            "tls": "",
    }
    protocol = _if_exists(inb, "protocol", "NULL")
    if protocol != "vmess" and protocol != "vless":
        raise Exception("Invalid protocol: " + protocol)
    if 'port' in inb:
        link["port"] = inb['port']
    if 'streamSettings' in inb:
        ss = 'streamSettings'
    elif 'transportSettings' in inb:
        ss = 'transportSettings'
    else:
        ss = None
    if ss:
        if 'network' in inb[ss]:
            link["net"] = inb[ss]['network']
            xs = link["net"] + "Settings" if link["net"] != "h2" else "httpSettings"
            if xs in inb[ss]:
                if link["net"] == "kcp":
                    link["path"] = _if_exists(inb[ss][xs], "seed", link["path"])
                elif link["net"] == "ws":
                    link = {**link, **_handle_http_inb(ss, xs)}
                elif link["net"] == "h2":
                    link = {**link, **_handle_http_inb(ss, xs)}
                elif link["net"] == "tcp":
                    link = {**link, **_handle_http_inb(ss, xs)}
                elif link["net"] == "grpc":
                    link["path"] = _if_exists(inb[ss][xs], "serviceName", link["path"])
                elif link["net"] == "quic":
                    link["host"] = _if_exists(inb[ss][xs], "security", link["host"])
                    link["path"] = _if_exists(inb[ss][xs], "key", link["path"])
        if 'security' in inb[ss] and inb[ss]['security'] != "none":
            link["tls"] = inb[ss]['security']
            link["sni"] = link["host"]
    if protocol == "vmess":
        return writelink("vmess", jsondumps({**link,
                "v": "2",
                "type": "",
                "ps": "^NAME^",
                "add": "^ADDRESS^",
                "id": "^UUID^",
                "aid": "^AID^",
                "scr": "^SCR^",
                }, separators=(',', ':')))
    return ("vless", f"^UUID^@^ADDRESS^:{link['port']}" +
        f"?path={link['path']}&security={link['tls']}&encryption=none&host={link['host']}&type={link['net']}&sni={link['sni']}" +
        "#^NAME^")

def cfgtolink( # Calls inbtolink for an inbound in cfg
        cfg,
        inb=None, # Index of the inbound. Only used when you have multiple inbounds in your cfg
        ):
    cfg = anytojson(cfg)
    valid, reason = isvalidcfg(cfg)
    if not valid:
        raise ValueError(reason)
    if 'inbound' in cfg:
        return inbtolink(cfg['inbound'])
    if 'inbounds' in cfg:
        if len(cfg['inbounds']) == 1:
            inb = 0
        if inb is None:
            raise Exception("No inbounds or Multiple inbounds were found and no 'inb' parameter was given to the function")
        return inbtolink(cfg['inbounds'][inb])
    raise Exception("No inbound found in configuration file")

def api(action, *args, infile=None, backend="xray", port=10085):
    command = [backend, 'api', action, '-s', f'127.0.0.1:{int(port)}', '-t', '2', *args]
    out = subrun(
        command,
        input=infile,
        capture_output=True,
        )
    return out
    #raise Exception("api call failed '{0}' The output is as follows:\n--stdout:\n{1}\n--stderr:\n{2}".format(' '.join(command), out.stdout.decode(), out.stderr.decode()))

def parse_traffic(js):
    seperate = ">>>"
    js = anytojson(js)
    users = {}
    for entry in js['stat']:
        try:
            kind, user, traffic, mode = entry['name'].split(seperate)
        except (KeyError, ValueError):
            continue
        user = user.split("@")[1]
        if kind != "user" or traffic != "traffic" or mode != "downlink" and mode != "uplink":
            continue
        try:
            users[user] = int(users[user]) + int(entry['value'])
        except KeyError:
            users[user] = int(entry['value'])
    return users

def readinfile(infile):
    if not isopenedfile(infile):
        infile = open(infile, "r")
    return infile

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
        service="v2ray@raytools",
        ):
    sc = None
    codes = []
    for server in servers:
        if type(server) != str:
            name = server[0]
            sc = server[1]
        else:
            name = server
            sc = service
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
    return datetime.now(tz=ZoneInfo("Asia/Tehran")).replace(microsecond=0)

def timemake(date):
    return datetime(*[int(i) for i in date])

def timedelta(date, days): # Increment/Decrement days in timestamp or datetime object. Returns timestamp
    if isinstance(date, datetime):
        date = timetostamp(date)
    if isinstance(date, int):
        return date + days * 86400
    raise Exception("Invalid Type")

def strtotime(date): # Converts standard ISO8601 string to datetime object
    if not isinstance(date, str):
        raise TypeError("Invalid Type")
    if "T" in date:
        date= date.split("T")[0]
    if not recompile(r"(\d{4})-(\d{2})-(\d{2})").match(date):
        raise ValueError(f"Invalid isoformat string: {date}")
    y, m, d = list(map(int, date.split('-')))
    return jdate(y, m, d)

def timetostr(date): # Converts datetime object to standard ISO8601 string ("YYYY-MM-DD HH:MM:SS.SSS")
    if not isinstance(date, datetime):
        raise TypeError("Invalid Type")
    return date.isoformat().split("T")[0]

def stamptotime(date): # Converts timestamp to a datetime object
    return datetime.fromtimestamp(date)

def timetostamp(date): # Converts datetime object to timestamp
    if not isinstance(date, datetime):
        raise TypeError("Invalid Type")
    return int(date.timestamp())

def isjsonsafe(text):
    illegals = '"\''
    for i in illegals:
        if i in text:
            return None
    return True

def matchword(text):
    return recompile(r'^[0-9A-Za-z]$').match(text)

def parse_date(date):
    if isinstance(date, int):
        return date
    if isinstance(date, jdate):
        return timetostamp(date)
    if not isinstance(date, str):
        raise TypeError("Invalid type")
    if date == "now":
        return timetostamp(timenow())
    m = recompile(r'^(\+|\-)?\d+$').match(date)
    if m:
        return timedelta(timetostamp(timenow()), int(m[0]))
    date = date.split("/")
    if len(date) < 3 or len(date) > 6 or not all([i.isdigit() for i in date]):
        raise ValueError("Invalid date: " + '/'.join(date))
    return timetostamp(timemake(date))

def isopenedfile(obj):
    return isinstance(obj, io.TextIOWrapper)

def isvalidcfg(cfg):
    more = "Please refer to https://xtls.github.io/config/api.html for help."
    if not 'inbounds' in cfg:
        return (False, "No 'inbounds' found in configuration file")
    if not 'stats' in cfg:
        return (False, "No 'stats' found in configuration file")
    try:
        if not cfg['policy']['levels']['0']['statsUserUplink'] == True or not cfg['policy']['levels']['0']['statsUserDownlink'] == True:
            return (False, 'Please set statsUserUplink and statsUserDownlink to true in your configuration file')
    except KeyError:
        return (False, "Invalid 'policy' entry. " + more)
    try:
        if not cfg['api']['tag'] == "api":
            return (False, "Invalid api tag")
        if not "HandlerService" in cfg['api']['services'] or not "StatsService" in cfg['api']['services']:
            return (False, "Please add 'HandlerService' and 'StatsService' to your api.services")
    except KeyError:
        return (False, "None or bad 'api' structure in configuration file. " + more)
    passed = False
    for inb in cfg['inbounds']:
        if inb['tag'] == "api":
            passed = True
            try:
                if not inb['listen'] == "127.0.0.1":
                    pass # Warning
                if not inb['protocol'] == "dokodemo-door":
                    return (False, "inbound.api protocol needs to be set to dokodemo-door")
                if not "port" in inb:
                    return (False, "No port was set in inbound.api")
            except KeyError:
                return (False, "bad api inbound structure. " + more)
    if not passed:
        return (False, "No api inbound was found. " + more)
    try:
        passed = False
        for rule in cfg['routing']['rules']:
            if rule['inboundTag'] == ["api"]:
                passed = True
                if not rule['outboundTag'] == "api":
                    raise KeyError
    except KeyError:
        return (False, "Invalid routing for api. " + more)
    if not passed:
        return (False, "No api route was found. " + more)
    return (True, "All good!")


def islink(link):
    if not isinstance(link, str):
        return False
    matched = matchlink(link, ["vmess", "vless"])
    if len(matched) != 2:
        return False

def matchlink(link, protocols):
    res = recompile(r'^(' + '|'.join(protocols) + r')://(.+)').match(link)
    return res.groups() if res else ()

def _handle_http_inb(ss, xs):
    final = {}
    if 'headers' in ss[xs]:
        if 'Host' in ss[xs]['headers']:
            final["host"] = ss[xs]['headers']['Host']
    if 'host' in ss[xs]:
        if type(ss[xs]['host']) == str:
            final["host"] = ss[xs]['host'] 
        else:
            final["host"] = ss[xs]['host'][0]
    if 'path' in ss:
        final["path"] = ss['path']
    if 'path' in ss[xs]:
        final["path"] = ss[xs]['path']
    return final

def _if_exists(dic, key, default=None):
    return dic[key] if key in dic else default