from raytools.func import *
from raytools.db import Database
from raytools.models import *
from raytools.parser import Daemon
from raytools.log import *
from raytools.handle import *
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Lock
import logging


def log_tail(filename, locks):
    global users
    logging.info("Tailing: " + filename)
    for line in tail_F(filename):
        if not line:
            continue
        user, ip = log_parseline(line)
        if user and ip:
            locks_aq(locks)
            try:
                users[user].add(ip)
            except KeyError:
                users[user] = {ip}
            locks_re(locks)

def check_count(session, locks):
    global users, warnings
    locks_aq(locks)
    for user in counter(users):
        log.info("WAR/COUNT: '{}'".format(user))        
        try:
            warnings[user] = warnings[user] + 1
        except KeyError:
            warnings[user] = 1            
        if warnings[user] > 5:
            logging.warning("DIS/COUNT: '{}'".format(user))
            handle_disable(session, (int(user), "id"))
    users = {}
    locks_re(locks)

def check_expire(session, locks):
    locks_aq(locks)
    handle_expired(session, expired="now", disable=True)
    locks_re(locks)

def check_traffic(session, locks):
    locks_aq(locks) 
    handle_traffic(session)
    locks_re(locks)
    
def clear_warnings(locks):
    global warnings
    locks_aq(locks) 
    warnings = {}
    locks_re(locks)


def init_args():
    parser = Daemon()
    return parser.parse()

def main():
    args = init_args()
    db = Database(args.__dict__.pop('database'))
    session = db.session()
    global users, warnings
    users = {}
    warnings = {}
    
    # Locks
    dlock = Lock()
    ulock = Lock()
    wlock = Lock()
    
    # Logging
    configure_logging(
        logging,
        level=0,
        format="%(asctime)s (%(name)s): %(message)s",
        filename=args.output_log,
        )
    
    # Scheduler
    scheduler = BackgroundScheduler()
    for filename in args.logs:
        scheduler.add_job(log_tail, args=(filename, (ulock,)))
    scheduler.add_job(check_count, 'interval', args=(session, (dlock, ulock, wlock)), seconds=30)
    scheduler.add_job(clear_warnings, 'interval', args=((wlock,),), minutes=5)
    scheduler.add_job(check_expire, 'interval', args=(session, (dlock,)), minutes=30)
    scheduler.add_job(check_traffic, 'interval', args=(session, (dlock,)), minutes=5)
    scheduler.start()
    logging.info("Daemon started")
    
    # Run until interrupt
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()