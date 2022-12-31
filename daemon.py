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

MAX_WARN, MAX_RUN = 5, 8

def log_tail(filename, locks=()):
    global users
    logging.info("Tailing: " + filename)
    for line in tail(open(filename)):
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

def check_count(database, locks=()):
    global users, warnings, n_run
    n_run = n_run + 1
    if n_run > MAX_RUN:
        log.info("Clearing warnings")
        n_run = 0
        warnings = {}
    log.info(f"check_count's {str(n_run)}th run")
    locks_aq(locks)
    for user, ips in counter(users):
        try:
            warnings[user] = warnings[user] + 1
        except KeyError:
            warnings[user] = 1
        log.info("WAR/COUNT: {}: {}: {}".format(user, warnings[user], ' '.join(ips)))
        log.debug(warnings)
        if warnings[user] >= MAX_WARN:
            logging.warning("DISCONNECT/COUNT: '{}'".format(user))
            handle_disable(database, (int(user), "id"), reason="count")
            warnings.pop(user)
    users = {}
    locks_re(locks)

def check_expire(database, locks=()):
    locks_aq(locks)
    handle_expired(database, expired="now", disable=True)
    locks_re(locks)

def check_traffic(database, locks=()):
    locks_aq(locks) 
    handle_update_traffic(database)
    locks_re(locks)
    
def refresh(database, cfg_path, systemd, db_path, locks=()):
    if not is_refresh_required():
        return
    locks_aq(locks)
    log.info("Refreshing...")
    handle_refresh(database, cfg_path, systemd)
    locks_re(locks)
    
def main():
    # Arguments
    parser = Daemon()
    args = parser.parse()
    
    # Logging
    configure_logging(
        logging,
        level=0,
        format="%(asctime)s (%(name)s): %(message)s",
        filename=args.output_log,
        )

    db_path = args.__dict__.pop('database')
    cfg_path = args.configuration
    systemd = args.systemd
    log.info("Starting database located at: " + db_path)
    db = Database(db_path)
    database = db.session()
    global users, warnings, n_run
    users = {}
    warnings = {}
    n_run = 0
    
    # Locks
    dlock = Lock()
    ulock = Lock()

    # Pre scheduler jobs
    handle_refresh(database, cfg_path, systemd)

    # Scheduler
    scheduler = BackgroundScheduler({'apscheduler.timezone': 'Asia/Tehran'})
    for filename in args.logs:
        scheduler.add_job(log_tail, args=(filename,), kwargs={'locks': (ulock,)})
    scheduler.add_job(check_count, 'interval', args=(database,), kwargs={'locks': (ulock, dlock,)}, seconds=15)
    scheduler.add_job(check_expire, 'interval', args=(database,), kwargs={'locks': (dlock,)}, minutes=2)
    scheduler.add_job(check_traffic, 'interval', args=(database,), kwargs={'locks': (dlock,)}, minutes=1)
    scheduler.add_job(refresh, 'interval', args=(database, cfg_path, systemd, db_path), kwargs={'locks': (dlock,)}, seconds=30)
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