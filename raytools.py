from raytools.handle import *
from raytools.db import Database
from raytools.parser import Raytools

def init_args():
    parser = Raytools()
    parser.parser_add.set_defaults(func=handle_add)
    parser.parser_get.set_defaults(func=handle_get)
    parser.parser_renew.set_defaults(func=handle_add)
    parser.parser_disable.set_defaults(func=handle_disable)
    parser.parser_enable.set_defaults(func=handle_enable)
    parser.parser_makecfg.set_defaults(func=handle_makecfg)
    parser.parser_restart.set_defaults(func=handle_restart)
    parser.parser_addsrv.set_defaults(func=handle_addsrv)
    return parser.parse(logs=(('sqlalchemy.engine', 10),), default=30)
    
def init_db(database):
    db = Database(database)
    db.create()
    return db
    
def main():
    args = init_args()
    db = init_db(args.__dict__.pop('database'))
    exit(args.__dict__.pop('func')(**vars(args), database=db, log=logging))

if __name__ == '__main__':
    main()