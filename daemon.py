#!/usr/bin/env python3
from raytools.func import *
from raytools.db import Database
from raytools.models import *
from raytools.parser import Daemon
from raytools.log import *
from raytools.handle import *
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Lock
from hashlib import md5
import logging


def log_tail(filename, locks=()):
    global users
    logging.info("Tailing: " + filename)
    for line in tail_F(filename):
        if not line:
            #time.sleep(0.1)
            continue
        try:
            user, ip = log_parseline(line)
        except TypeError:
            continue
        if user and ip:
            locks_aq(locks)
            try:
                users[user].add(ip)
            except KeyError:
                users[user] = {ip}
            locks_re(locks)

def check_count(session, locks=()):
    global users, warnings
    locks_aq(locks)
    for user in counter(users):
        try:
            warnings[user] = warnings[user] + 1
        except KeyError:
            warnings[user] = 1            
        log.info("WAR/COUNT: {}: {}".format(user, warnings[user]))
        if warnings[user] > 4:
            logging.warning("DIS/COUNT: '{}'".format(user))
            log.info(handle_disable(session, (int(user), "id"), reason="count"))
    users = {}
    locks_re(locks)

def check_expire(session, locks=()):
    locks_aq(locks)
    handle_expired(session, expired="now", disable=True)
    locks_re(locks)

def check_traffic(session, locks=()):
    locks_aq(locks) 
    handle_traffic(session)
    locks_re(locks)
    
def refresh(session, cfg_path, systemd, db_path, locks=()):
    locks_aq(locks)
    handle_refresh(session, cfg_path, systemd)
    locks_re(locks)
    
def clear_warnings(locks=()):
    global warnings
    locks_aq(locks) 
    warnings = {}
    log.info("Warnings cleared")
    locks_re(locks)

def init_args():
    parser = Daemon()
    return parser.parse()

def main():
    args = init_args()
    db_path = args.__dict__.pop('database')
    cfg_path = args.configuration
    systemd = args.systemd
    db = Database(db_path)
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
    
    # Pre scheduler jobs
    refresh(session, cfg_path, systemd, db_path, locks=())    
    # Scheduler
    scheduler = BackgroundScheduler({'apscheduler.timezone': 'Asia/Tehran'})
    for filename in args.logs:
        scheduler.add_job(log_tail, args=(filename,), kwargs={'locks': (ulock,)})
    scheduler.add_job(check_count, 'interval', args=(session,), kwargs={'locks': (ulock, dlock, wlock)}, seconds=30)
    scheduler.add_job(clear_warnings, 'interval', kwargs={'locks': (wlock,)}, minutes=5)
    scheduler.add_job(check_expire, 'interval', args=(session,), kwargs={'locks': (dlock,)}, minutes=2)
    scheduler.add_job(check_traffic, 'interval', args=(session,), kwargs={'locks': (dlock,)}, minutes=1)
    scheduler.add_job(refresh, 'interval', args=(session, cfg_path, systemd, db_path), kwargs={'locks': (dlock,)}, seconds=20)
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