from raytools.func import *
from raytools.db import Database
from raytools.parser import Daemon
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Lock
from sys import argv


def log_tail(filename, locks):
    global users
    print("tailing: " + filename)
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
        try:
            if not int(user.split("@")[0]) < l:
                continue
        except ValueError:
            pass
        print("{0}: {1} -> {2}".format(user, l, ' '.join(ips)))
    users = {}
    locks_re(locks)

def check_expire(session, locks):
    handle_expired(expires="now")
    pass

def init_args():
    parser = Daemon()
    return parser.parse(logs=(('sqlalchemy.engine', 20),), default=30)

def main():
    args = init_args()
    db = Database(args.__dict__.pop('database'))
    session = db.session()
    global users
    users = {}
    
    # Locks
    dlock = Lock()
    ulock = Lock()
    
    # Scheduler
    scheduler = BackgroundScheduler()
    for filename in args.logs:
        scheduler.add_job(log_tail, args=(filename, (ulock,)))
    scheduler.add_job(check_count, 'interval', args=(session, (dlock, ulock)), seconds=30)
    scheduler.add_job(check_expire, 'interval', args=(session, (dlock,)), hours=1)
    scheduler.start()
    
    # Run until interrupt
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()