from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from os import environ as env, path
from sys import stdin
from yaml import load, FullLoader
import logging

log = logging.getLogger(__name__)

class Base:
    # Frequently used help messages
    db_help = 'Full path to the database file. '
    'Can also be given from enviroment variable '
    '-> RT_DATABASE="customers.db"'
    username_help = "Username or UUID"
    username_new_help = "Username must be a unique string. Example: joe22 OR jane OR 124"
    date_help = "A slash seperated date format (optionally with time)."
    "Can also use + or - for delta time."
    "Example: '1401/2/14' OR '1401/4/22/16/30' OR +30 (30 days from now) OR -7 (7 days before) OR 'now' for the current time."
    days_help = "Subscription's duration in days"
    configuration_help = "Source configuration file. You could also use stdin for this -> cat config.json | raytools.py"
    yaml_help = "Path to your yaml configuration file"
    telegram_help = "User's Telgram ID"
    
    def parse_yaml(self, filepath):
        with open(filepath) as f:
            return load(f, Loader=FullLoader)

    def parse(self):
        args = self.parser.parse_args()
        ycfg = {}
        if args.yaml:
            try:
                ycfg = self.parse_yaml(args.yaml)
            except FileNotFoundError:
                self.parser.error(f"Yaml file {args.yaml} was not found")
        else:
            yfile = "raytools.yaml"
            paths = [
                f"./{yfile}",
                env.get('XDG_CONFIG_HOME', env.get('HOME', '~') + "/.config") + f"/{yfile}",
                f"/usr/local/etc/{yfile}",
                f"/etc/{yfile}",
                ]
            for filepath in paths:
                try:
                    ycfg = self.parse_yaml(filepath)
                except FileNotFoundError:
                    continue
        if not args.database:
            if not "database" in ycfg:
                self.parser.error("Database not set. -d --database or RT_DATABASE=")
            args.database = ycfg.pop("database")
        args.database = path.expanduser(args.database)
        args.yaml = ycfg
        return args

