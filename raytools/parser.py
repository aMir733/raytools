from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from os import environ as env
from sys import stdin
import logging

class Base:
    # Frequently used help messages
    db_help = 'Full path to the database file. '
    'Can also be given from enviroment variable '
    '-> RT_DATABASE="customers.db"'
    username_help = "Username"
    username_new_help = "Username must be a unique string. Example: joe22 OR jane OR 124"
    date_help = "A slash seperated date format (optionally with time). Example: '1401/2/14' OR '1401/4/22/16/30' OR 'now' for current time."
    days_help = "Subscription's duration in days"

    def calc_verb(self, verbose, quiet, default):
        if quiet:
            return 50
        if not verbose:
            return default
        res = default - verbose * 10
        return 10 if res < 10 else res

    def configure_logging(self, logs, level):
        logging.basicConfig(
                level=level,
                format="[%(levelname)s] %(name)s: %(message)s",
                )
        for log, delta_level in logs:
            logging.getLogger(log).setLevel(level + delta_level)
 
    def parse(self, logs, default=30):
        args = self.parser.parse_args()
        if not args.database:
            self.parser.error("Database not set. -d --database or RT_DATABASE=")
        if args.verbose:
            if args.quiet:
                self.parser.error("Cannot be quiet (-q) and loud (-v) at the same time")
            if args.verbose > 4:
                args.verbose = 4
        args.verbose = self.calc_verb(args.verbose, args.quiet, default)
        self.configure_logging(logs, args.verbose)
        return args

class Raytools(Base):
    def __init__(self):
        Raytools.parser = ArgumentParser(
            description='Manage your ray servers',
            formatter_class=ArgumentDefaultsHelpFormatter
            )
        Raytools.subparser = self.parser.add_subparsers(help='Action to take', required=True, dest="action")
        Raytools.parser_add = self.subparser.add_parser('add', help='Add a new user')
        Raytools.parser_get = self.subparser.add_parser('get', help='Get user\'s client information')
        Raytools.parser_renew = self.subparser.add_parser('renew', help='Renew user\'s subscription')
        Raytools.parser_disable = self.subparser.add_parser('disable', help='Disable (deactivate) a user')
        Raytools.parser_enable = self.subparser.add_parser('enable', help='Enable (activate) a user')
        Raytools.parser_makecfg = self.subparser.add_parser('makecfg', help='Populate the configuration file and output it to a file (or stdout)')
        Raytools.parser_restart = self.subparser.add_parser('restart', help='Restart ray servers')
        Raytools.parser_addsrv = self.subparser.add_parser('addsrv', help='Add a new server')

        # global arguments
        self.parser.add_argument(
            '-d', '--database', type=str, default=env.get("RT_DATABASE"),
            help=self.db_help
            )
        self.parser.add_argument('-q', '--quiet', action="store_true", help="quiet output")
        self.parser.add_argument('-v', '--verbose', action="count", help="verbosity level")
        # add arguments
        self.parser_add.add_argument('user', type=str, help=self.username_new_help)
        self.parser_add.add_argument('-c', '--count', type=int, default=1, help='Number of devices allowed for this user')
        self.parser_add.add_argument('-b', '--sdate', type=str, default=None, help=self.date_help + ' Subscription\'s start date')
        self.parser_add.add_argument('-e', '--edate', type=str, required=True, help=self.date_help + ' Subscription\'s end date')
        self.parser_add.add_argument('-u', '--uuid', type=str, default=None, help='UUID to use for this user')
        self.parser_add.add_argument('-p', '--plan', type=int, default=None, help='User\'s subscription\'s plan')
        self.parser_add.add_argument('-t', '--telegram', type=int, default=None, help='User\'s Telegram ID')
        # get arguments
        self.parser_get.add_argument('user', type=str, help=self.username_help)
        self.parser_get.add_argument('-s', '--server', type=str, default=None, help='Server\'s name')
        self.parser_get.add_argument('-a', '--address', type=str, default=None, help='Overwrite server\'s address')
        self.parser_get.add_argument('-n', '--name', type=str, default=None, help='Overwrite server\'s name (ps)')
        self.parser_get.add_argument('-c', '--security', type=str, default=None, help="Overwrite security (sc)")
        # renew arguments
        self.parser_renew.add_argument('user', type=str, help=self.username_help)
        self.parser_renew.add_argument('-b', '--sdate', type=str, default=None, help=self.date_help + ' Subscription\'s start date')
        self.parser_renew.add_argument('-e', '--edate', type=str, required=True, help=self.date_help + ' Subscription\'s end date')
        # disable arguments
        self.parser_disable.add_argument('user', type=str, help=self.username_help)
        self.parser_disable.add_argument(
            '-r', '--reason', type=str, required=True,
            help="Reason why this user is being disabled. Value should be in the 'disabled' table ('id' or 'reason'). If you pass a string it will create an entry for you"
            )
        # enable arguments
        self.parser_enable.add_argument('user', type=str, help=self.username_help)
        # makecfg arguments
        self.parser_makecfg.add_argument(
            '-i', '--input', type=str, default=stdin,
            help="Source configuration file. You could also use stdin for this -> cat config.json | script.py"
            )
        self.parser_makecfg.add_argument('-o', '--output', type=str, required=True, help="Destination configuration file. '-' for stdout.")
        # restart arguments
        self.parser_restart.add_argument('-s', '--service', type=str, required=True, help="Ray service name")
        # addsrv arguments
        self.parser_addsrv.add_argument(
            'link', type=str, 
            help="Path to your configuration file OR a vmess or vless link with these variables inside it: ^NAME^, ^ADDRESS^, ^UUID^, ^AID^(vmess only), ^SCR^(vmess only)"
            )
        self.parser_addsrv.add_argument('-n', '--name', type=str, required=True, help="A unique name for your server")
        self.parser_addsrv.add_argument('-a', '--address', type=str, required=True, help="Server's address")
        self.parser_addsrv.add_argument('-i', '--inbound-index', type=str, default=None, help="Only required if you have several inbounds in your configuration file")
    
class Daemon(Base):
    def __init__(self):
        Daemon.parser = ArgumentParser(
            description='Daemon to check for users activity and expiration date',
            formatter_class=ArgumentDefaultsHelpFormatter
            )
        self.parser.add_argument(
            '-d', '--database', type=str, default=env.get("RT_DATABASE"),
            help=self.db_help
            )
        self.parser.add_argument('-q', '--quiet', action="store_true", help="quiet output")
        self.parser.add_argument('-v', '--verbose', action="count", help="verbosity level")
        self.parser.add_argument('logs', type=str, nargs='+', help='Log files to watch for user activity')