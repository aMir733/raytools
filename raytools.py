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
    parser_add.add_argument('-d', '--date', type=str, default="now", help=date_help + ' Subscription\'s start date. Default: 30@now')
    parser_add.add_argument('-y', '--days', type=int, default=30, help=days_help + ' Default: 30')
    parser_add.add_argument('-p', '--paid', type=int, default=0, help=paid_help + ' Default: 0')
    parser_add.add_argument('-u', '--uuid', type=str, default=None, help='UUID to use for this user. Default: Randomly generated')
    parser_add.add_argument('-t', '--telegram-id', type=int, default=None, help='User\'s Telegram ID. Default: None')
    # get arguments
    parser_get.add_argument('user', type=str, help=username_help)
    parser_get.add_argument('server', type=str, help='Server\'s name in the database')
    parser_get.add_argument('-i', '--ip-address', type=str, default=None, help='Overwrite server\'s IP address')
    # renew arguments
    parser_renew.add_argument('user', type=str, help=username_help)
    parser_renew.add_argument('-d', '--date', type=str, default="now", help=date_help + ' Renew date. Default: 30@now')
    parser_renew.add_argument('-y', '--days', type=int, default=30, help=days_help + ' Default: 30')
    parser_renew.add_argument('-p', '--paid', type=int, default=0, help=paid_help + ' Default: 0')
    # disable arguments
    parser_disable.add_argument('user', type=str, help=username_help)
    # enable arguments
    parser_enable.add_argument('user', type=str, help=username_help)
    # restart arguments
    # addsrv arguments
    parser_addsrv.add_argument('configuration', type=str, help=username_help)
    parser_addsrv.add_argument('-n', '--name', type=str, required=True, help="Could be anything. (Required)")
    parser_addsrv.add_argument('-a', '--address', type=str, required=True, help="IP address or domain. (Required)")
    parser_addsrv.add_argument('-i', '--inbound-index', type=str, default=None, help="Index of the inbound. Only used if you have several inbounds in your configuration file.")

    parser_add.set_defaults(func=handle_add)
    parser_get.set_defaults(func=handle_get)
    parser_renew.set_defaults(func=handle_add)
    parser_disable.set_defaults(func=handle_disable)
    parser_enable.set_defaults(func=handle_enable)
    parser_restart.set_defaults(func=handle_restart)
    parser_addsrv.set_defaults(func=handle_addsrv)
    args = parser.parse_args()
    args.__dict__.pop('func')(**vars(args))


def _output(level, message):
    if level == 0: # Error
        parser.print_help()
        print("Error:\n\t")
        print(message)
        exit(1)
    elif level == 1: # Warning
        print("[Warning]: " + message)
    elif level == 2: # Info
        print("[Info]: " + message)

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
    if telegram_id:
        add_tg(
                db,
                ("username", kwargs["user"]),
                telegram_id,
                nocommit=True,
                )
    db.cun.commit()

def handle_get(*args, **kwargs):
    pass

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
    link = cfgtolink(
            kwargs["configuration"],
            "^NAME^",
            "^ADDRESS^",
            "^UUID^",
            "^AID^",
            "^SECURITY^",
            inb=kwargs["inbound_index"],
            nobase64=True,
            )
    add_server(
            db,
            kwargs["name"],
            kwargs["address"],
            link=link,
            )
    pass

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
