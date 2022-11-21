#!/usr/bin/env python3

from modules.raydb import *
from modules.rayfunc import *
from json import loads as jsonloads, dumps as jsondumps, load as jsonload, dump as jsondump
from re import compile as recompile
from argparse import ArgumentParser as argparse
from base64 import b64encode
import qrcode
import logging
from sys import stdin, stdout
from os import environ as env

def handle_add(*args, **kwargs):
    db = Database(kwargs["database"])
    if not kwargs["uuid"]:
        kwargs["uuid"] = make_uuid()
    if not isuuid(kwargs["uuid"]):
        log.critical(f"'{kwargs['uuid']}' is not a valid UUID")
        return 1
    kwargs["date"] = parse_date(kwargs["date"])
    add_user(
            db,
            kwargs["user"],
            kwargs["count"],
            kwargs["uuid"],
            nocommit=True,
            )
    add_payment(
            db,
            ("username", kwargs["user"]),
            date=kwargs["date"],
            days=kwargs["days"],
            paid=kwargs["paid"],
            start=True,
            nocommit=True,
            )
    if kwargs["telegram_id"]:
        add_tg(
                db,
                ("username", kwargs["user"]),
                telegram_id,
                nocommit=True,
                )
    db.con.commit()

def handle_get(*args, **kwargs):
    db = Database(kwargs["database"])
    try:
        user_id, username, count, uuid, disabled = get_user(db, query=("username", "LIKE", kwargs["user"]))
    except ValueError:
        log.critical("User not found")
        return 1
    log.info(f"{user_id} {username} {count} {uuid} {disabled}")
    if kwargs["server"]:
        try:
            address, link = get_server(db, columns=("address", "link"), query=("name", "LIKE", kwargs["server"]))
        except ValueError:
            log.critical("Server was either not found or has a NULL value")
            return 1
        print(formatlink(
            link,
            name=kwargs["name"] if kwargs["name"] else kwargs["server"],
            address=kwargs["address"] if kwargs["address"] else address,
            scr=kwargs["security"] if kwargs["security"] else "none",
            uuid=uuid,
            aid=0,
            ))

def handle_renew(*args, **kwargs):
    db = Database(kwargs["database"])
    kwargs["date"] = parse_date(kwargs["date"])
    add_payment(
            db,
            ("username", kwargs["user"]),
            date=kwargs["date"],
            days=kwargs["days"],
            paid=kwargs["paid"],
            )

def handle_disable(*args, **kwargs):
    db = Database(kwargs["database"])
    disable_user(db, ("username", kwargs["user"]),)

def handle_enable(*args, **kwargs):
    db = Database(kwargs["database"])
    enable_user(db, ("username", kwargs["user"]),)

def handle_restart(*args, **kwargs):
    db = Database(kwargs["database"])
    if kwargs["output"] == "-":
        log.info("Writing to stdout")
        kwargs["output"] = stdout
    else:
        kwargs["output"] = open(kwargs["output"], "w")
    if isinstance(kwargs["input"], str):
        log.info("Reading configuration from " + kwargs["input"])
        kwargs["input"] = open(kwargs["input"], "r")
    else:
        log.info("Reading configuration from stdin...")
    if not isopenedfile(kwargs["input"]):
        log.critical("Invalid type for input file")
        return 1
    kwargs["input"] = kwargs["input"].read()
    users = get_users(db, columns=["id", "count", "username"], query=("disabled", "IS NOT", "1"))
    kwargs["output"].write(jsondumps(populatecfg(users, kwargs["input"]), indent=4))

def handle_addsrv(*args, **kwargs):
    db = Database(kwargs["database"])
    try:
        kwargs["link"] = readlink(kwargs["link"])
    except ValueError:
        try:
            with open(kwargs["link"], "r") as f:
                kwargs["link"] = cfgtolink(f, inb=kwargs["inbound_index"])
        except FileNotFoundError:
            log.critical("Could not find the configuration located in: " + kwargs["link"])
            return 1
    add_server(
            db,
            kwargs["name"],
            kwargs["address"],
            kwargs["link"],
            )

def parse_date(date):
    if not isinstance(date, str):
        raise TypeError("Invalid type")
    if date == "now":
        return timetostamp(timenow())
    date = date.split("/")
    if len(date) != 3 or not all([i.isdigit() for i in date]):
        log.critical("Invalid date: " + '/'.join(date))
        return 1
    return timetostamp(timemake(date))

