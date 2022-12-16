from .func import *
from .models import *
from sqlmodel import select
from sqlalchemy.exc import *
from json import loads as jsonloads, dumps as jsondumps, load as jsonload, dump as jsondump
from re import compile as recompile
from base64 import b64encode
import logging
from sys import stdout

def handle_add(*args, **kwargs):
    if not kwargs["uuid"]:
        kwargs["uuid"] = make_uuid()
    if not isuuid(kwargs["uuid"]):
        raise ValueError(f"'{kwargs['uuid']}' is not a valid UUID")
    user = User(
            username=kwargs["username"],
            count=kwargs["count"],
            uuid=kwargs["uuid"],
            expires=parse_date(kwargs["expires"]),
            )
    kwargs["database"].add(user)
    if kwargs["telegram"]:
        telegram = Telegram(
                id=kwargs["telegram"],
                user=User(username=kwargs["username"]),
                )
        kwargs["database"].add(telegram)
    kwargs["database"].commit()

def handle_get(*args, **kwargs):
    table = "uuid" if isuuid(kwargs["user"]) else "username"
    user = kwargs["database"].exec(
            select(User).where(getattr(User, table) == kwargs["user"]),
            ).one()
    return user
    #kwargs["log"].info("Found: {}".format(user))
    #if kwargs["server"]:
    #    server = kwargs["database"].exec(select(Server).where(Server.name == kwargs["server"])).one()
    #    return(formatlink(
    #        server.link,
    #        name=kwargs["name"] if kwargs["name"] else server.name,
    #        address=kwargs["address"] if kwargs["address"] else server.address,
    #        scr=kwargs["security"] if kwargs["security"] else "none",
    #        uuid=uuid,
    #        aid=0,
    #        ))

def handle_renew(*args, **kwargs):
    user = handle_get(*args, **kwargs)
    user.expires = parse_date(kwargs["expires"])
    kwargs["database"].add(user)
    kwargs["database"].commit()

def handle_disable(*args, disabled=True, **kwargs):
    if not disabled:
        kwargs["reason"] = None
    user = handle_get(*args, **kwargs)
    user.disabled = kwargs["reason"]
    kwargs["database"].add(user)
    kwargs["database"].commit()

def handle_enable(*args, **kwargs):
    handle_disable(*args, **kwargs, disabled=False)

def handle_refresh(*args, **kwargs):
    kwargs["input"] = readinfile(kwargs["input"])
    users = kwargs["database"].exec(select(User.id, User.uuid).where(User.disabled == None)).all()
    users_len = len(users)
    kwargs["log"].info("Found {} users".format(users_len))
    cfg = parsecfg(kwargs["input"])
    inbounds, port = getinbounds(cfg, users)
    backend="v2ray" if kwargs["v2ray"] else "xray"
    return (api(i, inbounds, backend=backend, port=port) for i in ("rmi", "adi"))

def handle_addsrv(*args, **kwargs):
    if islink(kwargs["link"]):
        link = readlink(kwargs["link"])
    else:
        with open(kwargs["link"], "r") as f:
            link = cfgtolink(f, inb=kwargs["inbound_index"])
    server = Server(
            kwargs["name"],
            kwargs["address"],
            link,
            )
    kwargs["database"].add(server)
    kwargs["database"].commit()

def handle_expired(*args, **kwargs):
    date = parse_date(kwargs["expires"])
    kwargs["log"].info("Showing users that expire before " + str(stamptotime(date)))
    return kwargs["database"].exec(select(User).where(User.expires > date)).all()

def handle_login(*args, **kwargs):
    user = handle_get(*args, **kwargs)
    telegram = Telegram(id=kwargs["telegram"], user=user)
    kwargs["database"].add(telegram)
    kwargs["database"].commit()