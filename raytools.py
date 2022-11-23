from raytools.handle import *
from raytools.db import Database
from raytools.parser import Parser

def calc_verb(verbose, quiet, default=30):
    if quiet:
        return 50
    if not verbose:
        return default
    res = default - verbose * 10
    return 10 if res < 10 else res

def configure_logging(level):
    logging.basicConfig(
            level=level,
            format="[%(levelname)s] %(name)s: %(message)s",
            )
    logging.getLogger('sqlalchemy.engine').setLevel(level + 10)
    
def init_args():
    parser = Parser()
    parser.parser_add.set_defaults(func=handle_add)
    parser.parser_get.set_defaults(func=handle_get)
    parser.parser_renew.set_defaults(func=handle_add)
    parser.parser_disable.set_defaults(func=handle_disable)
    parser.parser_enable.set_defaults(func=handle_enable)
    parser.parser_makecfg.set_defaults(func=handle_makecfg)
    parser.parser_restart.set_defaults(func=handle_restart)
    parser.parser_addsrv.set_defaults(func=handle_addsrv)
    args = parser.parse_args()
    return args
    
def init_db(database):
    db = Database(database)
    db.create()
    return db
    
def main():
    args = init_args()
    db = init_db(args.__dict__.pop('database'))
    log_level = calc_verb(args.verbose, args.quiet)
    configure_logging(log_level)
    exit(args.__dict__.pop('func')(**vars(args), database=db, log=logging))

if __name__ == '__main__':
    main()