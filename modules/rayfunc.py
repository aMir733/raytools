import jdatetime # pip3 install jdatetime
from zoneinfo import ZoneInfo
from subprocess import run as subrun
from uuid import uuid4, UUID
from re import compile as recompile
from json import load as jsonload, loads as jsonloads, dumps as jsondumps
import io
from base64 import b64encode, b64decode

def anytojson(inp):
    if isinstance(inp, str):
        try:
            return jsonloads(inp)
        except:
            with open(inp, "r") as f:
                return jsonload(f)
    if isopenedfile(inp):
        return jsonload(inp)
    if not isinstance(cfg, dict):
        raise TypeError("Invalid Type")
    return inp

def populatecfg(
        clients, # [(x,y,z),(a,b,c)] -> (user_id, count, uuid)
        cfg, # {} OR "{}" OR /file/path OR io.TextIOWrapper
        ):
    cfg = anytojson(cfg)
    checkcfg(cfg)
    if not isinstance(clients, list) and not isinstance(clients, tuple):
        raise TypeError("Invalid type for clients. Only lists or tuples are acceptable")
    passed = None
    if 'inbound' in cfg:
        cfg['inbounds'] = [cfg.pop("inbound")]
    for inbound in cfg['inbounds']:
        if inbound['protocol'] != 'vmess' and inbound['protocol'] != 'vless':
            continue
        default_client = inbound['settings']['clients'][0]
        if default_client['email'] != "admin@raytools":
            continue
        passed = True
        max_digits = len(str(max(clients)[0]))
        for client in clients:
            inbound['settings']['clients'].append({
                **default_client,
                "id": client[2], # uuid
                "email": "{}@{}".format(
                    str(client[1]),
                    str(client[0]).zfill(max_digits),
                    )
            })
    if not passed:
        raise ValueError("Could not find an appropriate inbound to use")
    return cfg

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
    if not isinstance(link, str):
        raise TypeError("Invalid Type")
    matched = matchlink(link, ["vmess", "vless"])
    if len(matched) != 2:
        raise ValueError("Invalid Link or Protocol")
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
        if not _isjsonsafe(value):
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
    checkcfg(cfg)
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

def isopenedfile(obj):
    return isinstance(obj, io.TextIOWrapper)

def checkcfg(cfg):
    if not 'inbound' in cfg and not 'inbounds' in cfg:
        raise ValueError("No 'inbounds' found in configuration file")
    if 'inbound' in cfg and 'inbounds' in cfg:
        raise ValueError("Cannot have both 'inbound' and 'inbounds' entry in configuration file")

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

