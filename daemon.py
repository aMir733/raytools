from raytools.func import *
from raytools.db import Database
from raytools.parser import Daemon
from raytools.log import *
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Lock


def log_tail(filename, locks):
    global users
    logging.info("Tailing: " + filename)
    for line in tail(open(filename)):
        user = log_parseline(line)
        print(users)
        if user:
            locks_aq(locks)
            try:
                users[user[0]].add(user[1])
            except KeyError:
                users[user[0]] = {user[1]}
            locks_re(locks)

def check_count(session, locks):
    global users
    locks_aq(locks)
    for user, ips in users.items():
        l = len(ips)

    users = {}
    locks_re(locks)

def check_expire(session, locks):
    locks_aq(locks)
    handle_expired(session, expires="now", disable=True)
    locks_re(locks)

def check_traffic(session, locks):
    locks_aq(locks) 
    handle_traffic(session)
    locks_re(locks)

def init_args():
    parser = Daemon()
    return parser.parse()

def main():
    args = init_args()
    db = Database(args.__dict__.pop('database'))
    session = db.session()
    global users
    users = {}
    global warnings
    warnings = {}
    
    # Locks
    dlock = Lock()
    ulock = Lock()
    
    # Logging
    verb = calc_verb(args.__dict__.pop('verbose'), args.__dict__.pop('quiet'), 30)
    configure_logging(logging, verb, ((10, 'sqlalchemy.engine'),))
    
    # Scheduler
    scheduler = BackgroundScheduler()
    for filename in args.logs:
        scheduler.add_job(log_tail, args=(filename, (ulock,)))
    scheduler.add_job(check_count, 'interval', args=(session, (dlock, ulock)), seconds=30)
    scheduler.add_job(check_expire, 'interval', args=(session, (dlock,)), minutes=30)
    scheduler.add_job(check_traffic, 'interval', args=(session, (dlock,)), minutes=5)
    scheduler.start()
    
    # Run until interrupt
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()