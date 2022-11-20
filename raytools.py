#!/usr/bin/env python3

from modules.raydb import *
from modules.rayfunc import *
from json import loads as jsonloads, dumps as jsondumps, load as jsonload, dump as jsondump
from re import compile as recompile
from argparse import ArgumentParser as argparse
from base64 import b64encode
import qrcode

default_db = "customers.db"

def parse_args():
    global parser
    parser = argparse(description='Manage your v2ray config file and its users')
    subparser = parser.add_subparsers(help='Action to take', required=True)
    parser_add = subparser.add_parser('add', help='Add a new user')
    parser_get = subparser.add_parser('get', help='Get user\'s client information')
    parser_renew = subparser.add_parser('renew', help='Renew user\'s subscription')
    parser_disable = subparser.add_parser('disable', help='Disable (deactivate) a user')
    parser_enable = subparser.add_parser('enable', help='Enable (activate) a user')
    parser_restart = subparser.add_parser('restart', help='Restart ray server/servers')
    parser_addsrv = subparser.add_parser('addsrv', help='Add a new server')

    # Frequently used help messages
    username_help = "User's username. Example: 'joe22' OR 'joe%' OR 'j_e22' all point to 'joe22'"
    username_new_help = "Username must be a unique string. Example: joe22 OR jane OR 124"
    paid_help = "How much the user has paid."
    date_help = "A slash seperated date format. Example: '1401/2/14' OR 'now' for current time."
    days_help = "Subscription's duration in days"

    # global arguments
    parser.add_argument('-d', '--database', type=str, default=default_db, help='Full path to the database file. Default: ' + default_db)
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
    args.__dict__.pop('func')(**vars(args))

def _output(level, message, print_help=None):
    if print_help:
        parser.print_help()
    if level == 0:
        print("[ERROR]: " + message)
        exit(1)
    elif level == 1:
        print("[WARNING]: " + message)
    elif level == 2:
        print("[INFO]: " + message)

def handle_add(*args, **kwargs):
    db = Database(kwargs["database"])
    if not kwargs["uuid"]:
        kwargs["uuid"] = make_uuid()
    if not isuuid(kwargs["uuid"]):
        _output(0, kwargs["uuid"] + " is not a valid UUID")
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
        user_id, username, count, uuid, disabled = get_user(db, ("username", kwargs["user"]))
    except ValueError:
        _output(0, "User not found")
    _output(2, f"\nuser_id: {user_id}\nusername: {username}\ncount: {count}\nuuid: {uuid}\ndisabled: {disabled}")
    if kwargs["server"]:
        try:
            address, link = get_server(db, ("name", kwargs["server"]))
        except ValueError:
            _output(0, "Server was either not found or has a NULL value")
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

def handle_restart():
    db = Database(kwargs["database"])
    pass

def handle_addsrv(*args, **kwargs):
    db = Database(kwargs["database"])
    try:
        kwargs["link"] = readlink(kwargs["link"])
    except ValueError:
        try:
            with open(kwargs["link"], "r") as f:
                kwargs["link"] = cfgtolink(f, inb=kwargs["inbound_index"])
        except FileNotFoundError:
            _output(0, "Could not find configuration file in: " + kwargs["link"])
    print(kwargs["link"])
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
        _output(0, "Invalid date: " + '/'.join(date))
    return timetostamp(timemake(date))

if __name__ == '__main__':
    parse_args()
