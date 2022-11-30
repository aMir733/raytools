from raytools.func import *
from raytools.db import Database
from raytools.parser import Daemon
from apscheduler.schedulers.background import BackgroundScheduler
from multiprocessing import Manager
from sys import argv

def log_tail(filename, users):
    print("tailing: " + filename)
    for line in tail(open(filename)):
        user = log_parseline(line)
        if user:
            try:
                users[user[0]].add(user[1])
            except KeyError:
                users[user[0]] = {user[1]}

def check_count(users):
    for user, ips in users.items():
        l = len(ips)
        try:
            if int(user.split("@")[0]) > l:
                continue
        except ValueError:
            pass
        print("{0}: {1} -> {2}".format(user, l, ' '.join(ips)))
    users = {}
    
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

    # Multithread manager
    manager = Manager()
    users = manager.dict()
    
    # Scheduler
    scheduler = BackgroundScheduler()
    for filename in args.logs:
        scheduler.add_job(log_tail, args=(filename, users))
    scheduler.add_job(check_count, 'interval', args=(users,), seconds=30)
    scheduler.start()
    
    # Run until Ctrl+C
    try:
        while True:
            time.sleep(2)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    main()