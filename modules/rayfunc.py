import jdatetime # pip3 install jdatetime
from subprocess import run as subrun
from uuid import uuid4, UUID
from re import compile as recompile
from json import load as jsonload
import io


def cfgtolink(cfg, inb=None):
    if type(cfg) == str:
        with open(cfg, "r") as f:
            cfg = jsonload(f)
    elif type(cfg) == io.TextIOWrapper:
        cfg = jsonload(f)
    if not isinstance(cfg, dict):
        raise TypeError("Invalid Type")

def _handle_http_inb(ss, xs):
    final = {}
    if 'headers' in ss[xs]:
        if 'Host' in ss[xs]['headers']:
            final["host"] = ss[xs]['headers']['Host'}
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

def inbtolink(inb): # Based on documention found in www.v2ray.com
    link = {
            "port": "",
            "net": "",
            "host": "",
            "path": "",
            "sni": "",
            "tls": "",
    }
    # {"ps": "mobileaftab_H", "port": "443", "host": "aparat.com", "path": "/", "net": "ws", "scr": "none", "aid": "0", "v": "2", "add": "37.32.5.224", "id": "3fc88da7-c187-15d9-3545-6ec6c057244e", "sni": "", "tls": "", "type": ""}
    protocol = _if_exists(inb, "protocol", "None")
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
        return {**link,
                "v": "2",
                "scr": "none",
                "type": "",
                "add": "",
                "ps": "",
                "id": "",
                "aid": "",
                }
    return "
    
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
