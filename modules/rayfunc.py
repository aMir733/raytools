import jdatetime # pip3 install jdatetime
from subprocess import run as subrun
from uuid import uuid4, UUID
from re import compile as recompile
from json import load as jsonload, dumps as jsondumps
import io
from base64 import b64encode, b64decode

def formatlink(
        link,
        **kwargs,
        ):
    if not isinstance(link, str):
        raise TypeError("Invalid Type")
    matched = _matchlink(link, ["vmess", "vless"])
    if not matched:
        raise Exception("Invalid Link")
    for key, value in kwargs.items():
        if not isinstance(value, str):
            raise TypeError("Invalid Type")
        if not _isjsonsafe(value):
            raise Exception("Value contains an illegal character: " + value)
        link.replace("^{}^".format(key.upper()), value)

def inbtolink(
        inb,
        nobase64=None,
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
        final = "vmess://" + jsondumps({**link,
                "v": "2",
                "type": "",
                "ps": "^NAME^",
                "add": "^ADDRESS^",
                "id": "^UUID^",
                "aid": "^AID^",
                "scr": "^SCR^",
                }, separators=(',', ':'))
        if nobase64:
            return final
        return b64encode(final.encode()).decode()
    return ("vless://^UUID^@^ADDRESS^:{link['port']}" +
            "?path={link['path']}&security={link['tls']}&encryption=none&host={link['host']}&type={link['net']}&sni={link['sni']}" +
            "#^NAME^")

def cfgtolink( # Calls inbtolink for an inbound in cfg
        cfg,
        inb=None, # Index of the inbound. Only used when you have multiple inbounds in your cfg
        ):
    if type(cfg) == str:
        with open(cfg, "r") as f:
            cfg = jsonload(f)
    elif type(cfg) == io.TextIOWrapper:
        cfg = jsonload(f)
    if not isinstance(cfg, dict):
        raise TypeError("Invalid Type")
    if 'inbound' in cfg:
        return inbtolink(cfg['inbound'])
    if 'inbounds' in cfg:
        if len(cfg['inbounds']) == 1:
            inb = 0
        if inb is None:
            raise Exception("No inbounds or Multiple inbounds were found and no 'inb' parameter was given to the function")
        return inbtolink(cfg['inbounds'][inb])
    raise Exception("No inbound found in configuration file")

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
        raise TypeError("Invalid Type")
    if "T" in date:
        date= date.split("T")[0]
    if not recompile(r"(\d{4})-(\d{2})-(\d{2})").match(date):
        raise ValueError(f"Invalid isoformat string: {date}")
    y, m, d = list(map(int, date.split('-')))
    return jdatetime.date(y, m, d)

def timetostr(date): # Converts datetime object to standard ISO8601 string ("YYYY-MM-DD HH:MM:SS.SSS")
    if not isinstance(date, jdatetime.datetime):
        raise TypeError("Invalid Type")
    return date.isoformat().split("T")[0]

def stamptotime(date): # Converts timestamp to a datetime object
    return jdatetime.datetime.fromtimestamp(date)

def timetostamp(date): # Converts datetime object to timestamp
    return int(date.timestamp())

def _isjsonsafe(text):
    illegals = '"\''
    for i in illegals:
        if i in text:
            return None
    return True

def _matchword(text):
    return recompile(r'^[0-9A-Za-z]$').match(text)

def _matchlink(link, protocols):
    return recompile(r'^(' + '|'.join(protocols) + r')://(.*)').match(link)

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

