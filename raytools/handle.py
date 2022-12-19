from .func import *
from .models import *
from sqlmodel import select
from sqlalchemy.exc import *
from json import loads as jsonloads, dumps as jsondumps, load as jsonload, dump as jsondump
from re import compile as recompile
from base64 import b64encode
from sys import stdout
from time import sleep
import logging

log = logging.getLogger(__name__)
CONFIGURATION = "/usr/local/etc/xray/raytools.json"
SYSTEMD = "xray@raytools"

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
    refresh_required()
    if telegram:
        handle_login(database, user, telegram)
    return user

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
    refresh_required()
    return user
    
def handle_renew(database, user, expires):
    user = handle_get(database, user)
    user.expires = parse_date(expires)
    if user.disabled == "expired":
        user.disabled = None
    database.add(user)
    database.commit()
    refresh_required()
    return user

def handle_revoke(database, user, uuid=None):
    uuid = uuid if uuid else make_uuid()
    if not isuuid(uuid):
        raise ValueError(f"'{uuid}' is not a valid UUID")
    user = handle_get(database, user)
    user.uuid = uuid
    database.add(user)
    database.commit()
    refresh_required()
    return user

def handle_disable(database, user, reason="disabled"):
    user = handle_get(database, user)
    user.disabled = reason
    database.add(user)
    database.commit()
    refresh_required()
    return user

def handle_enable(database, user, reset_traffic=False):
    user = handle_get(database, user)
    user.disabled = None
    if reset_traffic:
        user.traffic = 0
    database.add(user)
    database.commit()
    refresh_required()
    return user

def handle_refresh(database, configuration=CONFIGURATION, systemd=SYSTEMD, v2ray=False):
    configuration = readinfile(configuration)
    users = database.exec(select(User.id, User.count, User.uuid).where(User.disabled == None)).all()
    users_len = len(users)
    log.info("Found {} users".format(users_len))
    cfg = parsecfg(configuration)
    inbounds, port = getinbounds(cfg, users)
    log.info("API Port: %s" % port)
    add_inbounds = {
        "inbounds": inbounds,
    }
    rm_inbounds = {
        "inbounds": [{"tag": inb["tag"]} for inb in inbounds]
    }
    backend = "v2ray" if v2ray else "xray"
    max_tries = 8
    log.info("Initiated API rmi with max retry of " + str(max_tries))
    for i in range(max_tries):
        rmi = api("rmi", infile=jsondumps(rm_inbounds).encode(), backend=backend, timeout=2, port=port)
        if "failed to dial" in rmi.stderr.decode():
            raise Exception("API failed because we could not reach it")
        if "not enough information for making a decision" in rmi.stderr.decode():
            break
        if rmi.returncode != 0:
            log.warning("Retried because of an API error: " + rmi.stderr.decode())
        if i + 1 == max_tries:
            log.error("Restarting systemd because xray crashed")
            systemd_restart(systemd)
    adi = api("adi", infile=jsondumps(add_inbounds).encode(), backend=backend, timeout=2, port=port)
    if adi.returncode == 0:
        log.info("Successfully refreshed")
        refresh_required(False)
        return True
    log.error("adi failed with error: " + adi.stderr.decode())

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
    log.info("Count: %s" % len(users))
    if users and disable:
        log.warning("Disabling {} users".format(len(users)))
        for user in users:
            user.disabled = "expired"
            database.add(user)
        database.commit()
        refresh_required()
        return users

def handle_traffic(database):
    out = api("statsquery").stdout.decode()
    traffics = parse_traffic(out)
    for id, traffic in traffics.items():
        try:
            user = database.exec(select(User).where(User.id == int(id))).one()
        except NoResultFound:
            log.error("Could not find user {} in the database. Maybe a refresh is required")
            continue
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