def parse_args():
    # Frequently used help messages
    username_help = "User's username. Example: 'joe22' OR 'joe%' OR 'j_e22' all point to 'joe22'"
    username_new_help = "Username must be a unique string. Example: joe22 OR jane OR 124"
    paid_help = "How much the user has paid."
    date_help = "A slash seperated date format. Example: '1401/2/14' OR 'now' for current time."
    days_help = "Subscription's duration in days"

    envprefix = "RT_"

    parser = argparse(description='Manage your v2ray config file and its users')
    subparser = parser.add_subparsers(help='Action to take', required=True)
    parser_add = subparser.add_parser('add', help='Add a new user')
    parser_get = subparser.add_parser('get', help='Get user\'s client information')
    parser_renew = subparser.add_parser('renew', help='Renew user\'s subscription')
    parser_disable = subparser.add_parser('disable', help='Disable (deactivate) a user')
    parser_enable = subparser.add_parser('enable', help='Enable (activate) a user')
    parser_restart = subparser.add_parser('restart', help='Restart ray server/servers')
    parser_addsrv = subparser.add_parser('addsrv', help='Add a new server')

    # global arguments
    parser.add_argument('-d', '--database', type=str, default=env.get(envprefix + "DATABASE"), help='Full path to the database file. Can also be given from enviroment variable -> RT_DATABASE="customers.db"')
    parser.add_argument('-q', '--quiet', action="store_true", help="quiet output")
    parser.add_argument('-v', '--verbose', action="count", help="verbosity level")
    # add arguments
    parser_add.add_argument('user', type=str, help=username_new_help)
    parser_add.add_argument('-c', '--count', type=int, default=1, help='Number of devices allowed for this user. Default: 1')
    parser_add.add_argument('-d', '--date', type=str, default="now", help=date_help + ' Subscription\'s start date. Default: now')
    parser_add.add_argument('-y', '--days', type=int, default=30, help=days_help + ' Default: 30')
    parser_add.add_argument('-p', '--paid', type=int, default=0, help=paid_help + ' Default: 0')
    parser_add.add_argument('-u', '--uuid', type=str, default=None, help='UUID to use for this user. Default: Randomly generated')
    parser_add.add_argument('-t', '--telegram-id', type=int, default=None, help='User\'s Telegram ID. Default: None')
    # get arguments
    parser_get.add_argument('user', type=str, help=username_help)
    parser_get.add_argument('-s', '--server', type=str, default=None, help='Server\'s name')
    parser_get.add_argument('-a', '--address', type=str, default=None, help='Overwrite server\'s address')
    parser_get.add_argument('-n', '--name', type=str, default=None, help='Overwrite server\'s name (ps)')
    parser_get.add_argument('-c', '--security', type=str, default=None, help="Overwrite security (sc). Default: 'none'")
    # renew arguments
    parser_renew.add_argument('user', type=str, help=username_help)
    parser_renew.add_argument('-d', '--date', type=str, default="now", help=date_help + ' Renew date. Default: now')
    parser_renew.add_argument('-y', '--days', type=int, default=30, help=days_help + ' Default: 30')
    parser_renew.add_argument('-p', '--paid', type=int, default=0, help=paid_help + ' Default: 0')
    # disable arguments
    parser_disable.add_argument('user', type=str, help=username_help)
    # enable arguments
    parser_enable.add_argument('user', type=str, help=username_help)
    # restart arguments
    parser_restart.add_argument('-i', '--input', type=str, default=stdin, help="Source configuration file. You could also use stdin for this -> cat config.json | script.py")
    parser_restart.add_argument('-o', '--output', type=str, required=True, help="Destination configuration file. '-' for stdout.")
    parser_restart.add_argument('-s', '--service', type=str, required=True, help="Ray service name")
    # addsrv arguments
    parser_addsrv.add_argument('link', type=str, help="Path to your configuration file OR a vmess or vless link with these variables inside it: ^NAME^, ^ADDRESS^, ^UUID^, ^AID^(vmess only), ^SCR^(vmess only)")
    parser_addsrv.add_argument('-n', '--name', type=str, required=True, help="A unique name for your server. (Required)")
    parser_addsrv.add_argument('-a', '--address', type=str, required=True, help="Server's address. (Required)")
    parser_addsrv.add_argument('-i', '--inbound-index', type=str, default=None, help="Only required if you have several inbounds in your configuration file. Default: None")

    parser_add.set_defaults(func=handle_add)
    parser_get.set_defaults(func=handle_get)
    parser_renew.set_defaults(func=handle_add)
    parser_disable.set_defaults(func=handle_disable)
    parser_enable.set_defaults(func=handle_enable)
    parser_restart.set_defaults(func=handle_restart)
    parser_addsrv.set_defaults(func=handle_addsrv)
    args = parser.parse_args()
    if not args.database:
        parser.error("Database not set. -d --database or RT_DATABASE=")
    if args.verbose:
        if args.quiet:
            parser.error("Cannot be quiet (-q) and loud (-v) at the same time")
        if args.verbose > 4:
            args.verbose = 4
    return args

def cal_verb(verbose, quiet, default=30):
    if quiet:
        return 50
    if not verbose:
        return default
    res = default - verbose * 10
    return 10 if res < 10 else res

if __name__ == '__main__':
    args = parse_args()
    log = logging.getLogger('raytools')
    log.setLevel(10)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(cal_verb(args.verbose, args.quiet))
    console_handler.setFormatter(logging.Formatter("[%(levelname)s]: %(message)s"))
    log.addHandler(console_handler)
    exit(args.__dict__.pop('func')(**vars(args)))
