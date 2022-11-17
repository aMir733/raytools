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
    parser_rerun = subparser.add_parser('rerun', help='Rerun ray')

    # Frequently used help messages
    username_help = "User's username. Example: 'joe22' OR 'joe%' OR 'j_e22' all point to 'joe22'"
    newusername_help = "count@username -> count is the number of devices allowed by this user. username must be a unique string. Example: 2@joe22 1@jane 3@12"
    paid_help = "How much the user has paid."
    date_help = "days@date -> days is the subscription length. date is a slash seperated date like '1401/2/14' . Or 'now' for current time."

    # global arguments
    parser.add_argument('-d', '--database', type=str, default=default_db, help='Full path to the database file. Default: ' + default_db)
    # add arguments
    parser_add.add_argument('user', type=str, help=newusername_help)
    parser_add.add_argument('-d', '--date', type=str, default="now", help=date_help + ' Subscription\'s start date. Default: 30@now')
    parser_add.add_argument('-p', '--paid', type=int, default=0, help=paid_help + "Default: 0")
    parser_add.add_argument('-u', '--uuid', type=str, default=None, help='UUID to use for this user. Default: Randomly generated')
    parser_add.add_argument('-t', '--telegram-id', type=int, default=None, help='User\'s Telegram ID. Default: None')
    # get arguments
    parser_get.add_argument('user', type=str, help=username_help)
    parser_get.add_argument('server', type=str, help='Server\'s name in the database')
    parser_get.add_argument('-i', '--ip-address', type=str, default=None, help='Overwrite server\'s IP address')
    # renew arguments
    parser_renew.add_argument('user', type=str, help=username_help)
    parser_renew.add_argument('-d', '--date', type=str, default="now", help=date_help + ' Renew date. Default: 30@now')
    parser_renew.add_argument('-p', '--paid', type=int, default=0, help=paid_help + "Default: 0")
    # disable arguments
    parser_disable.add_argument('user', type=str, help=username_help)
    # enable arguments
    parser_enable.add_argument('user', type=str, help=username_help)
    # rerun arguments

    parser_add.set_defaults(func=handle_add)
    parser_get.set_defaults(func=handle_get)
    parser_renew.set_defaults(func=handle_add)
    parser_disable.set_defaults(func=handle_disable)
    parser_enable.set_defaults(func=handle_enable)
    parser_rerun.set_defaults(func=handle_rerun)
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
    kwargs["user"] = parse_username(kwargs["user"])
    kwargs["date"] = parse_date(kwargs["date"])
    add_user(
            db,
            kwargs["user"][1],
            kwargs["user"][0],
            kwargs["uuid"],
            nocommit=True,
            )
    add_payment(
            db,
            ("username", kwargs[1]),
            date=kwargs["date"][1],
            days=kwargs["date"][0],
            paid=kwargs["paid"],
            start=True,
            nocommit=True,
            )
    if telegram_id:
        add_tg(
                db,
                ("username", kwargs[1]),
                telegram_id,
                nocommit=True,
                )
    db.cun.commit()

def handle_get(*args, **kwargs):
    pass

def handle_renew(*args, **kwargs):
    kwargs["date"] = parse_date(kwargs["date"])
    add_payment(
            db,
            ("username", kwargs[1]),
            date=kwargs["date"][1],
            days=kwargs["date"][0],
            paid=kwargs["paid"],
            )

def handle_disable(*args, **kwargs):
    disable_user(db, ("username", kwargs["user"]),)

def handle_enable(*args, **kwargs):
    enable_user(db, ("username", kwargs["user"]),)

def handle_rerun():

def parse_username(username):
    if not isinstance(username, str):
        raise TypeError("Invalid type")
    if not "@" in username:
        _output(0, "No @ in user: " + username)
    username = username.split("@")
    if len(username) != 2:
        _output(0, "Got too many '@' for username")
    if not username[0].isdigit():
        _output(0, "count needs to be a number: " + username[0])
    if not recompile(r'^[0-9A-Za-z\-\_]+$').match(username[1]):
        _output(0, "username must be a string containing only: A-Z a-z 0-9 - _")
    return (*username)


def parse_date(date):
    if not isinstance(date, str):
        raise TypeError("Invalid type")
    if not "@" in date:
        _output(0, "Invalid date: " + date)
    date = date.split("@")
    if len(username) != 2:
        _output(0, "Got too many '@' for date")
    if not date[0].isdigit():
        _output(0, "'days' needs to be a number: " + date[0])
    if date[1] == "now":
        date[1] = timetostamp(timenow())
    else:
        date[1] = date[1].split("/")
        if len(date[1]) != 3 or not all([i.isdigit() for i in date[1]]):
            _output(0, "Invalid date: " + '/'.join(date[1]))
        date[1] = timetostamp(timemake(date[1]))
    return (*date)


if __name__ == '__main__':
    parse_args()