class Raytools(Base):
    def __init__(self):
        Raytools.parser = ArgumentParser(
            description='Manage your ray servers',
            formatter_class=ArgumentDefaultsHelpFormatter
            )
        Raytools.subparser = self.parser.add_subparsers(help='Action to take', required=True)
        Raytools.parser_add = self.subparser.add_parser('add', help='Add a new user')
        Raytools.parser_get = self.subparser.add_parser('get', help='Get user\'s information')
        Raytools.parser_renew = self.subparser.add_parser('renew', help='Renew user\'s subscription')
        Raytools.parser_revoke = self.subparser.add_parser('revoke', help='Revoke user\'s uuid')
        Raytools.parser_disable = self.subparser.add_parser('disable', help='Disable (deactivate) a user')
        Raytools.parser_enable = self.subparser.add_parser('enable', help='Enable (activate) a user')
        Raytools.parser_refresh = self.subparser.add_parser('refresh', help='Populate the configuration file and output it to a file (or stdout)')
        Raytools.parser_restart = self.subparser.add_parser('restart', help='Restart ray servers')
        Raytools.parser_addsrv = self.subparser.add_parser('addsrv', help='Add a new server')
        Raytools.parser_expired = self.subparser.add_parser('expired', help='Get a list of users who expire on a particular date')
        Raytools.parser_get_traffic = self.subparser.add_parser('get_traffic', help='Get a list of users traffic')
        Raytools.parser_reset = self.subparser.add_parser('reset', help='Reset user\'s traffic')
        Raytools.parser_register = self.subparser.add_parser('register', help='Link a user\'s Telegram ID to their Database ID')
        Raytools.parser_login = self.subparser.add_parser('login', help='Get user\'s information from their telegram ID')

        # global arguments
        self.parser.add_argument('-y', '--yaml', type=str, default=None, help=self.yaml_help)
        self.parser.add_argument(
            '-d', '--database', type=str, default=env.get("RT_DATABASE"),
            help=self.db_help
            )
        self.parser.add_argument('-q', '--quiet', action="store_true", default=False, help="quiet output")
        self.parser.add_argument('-v', '--verbose', action="count", default=None, help="verbosity level")
        # add arguments
        self.parser_add.add_argument('username', type=str, help=self.username_new_help)
        self.parser_add.add_argument('-c', '--count', type=int, default=1, help='Number of devices allowed for this user')
        self.parser_add.add_argument('-e', '--expires', type=str, required=True, help=self.date_help + ' Subscription\'s end date')
        self.parser_add.add_argument('-u', '--uuid', type=str, default=None, help='UUID to use for this user')
        # get arguments
        self.parser_get.add_argument('user', type=str, help=self.username_help)
        # renew arguments
        self.parser_renew.add_argument('user', type=str, help=self.username_help)
        self.parser_renew.add_argument('-e', '--expires', type=str, required=True, help=self.date_help + ' Subscription\'s end date.')
        # revoke arguments
        self.parser_revoke.add_argument('user', type=str, help=self.username_help)
        self.parser_revoke.add_argument('-u', '--uuid', type=str, default=None, help='UUID to use for this user. Randomize if not set')
        # disable arguments
        self.parser_disable.add_argument('user', type=str, help=self.username_help)
        self.parser_disable.add_argument(
            '-r', '--reason', type=str, required=True,
            help="Reason why this user is being disabled. Value should be in the 'disabled' table ('id' or 'reason'). If you pass a string it will create an entry for you"
            )
        # enable arguments
        self.parser_enable.add_argument('user', type=str, help=self.username_help)
        # refresh arguments
        self.parser_refresh.add_argument('-c', '--configuration', type=str, default=stdin, help=self.configuration_help)
        self.parser_refresh.add_argument('-s', '--systemd', type=str, required=True, help="Xray\'s systemd service name (Just in case)")
        # addsrv arguments
        self.parser_addsrv.add_argument(
            'link', type=str, 
            help="Path to your configuration file OR a vmess or vless link with these variables inside it: ^NAME^, ^ADDRESS^, ^UUID^, ^AID^(vmess only), ^SCR^(vmess only)"
            )
        self.parser_addsrv.add_argument('-n', '--name', type=str, required=True, help="A unique name for your server")
        self.parser_addsrv.add_argument('-a', '--address', type=str, required=True, help="Server's address")
        self.parser_addsrv.add_argument('-i', '--inbound-index', type=str, default=None, help="Only required if you have several inbounds in your configuration file")
        # expired argumenrts
        self.parser_expired.add_argument('-e', '--expired', type=str, default="now", help=self.date_help + ' Expire date.')
        self.parser_expired.add_argument('-d', '--disable', action="store_true", default=False, help='Also disable the users who have expired')
        # get_traffic
        self.parser_get_traffic.add_argument('-t', '--top', type=int, default=0, help='Limit the list to this number. 0 to show all users')
        self.parser_get_traffic.add_argument('-g', '--greater', type=int, default=0, help='Show only users who have exceeded this number. Will change \'--top\' to 0 automatically')
        # reset
        self.parser_reset.add_argument('user', type=str, help=self.username_help)
        # register
        self.parser_register.add_argument('user', type=str, help=self.username_new_help)
        self.parser_register.add_argument('-t', '--tg-id', type=int, required=True, help=self.telegram_help)
        # login arguments
        self.parser_login.add_argument('tg_id', type=str, help=self.telegram_help)
    
class Daemon(Base):
    def __init__(self):
        Daemon.parser = ArgumentParser(
            description='Daemon to check for user activity and expiration date and more...',
            formatter_class=ArgumentDefaultsHelpFormatter
            )
        self.parser.add_argument('-y', '--yaml', type=str, default=None, help=self.yaml_help)
        self.parser.add_argument(
            '-d', '--database', type=str, default=env.get("RT_DATABASE"),
            help=self.db_help
            )
        self.parser.add_argument('-c', '--configuration', type=str, required=True, help=self.configuration_help)
        self.parser.add_argument('-s', '--systemd', type=str, required=True, help="Xray\'s systemd service name (Just in case)")
        self.parser.add_argument('-l', '--output-log', default="./raytools-daemon.log", help="Where to write logs")
        self.parser.add_argument('logs', type=str, nargs='+', help='Log files to watch for user activity')

class Robot(Base):
    def __init__(self):
        Robot.parser = ArgumentParser(
            description='Telegram robot for you and your users',
            formatter_class=ArgumentDefaultsHelpFormatter,
            )
        self.parser.add_argument('-y', '--yaml', type=str, default=None, help=self.yaml_help)
        self.parser.add_argument('-l', '--output-log', default="./raytools-robot.log", help="Where to write logs")
        self.parser.add_argument(
            '-d', '--database', type=str, default=env.get("RT_DATABASE"),
            help=self.db_help
            )