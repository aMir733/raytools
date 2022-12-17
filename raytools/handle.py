from .func import *
from .models import *
from sqlmodel import select
from sqlalchemy.exc import *
from json import loads as jsonloads, dumps as jsondumps, load as jsonload, dump as jsondump
from re import compile as recompile
from base64 import b64encode
from sys import stdout
import logging

log = logging.getLogger(__name__)

def handle_add(database, username, count, expires, uuid=None, telegram=None):
    uuid = uuid if uuid else make_uuid()
    if not isuuid(uuid):
        raise ValueError(f"'{uuid}' is not a valid UUID")
    user = User(
            username=username,
            count=count,
            uuid=uuid,
            expires=parse_date(expires),
            )
    database.add(user)
    database.commit()
    if telegram:
        handle_login(database, user, telegram)

def handle_get(database, user):
    if isinstance(user, User):
        return user
    col = "uuid" if isuuid(user) else "username"
    if isinstance(user, (list, tuple)):
        user, col = user
    user = database.exec(
            select(User).where(getattr(User, col) == user),
            ).one()
    return user

def handle_uuid(database, user, uuid=None):
    uuid = uuid if uuid else make_uuid()
    user = handle_get(database, user)
    user.uuid = uuid
    database.add(user)
    database.commit()
    
def handle_renew(database, user, expires):
    user = handle_get(database, user)
    user.expires = parse_date(expires)
    database.add(user)
    database.commit()

def handle_disable(database, user, reason, disabled=True):
    reason = reason if disabled else None
    user = handle_get(database, user)
    user.disabled = reason
    database.add(user)
    database.commit()

def handle_enable(database, user):
    handle_disable(database, user, disabled=False)

def handle_refresh(database, infile, v2ray=False):
    infile = readinfile(infile)
    users = database.exec(select(User.id, User.count, User.uuid).where(User.disabled == None)).all()
    users_len = len(users)
    log.info("Found {} users".format(users_len))
    cfg = parsecfg(infile)
    inbounds, port = getinbounds(cfg, users)
    inbounds = {
        "inbounds": inbounds,
    }
    backend = "v2ray" if v2ray else "xray"
    return [api(i, infile=jsondumps(inbounds).encode(), backend=backend, port=port) for i in ("rmi", "adi")]

def handle_addsrv(database, link, inbound_index, name, address):
    if islink(link):
        link = readlink(link)
    else:
        with open(link, "r") as f:
            link = cfgtolink(f, inb=inbound_index)
    server = Server(
            name,
            address,
            link,
            )
    database.add(server)
    database.commit()

def handle_expired(database, expired, disable=False):
    date = parse_date(expired)
    log.info("Showing users that expire before " + str(stamptotime(date)))
    users = database.exec(select(User).where(User.expires < date, User.disabled == None)).all()
    if disable:
        log.warning("Disabling {} users".format(len(users)))
        for user in users:
            user.disabled = "expired"
            database.add(user)
        database.commit()
    return users

def handle_traffic(database):
    out = api("statsquery")    
    traffics = parse_treffic(out)
    for id, traffic in traffics.items():
        user = database.exec(select(User).where(User.id == int(id))).one()
        if not isinstance(user.traffic, int):
            user.traffic = 0
        user.traffic = user.traffic + traffic
        database.add(user)
    database.commit()
    api("statsquery", "-reset=true") # Reset the traffic

def handle_login(database, user, telegram):
    user = handle_get(database, user)
    telegram = Telegram(id=telegram, user=user)
    database.add(telegram)
    database.commit()