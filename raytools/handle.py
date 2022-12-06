from .func import *
from .models import *
from sqlmodel import Session, select
from sqlalchemy.exc import *
from json import loads as jsonloads, dumps as jsondumps, load as jsonload, dump as jsondump
from re import compile as recompile
from base64 import b64encode
import logging
from sys import stdout

def handle_add(*args, **kwargs):
    session = Session(kwargs["database"].engine)
    if not kwargs["uuid"]:
        kwargs["uuid"] = make_uuid()
    if not isuuid(kwargs["uuid"]):
        kwargs["log"].critical(f"'{kwargs['uuid']}' is not a valid UUID")
        return 1
    if kwargs["sdate"]:
        kwargs["sdate"] = parse_date(kwargs["sdate"])
    kwargs["edate"] = parse_date(kwargs["edate"])
    user = User(
            username=kwargs["user"],
            count=kwargs["count"],
            uuid=kwargs["uuid"],
            )
    sale = Sale(
            sdate=kwargs["sdate"],
            edate=kwargs["edate"],
            first=True,
            user=user,
            )
    session.add(user)
    session.add(sale)
    if kwargs["telegram"]:
        telegram = Telegram(
                tg_id=kwargs["telegram"],
                user=User(username=kwargs["user"]),
                )
        session.add(telegram)
    session.commit()

def handle_get(*args, **kwargs):
    session = Session(kwargs["database"].engine)
    try:
        user = session.exec(
                select(User).where(User.username == kwargs["user"]),
                ).one()
    except NoResultFound:
        kwargs["log"].critical("No such username")
        return 1
    kwargs["log"].info("Found: {}".format(user))
    if kwargs["server"]:
        server = session.exec(select(Server).where(Server.name == kwargs["server"])).one()
        print(formatlink(
            server.link,
            name=kwargs["name"] if kwargs["name"] else server.name,
            address=kwargs["address"] if kwargs["address"] else server.address,
            scr=kwargs["security"] if kwargs["security"] else "none",
            uuid=uuid,
            aid=0,
            ))

def handle_renew(*args, **kwargs):
    session = Session(kwargs["database"].engine)
    kwargs["date"] = parse_date(kwargs["date"])
    user = session.exec(select(User).where(User.username == kwargs["user"])).one()
    sale = Sale(
            date=kwargs["date"],
            days=kwargs["days"],
            start=True,
            user=user,
            )
    session.add(sale)
    session.commit()

def handle_disable(*args, disabled=True, **kwargs):
    session = Session(kwargs["database"].engine)
    if not disabled:
        kwargs["reason"] = None
    user = session.exec(select(User).where(User.username == kwargs["user"])).one()
    user.disabled = kwargs["reason"]
    session.add(user)
    session.commit()

def handle_enable(*args, **kwargs):
    handle_disable(*args, **kwargs, disabled=False)

def handle_makecfg(*args, **kwargs):
    session = Session(kwargs["database"].engine)
    if kwargs["output"] == "-":
        kwargs["log"].info("Writing to stdout")
        out_file = stdout
    else:
        out_file = open(kwargs["output"], "w")
    if isinstance(kwargs["input"], str):
        kwargs["log"].info("Reading configuration from " + kwargs["input"])
        in_file = open(kwargs["input"], "r")
    else:
        kwargs["log"].info("Reading configuration from stdin...")
    if not isopenedfile(in_file):
        kwargs["log"].critical("Invalid type for input file")
        return 1
    users = session.exec(select(User.id, User.count, User.uuid).where(User.disabled == 0)).all()
    users_len = len(users)
    kwargs["log"].info("Found {} users".format(users_len))
    if not users_len:
        kwargs["log"].critical("No non-disabled user to add")
        return 1
    kwargs["log"].info("Writing config to " + kwargs["output"])
    out_file.write(jsondumps(populatecfg(users, in_file), indent=4))

def handle_restart(*args, **kwargs):
    pass

def handle_addsrv(*args, **kwargs):
    session = Session(kwargs["database"].engine)
    if islink(kwargs["link"]):
        link = readlink(kwargs["link"])
    else:
        try:
            with open(kwargs["link"], "r") as f:
                link = cfgtolink(f, inb=kwargs["inbound_index"])
        except FileNotFoundError:
            kwargs["log"].critical("Could not find the configuration located in: " + kwargs["link"])
            return 1
    server = Server(
            kwargs["name"],
            kwargs["address"],
            link,
            )
    session.add(server)
    session.commit()