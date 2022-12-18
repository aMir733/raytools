#!/usr/bin/env python3
from raytools.handle import *
from raytools.db import Database
from raytools.parser import Raytools
import logging
from raytools.log import *

def init_args():
    parser = Raytools()
    parser.parser_add.set_defaults(func=handle_add)
    parser.parser_get.set_defaults(func=handle_get)
    parser.parser_renew.set_defaults(func=handle_renew)
    parser.parser_uuid.set_defaults(func=handle_uuid)
    parser.parser_disable.set_defaults(func=handle_disable)
    parser.parser_enable.set_defaults(func=handle_enable)
    parser.parser_refresh.set_defaults(func=handle_refresh)
    parser.parser_addsrv.set_defaults(func=handle_addsrv)
    parser.parser_expired.set_defaults(func=handle_expired)
    parser.parser_login.set_defaults(func=handle_login)
    return parser.parse()

def main():
    args = init_args()
    verb = calc_verb(args.__dict__.pop('verbose'), args.__dict__.pop('quiet'), 30)
    configure_logging(logging, logs=((10, 'sqlalchemy.engine'),), level=verb, format="[%(levelname)s] %(name)s: %(message)s")
    if args.func == handle_refresh and not isinstance(args.configuration, str):
        log.warning("No configuration was specified in the arguments so, reading from stdin...")
    db = Database(args.__dict__.pop('database'))
    session = db.session()
    r = args.__dict__.pop('func')(**vars(args), database=session)
    if r:
        print(r)

if __name__ == '__main__':
    main()