from raytools.func import *
from raytools.db import Database
from raytools.parser import Daemon
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Lock
from sys import argv


def log_tail(filename, lock):
    global users
    print("tailing: " + filename)
    for line in tail(open(filename)):
        user = log_parseline(line)
        print(users)
        if user:
            lock.acquire()
            try:
                users[user[0]].add(user[1])
            except KeyError:
                users[user[0]] = {user[1]}
            lock.release()

def check_count(lock):
    global users
    lock.acquire()
    for user, ips in users.items():
        l = len(ips)
        try:
            if not int(user.split("@")[0]) < l:
                continue
        except ValueError:
            pass
        print("{0}: {1} -> {2}".format(user, l, ' '.join(ips)))
    users = {}
    lock.release()

def init_args():
    parser = Daemon()
    return parser.parse(logs=(('sqlalchemy.engine', 20),), default=30)

def init_db(database):
    db = Database(database)
    db.create()
    return db

def main():
    # Initialize parser and db
    args = init_args()
    db = init_db(args.__dict__.pop('database'))

    # Lock
    global users
    users = {}
    lock = Lock()
    
    # Scheduler
    scheduler = BackgroundScheduler()
    for filename in args.logs:
        scheduler.add_job(log_tail, args=(filename, lock))
    scheduler.add_job(check_count, 'interval', args=(lock,), seconds=30)
    scheduler.start()
    
    # Run until Ctrl+C
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()